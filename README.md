<p align="center">
  <img src="assets/djangoschemaform.png" alt="django-schemaform" width="400">
</p>

<p align="center">
  <strong>Django forms from Pydantic models</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/django-schemaform/"><img src="https://img.shields.io/pypi/v/django-schemaform.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/django-schemaform/"><img src="https://img.shields.io/pypi/pyversions/django-schemaform.svg" alt="Python"></a>
  <a href="https://github.com/joebadger/django-schemaform/blob/main/LICENSE.md"><img src="https://img.shields.io/badge/license-BSD--3--Clause-blue.svg" alt="License"></a>
</p>

---

**django-schemaform** lets you define your form schema once using Pydantic and get a fully-featured Django form with automatic field mapping, constraints, and validation.

## Installation

```bash
uv add django-schemaform
```

Or with pip:

```bash
pip install django-schemaform
```

## Quick Start

Define a Pydantic model and create a form:

```python
from pydantic import BaseModel, EmailStr, Field
from schemaform import SchemaForm


class ContactSchema(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(min_length=10, description="Your message to us")


class ContactForm(SchemaForm):
    class Meta:
        schema = ContactSchema
```

Use it in your Django view:

```python
from django.shortcuts import render, redirect


def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.validated_data  # Pydantic model instance
            # process data...
            return redirect("success")
    else:
        form = ContactForm()
    
    return render(request, "contact.html", {"form": form})
```

That's it! The form automatically:
- Maps `str` → `CharField`, `EmailStr` → `EmailField`
- Applies `min_length`/`max_length` constraints
- Uses the `description` as help text
- Validates through Pydantic on submit

## Field Type Mapping

### Core Python Types

| Python Type | Django Field |
|-------------|--------------|
| `str` | `CharField` |
| `int` | `IntegerField` |
| `float` | `FloatField` |
| `bool` | `BooleanField` |
| `Decimal` | `DecimalField` |
| `date` | `DateField` |
| `time` | `TimeField` |
| `datetime` | `DateTimeField` |
| `timedelta` | `DurationField` |
| `UUID` | `UUIDField` |

### Pydantic Types

| Pydantic Type | Django Field |
|---------------|--------------|
| `EmailStr` | `EmailField` |
| `HttpUrl` | `URLField` |
| `AnyUrl` | `URLField` |
| `SecretStr` | `CharField` (password widget) |
| `Json` | `JSONField` |
| `PastDate` | `DateField` |
| `FutureDate` | `DateField` |
| `PastDatetime` | `DateTimeField` |
| `FutureDatetime` | `DateTimeField` |

### File Upload Types

| SchemaForm Type | Django Field |
|-----------------|--------------|
| `FileUpload` | `FileField` |
| `ImageUpload` | `ImageField` |

```python
from schemaform import SchemaForm, FileUpload, ImageUpload

class UploadSchema(BaseModel):
    document: FileUpload
    photo: ImageUpload | None = None  # Optional
```

### Choice Fields

| Python Type | Django Field |
|-------------|--------------|
| `Literal["a", "b", "c"]` | `ChoiceField` |
| `enum.Enum` subclass | `ChoiceField` |

```python
from typing import Literal
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskSchema(BaseModel):
    status: Literal["pending", "done"]
    priority: Priority
    category: Priority | None = None  # Optional - adds empty choice
```

### Constraint Mapping

| Pydantic Constraint | Django Field Attribute |
|---------------------|------------------------|
| `min_length` | `min_length` |
| `max_length` | `max_length` |
| `ge` / `gt` | `min_value` |
| `le` / `lt` | `max_value` |
| `max_digits` | `max_digits` (Decimal) |
| `decimal_places` | `decimal_places` (Decimal) |
| `pattern` | `validators` (RegexValidator) |

### Labels and Help Text

Field metadata from Pydantic is automatically applied:

```python
class ProfileSchema(BaseModel):
    username: str = Field(
        title="Username",           # → label
        description="Choose wisely" # → help_text
    )
```

## Validation

### Single-Field Validation

Use Pydantic's `@field_validator` for field-level validation:

```python
from pydantic import BaseModel, field_validator
from schemaform import SchemaForm, FileUpload


class UploadSchema(BaseModel):
    resume: FileUpload

    @field_validator("resume")
    @classmethod
    def validate_resume(cls, v):
        if v.size > 5 * 1024 * 1024:  # 5MB
            raise ValueError("File must be under 5MB")
        if not v.content_type == "application/pdf":
            raise ValueError("Only PDF files allowed")
        return v
```

### Cross-Field Validation

Use `@model_validator` for validation across multiple fields:

```python
from pydantic import BaseModel, SecretStr, model_validator
from schemaform import SchemaForm


class RegistrationSchema(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    password_confirm: SecretStr

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password.get_secret_value() != self.password_confirm.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class RegistrationForm(SchemaForm):
    class Meta:
        schema = RegistrationSchema
```

Validation errors are automatically mapped to the appropriate form fields or to `__all__` for non-field errors.

## Demo Application

A demo Django application is included with example forms showcasing various features:

- **Contact Form** — Email, time fields, Literal choices
- **User Registration** — SecretStr passwords, PastDate, password matching validation
- **Event Booking** — Date/time, Decimal constraints, Enum choices, cross-field validation
- **Product Review** — UUID, integer rating with range, optional ImageUpload
- **Job Application** — FileUpload with validation, HttpUrl, Enum, Decimal
- **Medical Appointment** — FutureDatetime, Enum, sensitive data handling

See [demo/README.md](demo/README.md) for setup instructions.

## Requirements

- Python ≥ 3.12
- Django ≥ 5.2, < 6.0
- Pydantic ≥ 2.0, < 3.0

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

BSD-3-Clause — see [LICENSE.md](LICENSE.md) for details.
