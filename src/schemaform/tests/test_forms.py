"""Tests for SchemaForm field building and validation."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal
from unittest.mock import patch
from uuid import UUID

import pytest
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    EmailStr,
    Field,
    FutureDate,
    FutureDatetime,
    HttpUrl,
    NaiveDatetime,
    PastDate,
    PastDatetime,
    SecretStr,
)

from schemaform import FileUpload, SchemaForm
from schemaform.forms import TYPE_TO_FIELD

from .conftest import SampleEnum, SampleSchema, SampleSchemaForm


# =============================================================================
# Test SchemaForm Initialization
# =============================================================================


class SampleSchemaFormInitialization:
    """Tests for SchemaForm.__init__."""

    def test_should_raise_value_error_when_no_schema_defined(self):
        """SchemaForm without schema in Meta should raise ValueError."""

        # Arrange
        class NoSchemaForm(SchemaForm):
            class Meta:
                pass

        # Act & Assert
        with pytest.raises(ValueError, match="must define a 'schema' attribute"):
            NoSchemaForm()

    def test_should_raise_value_error_when_schema_not_basemodel(self):
        """SchemaForm with non-BaseModel schema should raise ValueError."""

        # Arrange
        class NotAModel:
            pass

        class InvalidSchemaForm(SchemaForm):
            class Meta:
                schema = NotAModel

        # Act & Assert
        with pytest.raises(ValueError, match="subclass of pydantic.BaseModel"):
            InvalidSchemaForm()

    def test_should_build_fields_from_pydantic_model_fields(self):
        """SchemaForm should create Django fields for each Pydantic model field."""
        # Arrange & Act
        form = SampleSchemaForm()

        # Assert
        assert "string_field" in form.fields
        assert "int_field" in form.fields
        assert "email_field" in form.fields
        assert len(form.fields) == len(SampleSchema.model_fields)

    def test_should_track_file_fields_in_file_field_names(self):
        """File and image fields should be tracked in _file_field_names."""
        # Arrange & Act
        form = SampleSchemaForm()

        # Assert
        assert "file_field" in form._file_field_names
        assert "image_field" in form._file_field_names
        assert "string_field" not in form._file_field_names


# =============================================================================
# Test Type-to-Field Mapping
# =============================================================================


class TestFieldTypeMapping:
    """Tests for _get_field_class and TYPE_TO_FIELD."""

    @pytest.mark.parametrize(
        ("python_type", "expected_field"),
        [
            (str, forms.CharField),
            (int, forms.IntegerField),
            (float, forms.FloatField),
            (Decimal, forms.DecimalField),
            (bool, forms.BooleanField),
            (date, forms.DateField),
            (datetime, forms.DateTimeField),
            (time, forms.TimeField),
            (timedelta, forms.DurationField),
            (UUID, forms.UUIDField),
            (EmailStr, forms.EmailField),
            (HttpUrl, forms.URLField),
            (AnyUrl, forms.URLField),
            (SecretStr, forms.CharField),
            (PastDate, forms.DateField),
            (FutureDate, forms.DateField),
            (PastDatetime, forms.DateTimeField),
            (FutureDatetime, forms.DateTimeField),
            (AwareDatetime, forms.DateTimeField),
            (NaiveDatetime, forms.DateTimeField),
        ],
    )
    def test_should_map_type_to_correct_field_class(self, python_type, expected_field):
        """Each Python/Pydantic type should map to the correct Django field."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        result = form._get_field_class(python_type)

        # Assert
        assert result is expected_field

    def test_should_handle_type_subclasses(self):
        """Custom type subclasses should map to parent type's field."""

        # Arrange
        class CustomStr(str):
            pass

        form = SampleSchemaForm()

        # Act
        result = form._get_field_class(CustomStr)

        # Assert
        assert result is forms.CharField

    def test_should_fallback_to_charfield_for_unknown_types(self):
        """Unknown types should fallback to CharField."""

        # Arrange
        class UnknownType:
            pass

        form = SampleSchemaForm()

        # Act
        result = form._get_field_class(UnknownType)

        # Assert
        assert result is forms.CharField

    def test_type_to_field_contains_expected_mappings(self):
        """TYPE_TO_FIELD should contain all expected type mappings."""
        # Assert
        assert TYPE_TO_FIELD[str] is forms.CharField
        assert TYPE_TO_FIELD[int] is forms.IntegerField
        assert TYPE_TO_FIELD[EmailStr] is forms.EmailField
        assert TYPE_TO_FIELD[PastDate] is forms.DateField


# =============================================================================
# Test Optional Type Handling
# =============================================================================


