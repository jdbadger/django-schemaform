"""Pytest configuration for SchemaForm tests."""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Literal
from uuid import UUID

import pytest
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

from schemaform import FileUpload, ImageUpload, SchemaForm


def pytest_configure() -> None:
    """Configure minimal Django settings for template rendering."""
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={},
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
            ],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "APP_DIRS": False,
                    "OPTIONS": {
                        "context_processors": [],
                    },
                }
            ],
            USE_TZ=True,
            FORMS_URLFIELD_ASSUME_HTTPS=True,
        )
        django.setup()


class SampleEnum(str, Enum):
    """Sample enum for testing choice fields."""

    OPTION_A = "option_a"
    OPTION_B = "option_b"
    OPTION_C = "option_c"


class SampleSchema(BaseModel):
    """
    Sample schema covering all supported field types for testing.

    All fields are optional and constrained (if applicable) to facilitate comprehensive testing.
    """

    # Basic types
    string_field: str | None = None
    int_field: int | None = None
    float_field: float | None = None
    decimal_field: Decimal | None = None
    bool_field: bool | None = None
    date_field: date | None = None
    datetime_field: datetime | None = None
    time_field: time | None = None
    duration_field: timedelta | None = None
    uuid_field: UUID | None = None

    # Pydantic special types
    email_field: EmailStr | None = None
    http_url_field: HttpUrl | None = None
    any_url_field: AnyUrl | None = None
    secret_field: SecretStr | None = None

    # Constrained date/datetime types
    past_date_field: PastDate | None = None
    future_date_field: FutureDate | None = None
    past_datetime_field: PastDatetime | None = None
    future_datetime_field: FutureDatetime | None = None
    aware_datetime_field: AwareDatetime | None = None
    naive_datetime_field: NaiveDatetime | None = None

    # Choice types
    literal_field: Literal["option_a", "option_b", "option_c"] | None = None
    enum_field: SampleEnum | None = None

    # File types
    file_field: FileUpload | None = None
    image_field: ImageUpload | None = None

    # Constrained fields
    constrained_string: str | None = Field(default=None, min_length=3, max_length=100)
    constrained_int: int | None = Field(default=None, ge=0, le=1000)
    constrained_float: float | None = Field(default=None, gt=0.0, lt=100.0)
    constrained_decimal: Decimal | None = Field(
        default=None, max_digits=10, decimal_places=2, ge=Decimal("0.00")
    )
    step_number: int | None = Field(default=None, multiple_of=5)

    # Field metadata
    titled_field: str | None = Field(default=None, title="Custom Title")
    described_field: str | None = Field(default=None, description="This is help text")
    aliased_field: str | None = Field(default=None, alias="customAlias")


class SampleSchemaForm(SchemaForm):
    """Sample form for testing SchemaForm functionality."""

    class Meta:
        schema = SampleSchema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def html_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for static HTML files."""
    html_path = tmp_path / "html"
    html_path.mkdir(exist_ok=True)
    return html_path


@pytest.fixture
def render_form_to_file(html_dir: Path) -> Callable:
    """Render a SchemaForm to a static HTML file.

    Returns a callable that accepts a form instance and optional filename,
    writes a complete HTML document to the temporary directory, and returns
    the file path.
    """
    from django.forms import BaseForm

    def _render(form: BaseForm, filename: str = "form.html") -> Path:
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SchemaForm Test</title>
    <style>
        .errorlist {{ color: red; list-style: none; padding: 0; }}
        label {{ display: block; margin-top: 10px; font-weight: bold; }}
        input, select, textarea {{ display: block; margin-bottom: 5px; }}
        .helptext {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <form method="post" id="test-form">
        {form.as_p()}
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""
        file_path = html_dir / filename
        file_path.write_text(html_content)
        return file_path

    return _render


@pytest.fixture
def page_from_file(page):
    """Navigate a Playwright page to a local file.

    Returns a callable that accepts a file path, navigates to it using
    the file:// protocol, and returns the page ready for assertions.
    """

    def _navigate(file_path: Path):
        page.goto(f"file://{file_path.absolute()}")
        return page

    return _navigate
