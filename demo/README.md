# django-schemaform Demo

A showcase Django application demonstrating django-schemaform features with real-world form examples.

## Setup

```bash
cd demo
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## Demo Forms

The demo includes six forms showcasing different django-schemaform capabilities:

| Form | Features Demonstrated |
|------|----------------------|
| **Contact Form** | `EmailStr`, `time` field, `Literal` choices, basic validation |
| **User Registration** | `SecretStr` password fields, `PastDate`, `@model_validator` for password matching |
| **Event Booking** | `date`/`time` fields, `Decimal` with constraints, `Enum` choices, cross-field validation |
| **Product Review** | `UUID`, integer rating with `ge`/`le` range (1-5), optional `ImageUpload` |
| **Job Application** | `FileUpload` with `@field_validator` (size/type), `HttpUrl`, `Enum`, `Decimal` salary |
| **Medical Appointment** | `FutureDatetime`, `Enum` selection, sensitive data handling |

Each form page displays both the rendered form and the source code for its Pydantic schema, so you can see exactly how each feature works.

## Project Structure

```
demo/
├── manage.py
├── demo_project/          # Django settings
│   └── settings.py
└── showcase/              # Demo app
    ├── schemas.py         # Pydantic models
    ├── forms.py           # SchemaForm classes
    ├── views.py           # Form views with source display
    └── templates/         # HTML templates
```

## Requirements

- Python ≥ 3.14
- Django ≥ 5.2
- django-crispy-forms + crispy-bootstrap5 (for styled form rendering)
