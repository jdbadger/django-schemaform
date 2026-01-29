"""
django-schema-form: Build Django forms from Pydantic models.

This module provides SchemaForm, a Django form class that uses Pydantic's
model_fields API for field introspection and Pydantic for all validation.

Validation Philosophy:
    - Pydantic is the single source of truth for all validation rules
    - Use @field_validator for single-field validation (including file size/type)
    - Use @model_validator for cross-field validation (including conditional file requirements)
    - Django handles only mechanical file upload processing (parsing, MIME detection)
    - File fields receive UploadedFileWrapper in validators with .name, .size, .content_type
"""

from __future__ import annotations

import types
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Union, get_args, get_origin
from uuid import UUID

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen, MultipleOf
from django import forms
from django.forms.forms import DeclarativeFieldsMetaclass
from django.utils.translation import gettext_lazy as _
from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    EmailStr,
    FutureDate,
    FutureDatetime,
    HttpUrl,
    NaiveDatetime,
    PastDate,
    PastDatetime,
    SecretStr,
)
from pydantic import ValidationError as PydanticValidationError
from pydantic.fields import FieldInfo
from pydantic_core import ErrorDetails

from .types import UploadedFileWrapper


# Type to Django Field Mapping

TYPE_TO_FIELD: dict[Any, type[forms.Field]] = {
    str: forms.CharField,
    int: forms.IntegerField,
    float: forms.FloatField,
    Decimal: forms.DecimalField,
    bool: forms.BooleanField,
    date: forms.DateField,
    datetime: forms.DateTimeField,
    time: forms.TimeField,
    timedelta: forms.DurationField,
    UUID: forms.UUIDField,
}

# Add Pydantic types
TYPE_TO_FIELD[EmailStr] = forms.EmailField
TYPE_TO_FIELD[HttpUrl] = forms.URLField
TYPE_TO_FIELD[AnyUrl] = forms.URLField
TYPE_TO_FIELD[SecretStr] = forms.CharField

# Add Pydantic constrained date/datetime types
TYPE_TO_FIELD[PastDate] = forms.DateField
TYPE_TO_FIELD[FutureDate] = forms.DateField
TYPE_TO_FIELD[PastDatetime] = forms.DateTimeField
TYPE_TO_FIELD[FutureDatetime] = forms.DateTimeField
TYPE_TO_FIELD[AwareDatetime] = forms.DateTimeField
TYPE_TO_FIELD[NaiveDatetime] = forms.DateTimeField


# Pydantic Error Message Translation

PYDANTIC_ERROR_MESSAGES: dict[str, str] = {
    # Required/missing
    "missing": "This field is required.",
    # String errors
    "string_type": "Enter a valid string.",
    "string_too_short": "Ensure this value has at least {min_length} characters.",
    "string_too_long": "Ensure this value has at most {max_length} characters.",
    "string_pattern_mismatch": "Enter a valid value matching the required pattern.",
    # Numeric errors
    "int_type": "Enter a whole number.",
    "int_parsing": "Enter a whole number.",
    "float_type": "Enter a number.",
    "float_parsing": "Enter a number.",
    "decimal_type": "Enter a number.",
    "decimal_parsing": "Enter a valid decimal number.",
    "greater_than": "Ensure this value is greater than {gt}.",
    "greater_than_equal": "Ensure this value is greater than or equal to {ge}.",
    "less_than": "Ensure this value is less than {lt}.",
    "less_than_equal": "Ensure this value is less than or equal to {le}.",
    # Boolean errors
    "bool_type": "Enter a valid boolean value.",
    "bool_parsing": "Enter a valid boolean value.",
    # Date/time errors
    "date_type": "Enter a valid date.",
    "date_parsing": "Enter a valid date.",
    "date_from_datetime_parsing": "Enter a valid date.",
    "datetime_type": "Enter a valid date and time.",
    "datetime_parsing": "Enter a valid date and time.",
    "time_type": "Enter a valid time.",
    "time_parsing": "Enter a valid time.",
    "timedelta_type": "Enter a valid duration.",
    "timedelta_parsing": "Enter a valid duration.",
    # Choice/enum errors
    "literal_error": "Select a valid choice.",
    "enum": "Select a valid choice.",
    # UUID errors
    "uuid_type": "Enter a valid UUID.",
    "uuid_parsing": "Enter a valid UUID.",
    # Email/URL errors
    "value_error.email": "Enter a valid email address.",
    "value_error.url": "Enter a valid URL.",
}


class SchemaFormMetaOptions:
    def __init__(self, schema: type[BaseModel] | None = None):
        self.schema = schema


