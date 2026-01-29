"""Real-world forms demonstrating SchemaForm capabilities."""

import inspect
import textwrap

from schemaform import SchemaForm

from .schema import (
    ContactRequest,
    EventBooking,
    JobApplication,
    MedicalAppointment,
    ProductReview,
    UserRegistration,
)


class BaseForm(SchemaForm):
    """Base form with source code inspection capability."""

    @classmethod
    def get_source_code(cls) -> str:
        """Return the source code of this form class for display."""
        source = inspect.getsource(cls)
        return textwrap.dedent(source)


class ContactForm(BaseForm):
    """Simple contact form - basic fields and choices."""

    class Meta:
        schema = ContactRequest


class UserRegistrationForm(BaseForm):
    """User registration with password confirmation validation.

    Note: Password matching and terms validation is handled by the
    UserRegistration schema's @model_validator. No form-level clean() needed.
    """

    class Meta:
        schema = UserRegistration


class EventBookingForm(BaseForm):
    """Event booking form with date/time and budget fields.

    Note: Time validation (end_time > start_time) is handled by the
    EventBooking schema's @model_validator. No form-level clean() needed.
    """

    class Meta:
        schema = EventBooking


class ProductReviewForm(BaseForm):
    """Product review form with rating and optional photo."""

    class Meta:
        schema = ProductReview


class JobApplicationForm(BaseForm):
    """Job application form with file upload validation.

    Note: Resume file type and size validation is handled by the
    JobApplication schema's @field_validator. No form-level clean_resume() needed.
    """

    class Meta:
        schema = JobApplication


class MedicalAppointmentForm(BaseForm):
    """Medical appointment scheduling form."""

    class Meta:
        schema = MedicalAppointment
