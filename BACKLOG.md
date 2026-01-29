# django-schemaform Backlog

Features and improvements deferred for future development.

## Currently Supported Features

The following are **fully implemented and tested**:

### Field Types
- **Basic types:** str, int, float, Decimal, bool, date, datetime, time, timedelta, UUID
- **Pydantic types:** EmailStr, HttpUrl, AnyUrl, SecretStr
- **File types:** FileUpload, ImageUpload (with UploadedFileWrapper for validator access)
- **Choice types:** Literal, Enum (including optional variants)
- **Constrained date/time:** PastDate, FutureDate, PastDatetime, FutureDatetime, AwareDatetime, NaiveDatetime

### Field Configuration
- Labels (from field names or Pydantic Field title)
- Help text (from Pydantic Field description)
- Required/optional fields (including `T | None` syntax)
- Default values

### Constraints
- Numeric: Ge, Gt, Le, Lt (min_value, max_value)
- String: MinLen, MaxLen (min_length, max_length)
- Decimal: max_digits, decimal_places
- Extracted from both metadata and Field() kwargs

### Validation
- **Pydantic as single source of truth:** All validation via Pydantic schema
- **@field_validator:** Single-field validation including file size, extension, content type
- **@model_validator:** Cross-field validation (e.g., conditional file requirements, password confirmation)
- **UploadedFileWrapper:** File fields receive wrapper with `.name`, `.size`, `.content_type` in validators
- **Django file handling:** Django handles mechanical file upload parsing
- **User-friendly error messages:** Custom ValueError messages passed through to form errors
- **Field-specific errors:** Validator errors attach to correct fields
- **Custom clean_<fieldname> methods:** Still supported for Django-specific validation

### Widgets
- HTML5 widgets for date/time fields
- Automatic widget selection based on field type
- Choice widgets for Literal/Enum types

---

## Deferred Features

### Nested Pydantic Models

**Description:** Support nested Pydantic models rendered as fieldsets or inline forms.

**Example:**
```python
class Address(BaseModel):
    street: str
    city: str
    zip_code: str

class Person(BaseModel):
    name: str
    address: Address  # Nested model
```

**Considerations:**
- Render as Django fieldset with prefix
- Handle nested validation errors (multi-level `loc`)
- Consider inline formsets for `list[NestedModel]`

---

### List and Collection Types

**Description:** Support `list[T]`, `set[T]`, and other collection types.

**Example:**
```python
class Survey(BaseModel):
    tags: list[str]
    scores: list[int]
```

**Considerations:**
- Render as `MultipleChoiceField` for `list[Literal[...]]`
- Use JavaScript-enhanced widgets for dynamic list entry
- Handle `list[NestedModel]` as inline formsets

---

### SlugField and RegexField Support

**Description:** Map Pydantic `pattern` constraint to Django `SlugField` or `RegexField`.

**Considerations:**
- Detect slug pattern (`^[-a-zA-Z0-9_]+$`) for `SlugField`
- Use `RegexField` for arbitrary patterns
- Extract `pattern` from `FieldInfo.metadata`

---

### IPAddressField Support

**Description:** Support `IPv4Address`, `IPv6Address` from Python's `ipaddress` module.

**Considerations:**
- Map to Django's `GenericIPAddressField`
- Handle protocol specification (IPv4-only, IPv6-only, both)

---

### JSONField Support

**Description:** Support `dict` and `list` types as JSON fields.

**Example:**
```python
class Config(BaseModel):
    settings: dict[str, Any]
    items: list[dict[str, str]]
```

**Considerations:**
- Use Django's `JSONField` widget
- Pydantic handles JSON validation naturally
- Consider code editor widget for better UX

---

## Technical Debt

None currently identified. All core functionality is implemented and tested.

---

## Design Decisions: Features We Won't Implement

### Custom Widget Overrides via Schema Metadata

**Why not implement:** Django already provides a clean, standard way to customize widgets via `__init__`:

```python
class MySchema(BaseModel):
    content: str

class MySchemaForm(SchemaForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget = forms.Textarea(attrs={'rows': 10})
    
    class Meta:
        schema = MySchema
```

This approach is:
- **More explicit:** Widget customization is clearly visible in the form class
- **More flexible:** Full access to Django's widget API and attrs
- **More standard:** Uses Django's established patterns
- **No magic:** Doesn't require learning new conventions in json_schema_extra

Users can also override fields completely for more complex customizations:

```python
class MySchemaForm(SchemaForm):
    content = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        schema = MySchema
```

**Recommendation:** Use Django's standard field/widget customization patterns rather than adding schema-based overrides.