class SchemaFormMeta(DeclarativeFieldsMetaclass):
    def __new__(mcs, name, bases, attrs):
        _meta = attrs.get("Meta", None)
        new_class = super().__new__(mcs, name, bases, attrs)
        if _meta is not None:
            schema = getattr(_meta, "schema", None)
            new_class._meta = SchemaFormMetaOptions(schema=schema)
        return new_class


class SchemaForm(forms.BaseForm, metaclass=SchemaFormMeta):
    """
    A Django form class that builds fields from a Pydantic model.

    Uses Pydantic's model_fields API for field introspection and
    Pydantic for all validation (except file fields, which use Django).

    Usage:
        from pydantic import BaseModel, Field
        from django_schema_form import SchemaForm

        class PersonSchema(BaseModel):
            name: str = Field(min_length=1, max_length=100)
            age: int = Field(ge=0, le=150)
            email: str | None = None

        class PersonForm(SchemaForm):
            class Meta:
                schema = PersonSchema
    """

    _meta: SchemaFormMetaOptions
    schema: type[BaseModel] | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.schema = getattr(self._meta, "schema", None)
        if not self.schema or not issubclass(self.schema, BaseModel):
            raise ValueError(
                "Subclasses of SchemaForm must define a 'schema' attribute "
                "in 'Meta' that is a subclass of pydantic.BaseModel"
            )

        # Track which fields are file fields (for hybrid validation)
        self._file_field_names: set[str] = set()

        # Build form fields from Pydantic model_fields
        for field_name, field_info in self.schema.model_fields.items():
            self.fields[field_name] = self._build_field(field_name, field_info)

    # Field Building

    def _build_field(self, field_name: str, field_info: FieldInfo) -> forms.Field:
        """Build a Django form field from a Pydantic FieldInfo."""
        annotation = field_info.annotation

        # Unwrap Optional types first
        is_optional = False
        core_type = annotation
        unwrapped = self._unwrap_optional(annotation)
        if unwrapped is not None:
            is_optional = True
            core_type = unwrapped

        # Check for file/image fields (via json_schema_extra) - check core type
        file_format = self._get_file_format(field_info)
        if file_format == "binary":
            self._file_field_names.add(field_name)
            return self._build_file_field(field_name, field_info, forms.FileField, is_optional)
        elif file_format == "image":
            self._file_field_names.add(field_name)
            return self._build_file_field(field_name, field_info, forms.ImageField, is_optional)

        # Detect choice fields (Literal or Enum)
        choices = self._detect_choices(core_type)
        if choices is not None:
            field_class = forms.ChoiceField
        else:
            field_class = self._get_field_class(core_type)

        # Build kwargs
        kwargs = self._build_field_kwargs(field_name, field_info, field_class, is_optional)

        if choices is not None:
            # Add empty choice for optional fields
            if is_optional:
                kwargs["choices"] = [("", "---------")] + choices
            else:
                kwargs["choices"] = choices

        # Extract constraints from metadata
        constraints = self._extract_constraints(field_info)

        # Separate widget-only attributes from field kwargs
        step = constraints.pop("step", None)

        kwargs.update(constraints)

        # Create the field
        field = field_class(**kwargs)

        # Apply step attribute to numeric field widgets
        if step is not None and isinstance(field, (forms.IntegerField, forms.FloatField, forms.DecimalField)):
            field.widget.attrs["step"] = step

        # Apply widget customizations (pass core_type for datetime constraints)
        field = self._customize_widget(field, core_type)

        return field

    def _build_file_field(
        self,
        field_name: str,
        field_info: FieldInfo,
        field_class: type[forms.Field],
        is_optional: bool,
    ) -> forms.Field:
        """Build a file or image field."""
        kwargs = {
            "label": field_info.alias or field_info.title or field_name.replace("_", " ").title(),
            "help_text": field_info.description or "",
            "required": not is_optional and field_info.is_required(),
        }

        return field_class(**kwargs)

    def _build_field_kwargs(
        self,
        field_name: str,
        field_info: FieldInfo,
        field_class: type[forms.Field],
        is_optional: bool,
    ) -> dict[str, Any]:
        """Build common kwargs for a Django form field."""
        # For BooleanField, required=False means the checkbox can be unchecked
        if field_class == forms.BooleanField:
            required = not is_optional and field_info.is_required()
        else:
            required = field_info.is_required() and not is_optional

        return {
            "label": field_info.alias or field_info.title or field_name.replace("_", " ").title(),
            "help_text": field_info.description or "",
            "required": required,
        }

    def _get_field_class(self, python_type: Any) -> type[forms.Field]:
        """Map a Python type to a Django form field class."""
        # Direct lookup
        if python_type in TYPE_TO_FIELD:
            return TYPE_TO_FIELD[python_type]

        # Check for subclasses (e.g., custom Enum that's also a str)
        for type_key, field_class in TYPE_TO_FIELD.items():
            if isinstance(python_type, type) and issubclass(python_type, type_key):
                return field_class

        # Fallback
        return forms.CharField

    def _get_file_format(self, field_info: FieldInfo) -> str | None:
        """Check if field has a file format marker in json_schema_extra."""
        # First check the field_info directly
        extra = field_info.json_schema_extra
        if isinstance(extra, dict):
            fmt = extra.get("format")  # type: ignore[misc]
            if fmt in ("binary", "image"):
                return fmt

        # For optional Annotated types (FileUpload | None), check the Union args
        import typing
        args = typing.get_args(field_info.annotation)
        if args:
            # Check first arg (should be the Annotated type)
            first_arg = args[0]
            if hasattr(first_arg, "__metadata__"):
                for metadata in first_arg.__metadata__:
                    if isinstance(metadata, FieldInfo) and metadata.json_schema_extra:
                        fmt = metadata.json_schema_extra.get("format")
                        if fmt in ("binary", "image"):
                            return fmt
        return None

    def _customize_widget(self, field: forms.Field, core_type: Any = None) -> forms.Field:
        """Apply widget customizations for specific field types."""
        if isinstance(field, forms.DateField) and not isinstance(field, forms.DateTimeField):
            attrs = {"type": "date"}
            attrs.update(self._get_datetime_min_max_attrs(core_type))
            field.widget = forms.DateInput(attrs=attrs)
        elif isinstance(field, forms.DateTimeField):
            attrs = {"type": "datetime-local"}
            attrs.update(self._get_datetime_min_max_attrs(core_type))
            field.widget = forms.DateTimeInput(attrs=attrs)
        elif isinstance(field, forms.TimeField):
            field.widget = forms.TimeInput(attrs={"type": "time"})
        elif core_type is SecretStr:
            field.widget = forms.PasswordInput(render_value=False)
        return field

    def _get_datetime_min_max_attrs(self, core_type: Any) -> dict[str, str]:
        """Get min/max attributes for Pydantic date/datetime constraint types."""
        attrs = {}
        today = date.today()
        now = datetime.now()

        if core_type is PastDate:
            # max = today (HTML5 date input uses YYYY-MM-DD)
            attrs["max"] = today.isoformat()
        elif core_type is FutureDate:
            # min = today
            attrs["min"] = today.isoformat()
        elif core_type is PastDatetime:
            # max = now (datetime-local uses YYYY-MM-DDTHH:MM)
            attrs["max"] = now.strftime("%Y-%m-%dT%H:%M")
        elif core_type is FutureDatetime:
            # min = now
            attrs["min"] = now.strftime("%Y-%m-%dT%H:%M")
        # AwareDatetime/NaiveDatetime: Pydantic handles timezone validation,
        # Django's DateTimeField behavior depends on USE_TZ setting

        return attrs

    # Type Introspection Helpers

    def _unwrap_optional(self, annotation: Any) -> type | None:
        """
        If annotation is Optional[X] or X | None, return X.
        Otherwise return None.
        """
        origin = get_origin(annotation)

        # Handle Union types (including X | None syntax)
        if origin is Union or origin is types.UnionType:
            args = get_args(annotation)
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1 and type(None) in args:
                return non_none_args[0]

        return None

    def _detect_choices(self, annotation: Any) -> list[tuple[Any, str]] | None:
        """
        Detect if annotation is a Literal or Enum and return choices.
        Returns list of (value, label) tuples or None.
        """
        origin = get_origin(annotation)

        # Literal["a", "b", "c"]
        if origin is Literal:
            args = get_args(annotation)
            return [(val, str(val)) for val in args]

        # Enum subclass
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return [(member.value, member.name.replace("_", " ").title()) for member in annotation]

        return None

    def _extract_constraints(self, field_info: FieldInfo) -> dict[str, Any]:
        """Extract constraint kwargs from FieldInfo metadata."""
        kwargs: dict[str, Any] = {}

        for meta in field_info.metadata:
            # Numeric constraints
            if isinstance(meta, Ge):
                kwargs["min_value"] = meta.ge
            if isinstance(meta, Gt):
                # Django doesn't have exclusive min, use min_value
                kwargs["min_value"] = meta.gt
            if isinstance(meta, Le):
                kwargs["max_value"] = meta.le
            if isinstance(meta, Lt):
                # Django doesn't have exclusive max, use max_value
                kwargs["max_value"] = meta.lt

            # String length constraints
            if isinstance(meta, MinLen):
                kwargs["min_length"] = meta.min_length
            if isinstance(meta, MaxLen):
                kwargs["max_length"] = meta.max_length

            # Step constraint (for HTML5 number inputs)
            if isinstance(meta, MultipleOf):
                kwargs["step"] = meta.multiple_of

            # Decimal field constraints from Pydantic metadata
            if hasattr(meta, "max_digits") and meta.max_digits is not None:
                kwargs["max_digits"] = meta.max_digits
            if hasattr(meta, "decimal_places") and meta.decimal_places is not None:
                kwargs["decimal_places"] = meta.decimal_places

        return kwargs

    # Validation

    def _clean_fields(self):
        """
        Override to extract raw values from widgets.

        For non-file fields: Extract raw values, convert empty strings to None
        for optional fields, and let Pydantic handle validation.

        For file fields: Use Django's standard field validation.
        """
        for name, bf in self._bound_items():
            field = bf.field

            if name in self._file_field_names:
                # File fields use Django's validation
                try:
                    value = field._clean_bound_field(bf)
                    self.cleaned_data[name] = value
                    if hasattr(self, f"clean_{name}"):
                        value = getattr(self, f"clean_{name}")() 
                        self.cleaned_data[name] = value
                except forms.ValidationError as e:
                    self.add_error(name, e)
            else:
                # Non-file fields: extract raw value for Pydantic
                value = bf.data

                # Handle empty values
                if value in field.empty_values:
                    if field.required:
                        # Let Pydantic report the missing field error
                        self.cleaned_data[name] = None
                    else:
                        self.cleaned_data[name] = None
                else:
                    self.cleaned_data[name] = value

    def _clean_form(self):
        """
        Override to use Pydantic for validation.

        Validates all fields with Pydantic, including file fields wrapped
        in UploadedFileWrapper so @model_validator can access file metadata.

        Django handles mechanical file validation (upload parsing, MIME detection).
        Pydantic handles business logic (conditional requirements, size limits, etc.).
        """
        # Build data dict for Pydantic, wrapping file fields
        pydantic_data = {}
        original_files = {}  # Keep original UploadedFile objects for cleaned_data

        for k, v in self.cleaned_data.items():
            if k in self._file_field_names:
                # Wrap file fields for Pydantic validators
                if v is not None:
                    pydantic_data[k] = UploadedFileWrapper(v)
                    original_files[k] = v
                else:
                    pydantic_data[k] = None
            else:
                pydantic_data[k] = v

        try:
            # Validate with Pydantic
            assert self.schema is not None
            validated = self.schema(**pydantic_data)
            self.cleaned_data = validated.model_dump()

            # Restore original UploadedFile objects (model_dump can't serialize them)
            for field_name, file_obj in original_files.items():
                self.cleaned_data[field_name] = file_obj

        except PydanticValidationError as e:
            for err in e.errors():
                field_name, message = self._convert_pydantic_error(err)
                self.add_error(field_name, forms.ValidationError(_(message)))

    def _convert_pydantic_error(self, error: ErrorDetails) -> tuple[str | None, str]:
        """
        Convert a Pydantic error dict to (field_name, user_friendly_message).

        Error location handling:
        - Single field in loc (including file fields): Error attaches to that field
        - Empty loc or '__root__': Non-field error (displayed at top of form)
        - Nested loc: Uses first element as field name
        """
        # Get field name from location
        loc = error.get("loc", ())
        if loc and loc[0] != "__root__":
            field_name: str | None = str(loc[0])
        else:
            field_name = None

        # Get error type and context
        error_type = error.get("type", "value_error")
        ctx = error.get("ctx", {})

        # For value_error (custom ValueError from validators), use Pydantic's message directly
        # as it contains the custom error message from the validator
        if error_type == "value_error":
            message = error.get("msg", "Enter a valid value.")
        elif error_type in PYDANTIC_ERROR_MESSAGES:
            message = PYDANTIC_ERROR_MESSAGES[error_type]
            # Interpolate context values
            try:
                message = message.format(**ctx)
            except KeyError:
                pass  # Keep the message template if context is missing
        else:
            # Fallback to Pydantic's message
            message = error.get("msg", "Enter a valid value.")

        return field_name, message

    def _post_clean(self):
        """Hook for subclasses to add additional validation."""
        pass