class TestOptionalTypeHandling:
    """Tests for _unwrap_optional."""

    def test_should_unwrap_pipe_none_syntax(self):
        """X | None syntax should unwrap to X."""
        # Arrange
        form = SampleSchemaForm()
        annotation = str | None

        # Act
        result = form._unwrap_optional(annotation)

        # Assert
        assert result is str

    def test_should_unwrap_complex_pipe_none(self):
        """Complex types with | None should unwrap correctly."""
        # Arrange
        form = SampleSchemaForm()
        annotation = int | None

        # Act
        result = form._unwrap_optional(annotation)

        # Assert
        assert result is int

    def test_should_return_none_for_non_optional(self):
        """Non-optional types should return None."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        result = form._unwrap_optional(str)

        # Assert
        assert result is None

    def test_should_return_none_for_union_without_none(self):
        """Union types without None should return None."""
        # Arrange
        form = SampleSchemaForm()
        annotation = str | int

        # Act
        result = form._unwrap_optional(annotation)

        # Assert
        assert result is None


# =============================================================================
# Test Choice Detection
# =============================================================================


class TestChoiceDetection:
    """Tests for _detect_choices."""

    def test_should_detect_literal_choices(self):
        """Literal types should return choices as (value, value) tuples."""
        # Arrange
        form = SampleSchemaForm()
        annotation = Literal["a", "b", "c"]

        # Act
        result = form._detect_choices(annotation)

        # Assert
        assert result == [("a", "a"), ("b", "b"), ("c", "c")]

    def test_should_detect_enum_choices(self):
        """Enum types should return choices as (value, title) tuples."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        result = form._detect_choices(SampleEnum)

        # Assert
        assert result == [
            ("option_a", "Option A"),
            ("option_b", "Option B"),
            ("option_c", "Option C"),
        ]

    def test_should_return_none_for_non_choice_types(self):
        """Non-choice types should return None."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        result = form._detect_choices(str)

        # Assert
        assert result is None

    def test_should_add_empty_choice_for_optional_literal(self):
        """Optional Literal fields should have empty choice prepended."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        literal_field = form.fields["literal_field"]

        # Assert
        assert isinstance(literal_field, forms.ChoiceField)
        assert literal_field.choices[0] == ("", "---------")

    def test_should_add_empty_choice_for_optional_enum(self):
        """Optional Enum fields should have empty choice prepended."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        enum_field = form.fields["enum_field"]

        # Assert
        assert isinstance(enum_field, forms.ChoiceField)
        assert enum_field.choices[0] == ("", "---------")


# =============================================================================
# Test Constraint Extraction
# =============================================================================


class TestConstraintExtraction:
    """Tests for _extract_constraints."""

    def test_should_extract_min_length_constraint(self):
        """min_length should be extracted from Field metadata."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_string"]

        # Assert
        assert field.min_length == 3

    def test_should_extract_max_length_constraint(self):
        """max_length should be extracted from Field metadata."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_string"]

        # Assert
        assert field.max_length == 100

    def test_should_extract_ge_as_min_value(self):
        """ge constraint should become min_value."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_int"]

        # Assert
        assert field.min_value == 0

    def test_should_extract_le_as_max_value(self):
        """le constraint should become max_value."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_int"]

        # Assert
        assert field.max_value == 1000

    def test_should_extract_gt_as_min_value(self):
        """gt constraint should become min_value."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_float"]

        # Assert
        assert field.min_value == 0.0

    def test_should_extract_lt_as_max_value(self):
        """lt constraint should become max_value."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_float"]

        # Assert
        assert field.max_value == 100.0

    def test_should_extract_decimal_precision(self):
        """max_digits and decimal_places should be extracted."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["constrained_decimal"]

        # Assert
        assert field.max_digits == 10
        assert field.decimal_places == 2

    def test_should_extract_multiple_of_as_step(self):
        """multiple_of should become step widget attribute."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["step_number"]

        # Assert
        assert field.widget.attrs.get("step") == 5


# =============================================================================
# Test Widget Customization
# =============================================================================


class TestWidgetCustomization:
    """Tests for _customize_widget and _get_datetime_min_max_attrs."""

    def test_should_apply_date_input_widget(self):
        """DateField should use DateInput with type='date'."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["date_field"]

        # Assert
        assert isinstance(field.widget, forms.DateInput)
        # Django extracts 'type' attr and stores as input_type
        assert field.widget.input_type == "date"

    def test_should_apply_datetime_input_widget(self):
        """DateTimeField should use DateTimeInput with type='datetime-local'."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["datetime_field"]

        # Assert
        assert isinstance(field.widget, forms.DateTimeInput)
        # Django extracts 'type' attr and stores as input_type
        assert field.widget.input_type == "datetime-local"

    def test_should_apply_time_input_widget(self):
        """TimeField should use TimeInput with type='time'."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["time_field"]

        # Assert
        assert isinstance(field.widget, forms.TimeInput)
        # Django extracts 'type' attr and stores as input_type
        assert field.widget.input_type == "time"

    def test_should_apply_password_input_for_secret(self):
        """SecretStr field should use PasswordInput widget."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["secret_field"]

        # Assert
        assert isinstance(field.widget, forms.PasswordInput)

    def test_should_add_max_attr_for_past_date(self):
        """PastDate field should have max attribute set to today."""
        # Arrange
        with patch("schemaform.forms.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 22)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            class PastDateSchema(BaseModel):
                past_date: PastDate

            class PastDateForm(SchemaForm):
                class Meta:
                    schema = PastDateSchema

            # Act
            form = PastDateForm()
            field = form.fields["past_date"]

            # Assert
            assert field.widget.attrs.get("max") == "2026-01-22"

    def test_should_add_min_attr_for_future_date(self):
        """FutureDate field should have min attribute set to today."""
        # Arrange
        with patch("schemaform.forms.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 22)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            class FutureDateSchema(BaseModel):
                future_date: FutureDate

            class FutureDateForm(SchemaForm):
                class Meta:
                    schema = FutureDateSchema

            # Act
            form = FutureDateForm()
            field = form.fields["future_date"]

            # Assert
            assert field.widget.attrs.get("min") == "2026-01-22"

    def test_should_add_max_attr_for_past_datetime(self):
        """PastDatetime field should have max attribute set to now."""
        # Arrange
        with patch("schemaform.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 22, 14, 30)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            class PastDatetimeSchema(BaseModel):
                past_dt: PastDatetime

            class PastDatetimeForm(SchemaForm):
                class Meta:
                    schema = PastDatetimeSchema

            # Act
            form = PastDatetimeForm()
            field = form.fields["past_dt"]

            # Assert
            assert field.widget.attrs.get("max") == "2026-01-22T14:30"

    def test_should_add_min_attr_for_future_datetime(self):
        """FutureDatetime field should have min attribute set to now."""
        # Arrange
        with patch("schemaform.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 22, 14, 30)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            class FutureDatetimeSchema(BaseModel):
                future_dt: FutureDatetime

            class FutureDatetimeForm(SchemaForm):
                class Meta:
                    schema = FutureDatetimeSchema

            # Act
            form = FutureDatetimeForm()
            field = form.fields["future_dt"]

            # Assert
            assert field.widget.attrs.get("min") == "2026-01-22T14:30"


# =============================================================================
# Test File Field Handling
# =============================================================================


class TestFileFieldHandling:
    """Tests for file/image field building."""

    def test_should_build_file_field_for_file_upload(self):
        """FileUpload annotation should create FileField."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["file_field"]

        # Assert
        assert isinstance(field, forms.FileField)
        assert not isinstance(field, forms.ImageField)

    def test_should_build_image_field_for_image_upload(self):
        """ImageUpload annotation should create ImageField."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["image_field"]

        # Assert
        assert isinstance(field, forms.ImageField)

    def test_should_detect_binary_format(self):
        """_get_file_format should detect binary format marker."""
        # Arrange
        form = SampleSchemaForm()
        field_info = SampleSchema.model_fields["file_field"]

        # Act
        result = form._get_file_format(field_info)

        # Assert
        assert result == "binary"

    def test_should_detect_image_format(self):
        """_get_file_format should detect image format marker."""
        # Arrange
        form = SampleSchemaForm()
        field_info = SampleSchema.model_fields["image_field"]

        # Act
        result = form._get_file_format(field_info)

        # Assert
        assert result == "image"

    def test_should_return_none_for_non_file_field(self):
        """_get_file_format should return None for regular fields."""
        # Arrange
        form = SampleSchemaForm()
        field_info = SampleSchema.model_fields["string_field"]

        # Act
        result = form._get_file_format(field_info)

        # Assert
        assert result is None


# =============================================================================
# Test Field Label and Metadata
# =============================================================================


class TestFieldMetadata:
    """Tests for field label, help_text, and alias handling."""

    def test_should_use_title_as_label(self):
        """Field with title should use it as label."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["titled_field"]

        # Assert
        assert field.label == "Custom Title"

    def test_should_use_description_as_help_text(self):
        """Field with description should use it as help_text."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["described_field"]

        # Assert
        assert field.help_text == "This is help text"

    def test_should_generate_label_from_field_name(self):
        """Field without title should generate label from name."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["string_field"]

        # Assert
        assert field.label == "String Field"

    def test_should_use_alias_as_label_if_provided(self):
        """Field with alias should use it as label."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["aliased_field"]

        # Assert
        assert field.label == "customAlias"


# =============================================================================
# Test Pydantic Validation
# =============================================================================


class TestPydanticValidation:
    """Tests for _clean_form and Pydantic validation."""

    def test_should_validate_valid_data(self):
        """Valid data should pass Pydantic validation."""

        # Arrange
        class RequiredStringSchema(BaseModel):
            name: str

        class RequiredStringForm(SchemaForm):
            class Meta:
                schema = RequiredStringSchema

        form = RequiredStringForm(data={"name": "John"})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert form.cleaned_data["name"] == "John"

    def test_should_report_missing_required_field(self):
        """Missing required field should add error."""

        # Arrange
        class RequiredStringSchema(BaseModel):
            name: str

        class RequiredStringForm(SchemaForm):
            class Meta:
                schema = RequiredStringSchema

        form = RequiredStringForm(data={})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "name" in form.errors

    def test_should_convert_empty_optional_to_none(self):
        """Empty optional fields should become None."""
        # Arrange
        form = SampleSchemaForm(data={"string_field": ""})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert form.cleaned_data["string_field"] is None

    def test_should_coerce_types_via_pydantic(self):
        """Pydantic should coerce string inputs to correct types."""

        # Arrange
        class TypedSchema(BaseModel):
            count: int
            price: Decimal

        class TypedForm(SchemaForm):
            class Meta:
                schema = TypedSchema

        form = TypedForm(data={"count": "42", "price": "19.99"})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert form.cleaned_data["count"] == 42
        assert form.cleaned_data["price"] == Decimal("19.99")

    def test_should_validate_constraints(self):
        """Constraint violations should add errors."""

        # Arrange
        class ConstrainedSchema(BaseModel):
            name: str = Field(min_length=3)

        class ConstrainedForm(SchemaForm):
            class Meta:
                schema = ConstrainedSchema

        form = ConstrainedForm(data={"name": "ab"})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "name" in form.errors


# =============================================================================
# Test Error Conversion
# =============================================================================


class TestErrorConversion:
    """Tests for _convert_pydantic_error."""

    def test_should_convert_missing_error(self):
        """Missing field error should convert to 'This field is required.'"""
        # Arrange
        form = SampleSchemaForm()
        from typing import cast

        from pydantic_core import ErrorDetails

        error = cast(
            ErrorDetails,
            {
                "loc": ("name",),
                "type": "missing",
                "ctx": {},
                "msg": "Field required",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert field_name == "name"
        assert message == "This field is required."

    def test_should_convert_string_too_short_with_context(self):
        """String too short error should interpolate min_length."""
        # Arrange
        from typing import cast

        from pydantic_core import ErrorDetails

        form = SampleSchemaForm()
        error = cast(
            ErrorDetails,
            {
                "loc": ("name",),
                "type": "string_too_short",
                "ctx": {"min_length": 3},
                "msg": "String should have at least 3 characters",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert message == "Ensure this value has at least 3 characters."

    def test_should_convert_string_too_long_with_context(self):
        """String too long error should interpolate max_length."""
        # Arrange
        from typing import cast

        from pydantic_core import ErrorDetails

        form = SampleSchemaForm()
        error = cast(
            ErrorDetails,
            {
                "loc": ("name",),
                "type": "string_too_long",
                "ctx": {"max_length": 100},
                "msg": "String should have at most 100 characters",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert message == "Ensure this value has at most 100 characters."

    def test_should_convert_numeric_constraint_errors(self):
        """Numeric constraint errors should interpolate correctly."""
        # Arrange
        from typing import cast

        from pydantic_core import ErrorDetails

        form = SampleSchemaForm()
        error = cast(
            ErrorDetails,
            {
                "loc": ("age",),
                "type": "greater_than_equal",
                "ctx": {"ge": 0},
                "msg": "Input should be greater than or equal to 0",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert message == "Ensure this value is greater than or equal to 0."

    def test_should_fallback_to_pydantic_message_for_unknown_error(self):
        """Unknown error types should use Pydantic's message."""
        # Arrange
        from typing import cast

        from pydantic_core import ErrorDetails

        form = SampleSchemaForm()
        error = cast(
            ErrorDetails,
            {
                "loc": ("field",),
                "type": "custom_unknown_error",
                "ctx": {},
                "msg": "Custom error message",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert message == "Custom error message"

    @pytest.mark.parametrize(
        ("error_type", "expected_message"),
        [
            ("int_type", "Enter a whole number."),
            ("int_parsing", "Enter a whole number."),
            ("float_type", "Enter a number."),
            ("float_parsing", "Enter a number."),
            ("bool_type", "Enter a valid boolean value."),
            ("date_type", "Enter a valid date."),
            ("datetime_type", "Enter a valid date and time."),
            ("time_type", "Enter a valid time."),
            ("uuid_type", "Enter a valid UUID."),
            ("literal_error", "Select a valid choice."),
            ("enum", "Select a valid choice."),
        ],
    )
    def test_should_convert_all_pydantic_error_types(
        self, error_type, expected_message
    ):
        """All PYDANTIC_ERROR_MESSAGES entries should convert correctly."""
        # Arrange
        from typing import cast

        from pydantic_core import ErrorDetails

        form = SampleSchemaForm()
        error = cast(
            ErrorDetails,
            {
                "loc": ("field",),
                "type": error_type,
                "ctx": {},
                "msg": "Pydantic message",
            },
        )

        # Act
        field_name, message = form._convert_pydantic_error(error)

        # Assert
        assert message == expected_message


# =============================================================================
# Test Required vs Optional Fields
# =============================================================================


class TestRequiredFields:
    """Tests for required field handling."""

    def test_optional_fields_should_not_be_required(self):
        """Optional fields (X | None) should have required=False."""
        # Arrange
        form = SampleSchemaForm()

        # Act & Assert
        assert not form.fields["string_field"].required
        assert not form.fields["int_field"].required

    def test_required_fields_should_be_required(self):
        """Required fields should have required=True."""

        # Arrange
        class RequiredSchema(BaseModel):
            name: str
            age: int

        class RequiredForm(SchemaForm):
            class Meta:
                schema = RequiredSchema

        form = RequiredForm()

        # Act & Assert
        assert form.fields["name"].required
        assert form.fields["age"].required

    def test_field_with_default_should_not_be_required(self):
        """Fields with defaults should not be required."""

        # Arrange
        class DefaultSchema(BaseModel):
            name: str = "default"

        class DefaultForm(SchemaForm):
            class Meta:
                schema = DefaultSchema

        form = DefaultForm()

        # Act & Assert
        assert not form.fields["name"].required


# =============================================================================
# Test Boolean Field Handling
# =============================================================================


class TestBooleanFieldHandling:
    """Tests for boolean field special cases."""

    def test_optional_boolean_should_not_be_required(self):
        """Optional boolean field should not be required."""
        # Arrange
        form = SampleSchemaForm()

        # Act
        field = form.fields["bool_field"]

        # Assert
        assert isinstance(field, forms.BooleanField)
        assert not field.required

    def test_required_boolean_should_be_required(self):
        """Required boolean field should be required."""

        # Arrange
        class RequiredBoolSchema(BaseModel):
            accepted: bool

        class RequiredBoolForm(SchemaForm):
            class Meta:
                schema = RequiredBoolSchema

        form = RequiredBoolForm()

        # Act
        field = form.fields["accepted"]

        # Assert
        assert field.required


# =============================================================================
# Test Required Choice Fields
# =============================================================================


class TestRequiredChoiceFields:
    """Tests for required Literal/Enum fields (no empty choice)."""

    def test_required_literal_should_not_have_empty_choice(self):
        """Required Literal field should not have empty choice."""

        # Arrange
        class RequiredLiteralSchema(BaseModel):
            status: Literal["active", "inactive"]

        class RequiredLiteralForm(SchemaForm):
            class Meta:
                schema = RequiredLiteralSchema

        form = RequiredLiteralForm()

        # Act
        field = form.fields["status"]

        # Assert
        # First choice should NOT be empty
        assert field.choices[0][0] != ""
        assert field.choices == [("active", "active"), ("inactive", "inactive")]

    def test_required_enum_should_not_have_empty_choice(self):
        """Required Enum field should not have empty choice."""

        # Arrange
        class RequiredEnumSchema(BaseModel):
            option: SampleEnum

        class RequiredEnumForm(SchemaForm):
            class Meta:
                schema = RequiredEnumSchema

        form = RequiredEnumForm()

        # Act
        field = form.fields["option"]

        # Assert
        # First choice should NOT be empty
        assert field.choices[0][0] != ""
        assert len(field.choices) == 3  # Only the enum values


# =============================================================================
# Test Optional File Fields
# =============================================================================


class TestOptionalFileFields:
    """Tests for optional file/image fields with Union syntax."""

    def test_optional_file_upload_should_be_detected(self):
        """FileUpload | None should be detected as file field."""
        # Arrange - SampleSchema has optional file fields
        form = SampleSchemaForm()

        # Act & Assert
        assert "file_field" in form._file_field_names
        assert isinstance(form.fields["file_field"], forms.FileField)
        assert not form.fields["file_field"].required

    def test_optional_image_upload_should_be_detected(self):
        """ImageUpload | None should be detected as image field."""
        # Arrange - SampleSchema has optional image fields
        form = SampleSchemaForm()

        # Act & Assert
        assert "image_field" in form._file_field_names
        assert isinstance(form.fields["image_field"], forms.ImageField)
        assert not form.fields["image_field"].required


# =============================================================================
# Test Direct Field Constraints
# =============================================================================


class TestDirectFieldConstraints:
    """Tests for constraints set directly on FieldInfo (Pydantic Field kwargs)."""

    def test_should_extract_ge_from_field_info(self):
        """ge constraint from Field() should set min_value."""

        # Arrange
        class GeSchema(BaseModel):
            value: int = Field(ge=5)

        class GeForm(SchemaForm):
            class Meta:
                schema = GeSchema

        form = GeForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.min_value == 5

    def test_should_extract_gt_from_field_info(self):
        """gt constraint from Field() should set min_value."""

        # Arrange
        class GtSchema(BaseModel):
            value: int = Field(gt=0)

        class GtForm(SchemaForm):
            class Meta:
                schema = GtSchema

        form = GtForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.min_value == 0

    def test_should_extract_le_from_field_info(self):
        """le constraint from Field() should set max_value."""

        # Arrange
        class LeSchema(BaseModel):
            value: int = Field(le=100)

        class LeForm(SchemaForm):
            class Meta:
                schema = LeSchema

        form = LeForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.max_value == 100

    def test_should_extract_lt_from_field_info(self):
        """lt constraint from Field() should set max_value."""

        # Arrange
        class LtSchema(BaseModel):
            value: int = Field(lt=10)

        class LtForm(SchemaForm):
            class Meta:
                schema = LtSchema

        form = LtForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.max_value == 10

    def test_should_extract_min_length_from_field_info(self):
        """min_length constraint from Field() should be extracted."""

        # Arrange
        class MinLenSchema(BaseModel):
            value: str = Field(min_length=3)

        class MinLenForm(SchemaForm):
            class Meta:
                schema = MinLenSchema

        form = MinLenForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.min_length == 3

    def test_should_extract_max_length_from_field_info(self):
        """max_length constraint from Field() should be extracted."""

        # Arrange
        class MaxLenSchema(BaseModel):
            value: str = Field(max_length=50)

        class MaxLenForm(SchemaForm):
            class Meta:
                schema = MaxLenSchema

        form = MaxLenForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.max_length == 50

    def test_should_extract_decimal_constraints_from_field_info(self):
        """max_digits and decimal_places from Field() should be extracted."""

        # Arrange
        class DecimalSchema(BaseModel):
            value: Decimal = Field(max_digits=8, decimal_places=2)

        class DecimalForm(SchemaForm):
            class Meta:
                schema = DecimalSchema

        form = DecimalForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.max_digits == 8
        assert field.decimal_places == 2

    def test_should_extract_multiple_of_from_field_info(self):
        """multiple_of from Field() should set step attribute."""

        # Arrange
        class StepSchema(BaseModel):
            value: int = Field(multiple_of=5)

        class StepForm(SchemaForm):
            class Meta:
                schema = StepSchema

        form = StepForm()

        # Act
        field = form.fields["value"]

        # Assert
        assert field.widget.attrs.get("step") == 5


# =============================================================================
# Test File Field Validation with clean_ methods
# =============================================================================


class TestFileFieldCleanMethods:
    """Tests for custom clean_ methods on file fields."""

    def test_clean_method_called_for_file_field(self):
        """Custom clean_<fieldname> should be called for file fields."""

        # Arrange
        class FileSchema(BaseModel):
            document: FileUpload

        class FileFormWithClean(SchemaForm):
            class Meta:
                schema = FileSchema

            def clean_document(self):
                value = self.cleaned_data.get("document")
                if value and value.name == "forbidden.pdf":
                    raise forms.ValidationError("Forbidden file")
                return value

        file = SimpleUploadedFile(
            "test.pdf", b"content", content_type="application/pdf"
        )
        form = FileFormWithClean(data={}, files={"document": file})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert form.cleaned_data["document"] == file

    def test_clean_method_validation_error_for_file_field(self):
        """Validation error in clean_<fieldname> should add error."""

        # Arrange
        class FileSchema(BaseModel):
            document: FileUpload

        class FileFormWithClean(SchemaForm):
            class Meta:
                schema = FileSchema

            def clean_document(self):
                value = self.cleaned_data.get("document")
                if value and value.name == "forbidden.pdf":
                    raise forms.ValidationError("Forbidden file")
                return value

        file = SimpleUploadedFile(
            "forbidden.pdf", b"content", content_type="application/pdf"
        )
        form = FileFormWithClean(data={}, files={"document": file})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "document" in form.errors
        assert "Forbidden file" in str(form.errors["document"])


# =============================================================================
# Test File Field Cross-Field Validation with Pydantic
# =============================================================================


class TestFileFieldPydanticValidation:
    """Tests for Pydantic validation of file fields including cross-field validation."""

    def test_model_validator_can_access_file_field(self):
        """@model_validator should receive UploadedFileWrapper for file fields."""
        # Arrange

        from pydantic import model_validator

        class RequestType(str, Enum):
            TIME_OFF = "time_off"
            REIMBURSEMENT = "reimbursement"

        class RequestSchema(BaseModel):
            request_type: RequestType
            receipt: FileUpload | None = None

            @model_validator(mode="after")
            def validate_receipt_required(self) -> "RequestSchema":
                if self.request_type == RequestType.REIMBURSEMENT:
                    if not self.receipt:
                        raise ValueError(
                            "Receipt is required for reimbursement requests"
                        )
                return self

        class RequestForm(SchemaForm):
            class Meta:
                schema = RequestSchema

        file = SimpleUploadedFile(
            "receipt.pdf", b"file data", content_type="application/pdf"
        )
        form = RequestForm(
            data={"request_type": "reimbursement"},
            files={"receipt": file},
        )

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert form.cleaned_data["receipt"] == file

    def test_model_validator_raises_non_field_error_for_cross_field_validation(self):
        """Cross-field validation error should appear in non_field_errors."""
        # Arrange

        from pydantic import model_validator

        class RequestType(str, Enum):
            TIME_OFF = "time_off"
            REIMBURSEMENT = "reimbursement"

        class RequestSchema(BaseModel):
            request_type: RequestType
            receipt: FileUpload | None = None

            @model_validator(mode="after")
            def validate_receipt_required(self) -> "RequestSchema":
                if self.request_type == RequestType.REIMBURSEMENT:
                    if not self.receipt:
                        raise ValueError(
                            "Receipt is required for reimbursement requests"
                        )
                return self

        class RequestForm(SchemaForm):
            class Meta:
                schema = RequestSchema

        form = RequestForm(
            data={"request_type": "reimbursement"},
            files={},
        )

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "__all__" in form.errors
        assert "Receipt is required" in str(form.errors["__all__"])

    def test_field_validator_can_validate_file_size(self):
        """@field_validator should receive UploadedFileWrapper with .size attribute."""
        # Arrange
        from pydantic import field_validator

        class DocumentSchema(BaseModel):
            document: FileUpload

            @field_validator("document")
            @classmethod
            def validate_document_size(cls, v):
                if v and v.size > 100:
                    raise ValueError("Document must be under 100 bytes")
                return v

        class DocumentForm(SchemaForm):
            class Meta:
                schema = DocumentSchema

        large_file = SimpleUploadedFile(
            "large.pdf", b"x" * 200, content_type="application/pdf"
        )
        form = DocumentForm(data={}, files={"document": large_file})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "document" in form.errors
        assert "under 100 bytes" in str(form.errors["document"])

    def test_field_validator_can_validate_file_extension(self):
        """@field_validator should receive UploadedFileWrapper with .name attribute."""
        # Arrange
        from pydantic import field_validator

        class DocumentSchema(BaseModel):
            document: FileUpload

            @field_validator("document")
            @classmethod
            def validate_document_extension(cls, v):
                if v and not v.name.endswith((".pdf", ".doc", ".docx")):
                    raise ValueError("Document must be PDF or Word format")
                return v

        class DocumentForm(SchemaForm):
            class Meta:
                schema = DocumentSchema

        wrong_type = SimpleUploadedFile(
            "file.exe", b"content", content_type="application/octet-stream"
        )
        form = DocumentForm(data={}, files={"document": wrong_type})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "document" in form.errors
        assert "PDF or Word format" in str(form.errors["document"])

    def test_field_validator_can_validate_content_type(self):
        """@field_validator should receive UploadedFileWrapper with .content_type attribute."""
        # Arrange
        from pydantic import field_validator

        class DocumentSchema(BaseModel):
            document: FileUpload

            @field_validator("document")
            @classmethod
            def validate_content_type(cls, v):
                if v and not v.content_type.startswith("application/"):
                    raise ValueError("File must be an application type")
                return v

        class DocumentForm(SchemaForm):
            class Meta:
                schema = DocumentSchema

        wrong_type = SimpleUploadedFile(
            "file.txt", b"text content", content_type="text/plain"
        )
        form = DocumentForm(data={}, files={"document": wrong_type})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "document" in form.errors
        assert "application type" in str(form.errors["document"])

    def test_file_field_error_attaches_to_field_not_non_field_errors(self):
        """Errors from @field_validator on file fields should attach to the field."""
        # Arrange
        from pydantic import field_validator

        class DocumentSchema(BaseModel):
            document: FileUpload

            @field_validator("document")
            @classmethod
            def validate_document(cls, v):
                raise ValueError("Invalid document")

        class DocumentForm(SchemaForm):
            class Meta:
                schema = DocumentSchema

        file = SimpleUploadedFile(
            "test.pdf", b"content", content_type="application/pdf"
        )
        form = DocumentForm(data={}, files={"document": file})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "document" in form.errors
        assert "__all__" not in form.errors

    def test_optional_file_field_with_no_file_passes_none_to_validator(self):
        """Optional file field with no upload should pass None to validators."""
        # Arrange
        validator_received = []

        from pydantic import field_validator

        class OptionalFileSchema(BaseModel):
            document: FileUpload | None = None

            @field_validator("document")
            @classmethod
            def capture_value(cls, v):
                validator_received.append(v)
                return v

        class OptionalFileForm(SchemaForm):
            class Meta:
                schema = OptionalFileSchema

        form = OptionalFileForm(data={}, files={})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert len(validator_received) == 1
        assert validator_received[0] is None

    def test_cleaned_data_contains_original_uploaded_file(self):
        """After validation, cleaned_data should contain original UploadedFile, not wrapper."""
        # Arrange
        from django.core.files.uploadedfile import UploadedFile

        class FileSchema(BaseModel):
            document: FileUpload

        class FileForm(SchemaForm):
            class Meta:
                schema = FileSchema

        file = SimpleUploadedFile(
            "test.pdf", b"content", content_type="application/pdf"
        )
        form = FileForm(data={}, files={"document": file})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert is_valid
        assert isinstance(form.cleaned_data["document"], UploadedFile)
        assert form.cleaned_data["document"].name == "test.pdf"

    def test_model_validator_can_access_multiple_file_fields(self):
        """@model_validator should receive wrappers for all file fields."""
        # Arrange
        from pydantic import model_validator

        class MultiFileSchema(BaseModel):
            resume: FileUpload
            cover_letter: FileUpload | None = None

            @model_validator(mode="after")
            def validate_files(self) -> "MultiFileSchema":
                if self.resume and self.cover_letter:
                    if self.resume.size + self.cover_letter.size > 500:
                        raise ValueError("Total file size must be under 500 bytes")
                return self

        class MultiFileForm(SchemaForm):
            class Meta:
                schema = MultiFileSchema

        resume = SimpleUploadedFile(
            "resume.pdf", b"x" * 300, content_type="application/pdf"
        )
        cover = SimpleUploadedFile(
            "cover.pdf", b"x" * 300, content_type="application/pdf"
        )
        form = MultiFileForm(data={}, files={"resume": resume, "cover_letter": cover})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "__all__" in form.errors
        assert "under 500 bytes" in str(form.errors["__all__"])


# =============================================================================
# Test _post_clean Hook
# =============================================================================


class TestPostCleanHook:
    """Tests for the _post_clean hook method."""

    def test_post_clean_is_called_during_validation(self):
        """_post_clean should be called during form validation."""
        # Arrange
        post_clean_called = []

        class SimpleSchema(BaseModel):
            name: str

        class FormWithPostClean(SchemaForm):
            class Meta:
                schema = SimpleSchema

            def _post_clean(self):
                post_clean_called.append(True)

        form = FormWithPostClean(data={"name": "test"})

        # Act
        form.is_valid()

        # Assert
        assert post_clean_called == [True]

    def test_post_clean_can_add_validation_errors(self):
        """_post_clean can add cross-field validation errors."""

        # Arrange
        class RangeSchema(BaseModel):
            min_val: int
            max_val: int

        class RangeForm(SchemaForm):
            class Meta:
                schema = RangeSchema

            def _post_clean(self):
                min_val = self.cleaned_data.get("min_val")
                max_val = self.cleaned_data.get("max_val")
                if min_val is not None and max_val is not None and min_val > max_val:
                    self.add_error(None, "min_val must be less than max_val")

        form = RangeForm(data={"min_val": "10", "max_val": "5"})

        # Act
        is_valid = form.is_valid()

        # Assert
        assert not is_valid
        assert "__all__" in form.errors


# =============================================================================
# Browser Tests for Widget Rendering
# =============================================================================


@pytest.mark.browser
class TestWidgetRenderingBrowser:
    """Browser tests verifying actual HTML widget rendering using Playwright."""

    # --- Date/Time Widgets ---

    def test_should_render_date_input_with_type_date(
        self, render_form_to_file, page_from_file
    ):
        """DateField should render as <input type="date"> in the browser."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="date_field"]')

        # Assert
        assert input_element.get_attribute("type") == "date"

    def test_should_render_datetime_input_with_type_datetime_local(
        self, render_form_to_file, page_from_file
    ):
        """DateTimeField should render as <input type="datetime-local"> in the browser."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="datetime_field"]')

        # Assert
        assert input_element.get_attribute("type") == "datetime-local"

    def test_should_render_time_input_with_type_time(
        self, render_form_to_file, page_from_file
    ):
        """TimeField should render as <input type="time"> in the browser."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="time_field"]')

        # Assert
        assert input_element.get_attribute("type") == "time"

    # --- Constrained Date/Datetime min/max Attributes ---

    def test_should_render_past_date_with_max_attribute(
        self, render_form_to_file, page_from_file
    ):
        """PastDate field should render with max attribute set to today."""
        # Arrange
        with patch("schemaform.forms.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 22)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            class PastDateSchema(BaseModel):
                past_date: PastDate

            class PastDateForm(SchemaForm):
                class Meta:
                    schema = PastDateSchema

            form = PastDateForm()
            file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="past_date"]')

        # Assert
        assert input_element.get_attribute("max") == "2026-01-22"

    def test_should_render_future_date_with_min_attribute(
        self, render_form_to_file, page_from_file
    ):
        """FutureDate field should render with min attribute set to today."""
        # Arrange
        with patch("schemaform.forms.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 22)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            class FutureDateSchema(BaseModel):
                future_date: FutureDate

            class FutureDateForm(SchemaForm):
                class Meta:
                    schema = FutureDateSchema

            form = FutureDateForm()
            file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="future_date"]')

        # Assert
        assert input_element.get_attribute("min") == "2026-01-22"

    def test_should_render_past_datetime_with_max_attribute(
        self, render_form_to_file, page_from_file
    ):
        """PastDatetime field should render with max attribute set to now."""
        # Arrange
        with patch("schemaform.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 22, 14, 30)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            class PastDatetimeSchema(BaseModel):
                past_datetime: PastDatetime

            class PastDatetimeForm(SchemaForm):
                class Meta:
                    schema = PastDatetimeSchema

            form = PastDatetimeForm()
            file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="past_datetime"]')

        # Assert
        assert input_element.get_attribute("max") == "2026-01-22T14:30"

    def test_should_render_future_datetime_with_min_attribute(
        self, render_form_to_file, page_from_file
    ):
        """FutureDatetime field should render with min attribute set to now."""
        # Arrange
        with patch("schemaform.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 22, 14, 30)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            class FutureDatetimeSchema(BaseModel):
                future_datetime: FutureDatetime

            class FutureDatetimeForm(SchemaForm):
                class Meta:
                    schema = FutureDatetimeSchema

            form = FutureDatetimeForm()
            file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="future_datetime"]')

        # Assert
        assert input_element.get_attribute("min") == "2026-01-22T14:30"

    # --- Password Widget ---

    def test_should_render_password_input_for_secret_field(
        self, render_form_to_file, page_from_file
    ):
        """SecretStr field should render as <input type="password"> in the browser."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="secret_field"]')

        # Assert
        assert input_element.get_attribute("type") == "password"

    # --- Choice/Select Widgets ---

    def test_should_render_select_for_literal_field(
        self, render_form_to_file, page_from_file
    ):
        """Literal field should render as <select> with options."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        select_element = page.locator('select[name="literal_field"]')
        options = select_element.locator("option")

        # Assert
        assert select_element.count() == 1
        # Optional field has empty choice + 3 literal values
        assert options.count() == 4
        # First option should be empty (for optional field)
        assert options.nth(0).get_attribute("value") == ""

    def test_should_render_select_for_enum_field(
        self, render_form_to_file, page_from_file
    ):
        """Enum field should render as <select> with options from enum values."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        select_element = page.locator('select[name="enum_field"]')
        options = select_element.locator("option")

        # Assert
        assert select_element.count() == 1
        # Optional field has empty choice + 3 enum values
        assert options.count() == 4

    def test_should_render_select_without_empty_option_for_required_choice(
        self, render_form_to_file, page_from_file
    ):
        """Required choice field should not have empty option."""

        # Arrange
        class RequiredChoiceSchema(BaseModel):
            status: Literal["active", "inactive"]

        class RequiredChoiceForm(SchemaForm):
            class Meta:
                schema = RequiredChoiceSchema

        form = RequiredChoiceForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        select_element = page.locator('select[name="status"]')
        options = select_element.locator("option")

        # Assert
        assert options.count() == 2
        # First option should NOT be empty
        assert options.nth(0).get_attribute("value") != ""

    # --- File/Image Widgets ---

    def test_should_render_file_input_for_file_field(
        self, render_form_to_file, page_from_file
    ):
        """FileUpload field should render as <input type="file">."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="file_field"]')

        # Assert
        assert input_element.get_attribute("type") == "file"

    def test_should_render_file_input_for_image_field(
        self, render_form_to_file, page_from_file
    ):
        """ImageUpload field should render as <input type="file">."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="image_field"]')

        # Assert
        assert input_element.get_attribute("type") == "file"

    # --- Label and Help Text ---

    def test_should_render_label_from_field_title(
        self, render_form_to_file, page_from_file
    ):
        """Field with title should render label with custom title text."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        label_element = page.locator('label[for="id_titled_field"]')

        # Assert
        assert "Custom Title" in label_element.text_content()

    def test_should_render_help_text_from_description(
        self, render_form_to_file, page_from_file
    ):
        """Field with description should render help text."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        # Django renders help text in a span with class 'helptext'
        help_text = page.locator(".helptext")

        # Assert
        assert "This is help text" in help_text.all_text_contents()[0]

    # --- Constraint Attributes ---

    def test_should_render_minlength_maxlength_on_text_input(
        self, render_form_to_file, page_from_file
    ):
        """Constrained string field should render with minlength and maxlength attributes."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="constrained_string"]')

        # Assert
        assert input_element.get_attribute("minlength") == "3"
        assert input_element.get_attribute("maxlength") == "100"

    def test_should_render_step_attribute_on_numeric_input(
        self, render_form_to_file, page_from_file
    ):
        """Field with multiple_of should render with step attribute."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="step_number"]')

        # Assert
        assert input_element.get_attribute("step") == "5"

    def test_should_render_min_max_on_constrained_int_input(
        self, render_form_to_file, page_from_file
    ):
        """Constrained int field should render with min and max attributes."""
        # Arrange
        form = SampleSchemaForm()
        file_path = render_form_to_file(form)

        # Act
        page = page_from_file(file_path)
        input_element = page.locator('input[name="constrained_int"]')

        # Assert
        assert input_element.get_attribute("min") == "0"
        assert input_element.get_attribute("max") == "1000"
