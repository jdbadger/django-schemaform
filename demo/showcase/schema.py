"""Real-world schemas demonstrating SchemaForm capabilities."""

import inspect
import textwrap
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    FutureDatetime,
    HttpUrl,
    PastDate,
    SecretStr,
    field_validator,
    model_validator,
)

from schemaform import FileUpload, ImageUpload


class BaseSchema(BaseModel):
    """Base schema with source code inspection capability."""

    @classmethod
    def get_source_code(cls) -> str:
        """Return the source code of this schema class for display."""
        source = inspect.getsource(cls)
        # Dedent to remove leading whitespace
        return textwrap.dedent(source)


# =============================================================================
# 1. Contact Request - Simple form with basic fields
# =============================================================================


class ContactRequest(BaseSchema):
    """Simple contact form with basic field types and choices."""

    name: str = Field(min_length=2, max_length=100, description="Your full name")
    email: EmailStr = Field(description="We'll never share your email")
    phone: str | None = Field(
        default=None, max_length=20, description="Optional phone number"
    )
    preferred_contact: Literal["email", "phone", "either"] = Field(
        default="email", description="How should we reach you?"
    )
    preferred_time: time | None = Field(
        default=None, description="Best time to contact you"
    )
    subject: str = Field(min_length=5, max_length=200)
    message: str = Field(
        min_length=20, max_length=5000, description="Tell us how we can help"
    )
    urgent: bool = Field(
        default=False, description="Check if this requires immediate attention"
    )


# =============================================================================
# 2. User Registration - Password fields and cross-field validation
# =============================================================================


class UserRegistration(BaseSchema):
    """User registration with password confirmation and terms acceptance.

    Demonstrates cross-field validation using @model_validator:
    - Passwords must match
    - Terms must be accepted
    """

    email: EmailStr = Field(description="Your email address")
    password: SecretStr = Field(min_length=8, description="At least 8 characters")
    password_confirm: SecretStr = Field(description="Re-enter your password")
    full_name: str = Field(min_length=2, max_length=100, description="Your full name")
    date_of_birth: PastDate = Field(description="Must be a date in the past")
    newsletter: bool = Field(default=False, description="Receive updates and tips")
    accepted_terms: bool = Field(description="You must accept the terms to continue")

    @model_validator(mode="after")
    def validate_registration(self) -> "UserRegistration":
        """Validate password confirmation and terms acceptance."""
        # Check passwords match
        password = self.password.get_secret_value()
        password_confirm = self.password_confirm.get_secret_value()
        if password != password_confirm:
            raise ValueError(
                "Passwords do not match. Please enter the same password in both fields."
            )

        # Check terms accepted
        if not self.accepted_terms:
            raise ValueError("You must accept the terms and conditions.")

        return self


# =============================================================================
# 3. Event Booking - Dates, times, decimals, and constraints
# =============================================================================


class RoomType(str, Enum):
    """Available room types for events."""

    CONFERENCE = "conference"
    BALLROOM = "ballroom"
    GARDEN = "garden"
    ROOFTOP = "rooftop"


class EventBooking(BaseSchema):
    """Event booking form with dates, times, and budget constraints.

    Demonstrates cross-field validation using @model_validator:
    - End time must be after start time
    """

    event_name: str = Field(min_length=3, max_length=100, description="Name your event")
    event_date: date = Field(description="When should the event take place?")
    start_time: time = Field(description="Event start time")
    end_time: time = Field(description="Event end time")
    event_type: Literal["conference", "wedding", "birthday", "corporate", "other"] = (
        Field(description="Type of event")
    )
    guest_count: int = Field(ge=1, le=500, description="Number of guests (1-500)")
    room_preference: RoomType | None = Field(
        default=None, description="Preferred venue room"
    )
    budget: Decimal = Field(
        ge=Decimal("100.00"),
        max_digits=10,
        decimal_places=2,
        description="Budget in USD (minimum $100)",
    )
    special_requests: str | None = Field(
        default=None, max_length=500, description="Dietary needs, accessibility, etc."
    )
    needs_catering: bool = Field(
        default=False, description="Include catering services?"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "EventBooking":
        """Validate that end_time is after start_time."""
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time.")
        return self


# =============================================================================
# 4. Product Review - UUID, ratings, and optional image
# =============================================================================


class ProductReview(BaseSchema):
    """Product review form with star rating and optional photo."""

    product_id: UUID = Field(description="Product identifier")
    rating: int = Field(ge=1, le=5, description="Rate from 1 to 5 stars")
    title: str = Field(
        min_length=5, max_length=100, description="Summarize your experience"
    )
    review_text: str = Field(
        min_length=20,
        max_length=2000,
        description="Share details about your experience",
    )
    recommend: bool = Field(description="Would you recommend this product?")
    verified_purchase: bool = Field(
        default=False, description="I purchased this product"
    )
    photo: ImageUpload | None = Field(
        default=None, description="Add a photo of the product"
    )


# =============================================================================
# 5. Job Application - File uploads, URLs, and enums
# =============================================================================


class ExperienceLevel(str, Enum):
    """Experience levels for job applications."""

    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class JobApplication(BaseSchema):
    """Job application form with resume upload and professional links.

    Demonstrates file validation using @field_validator:
    - Resume must be PDF or Word format
    - Resume must be under 5MB
    """

    full_name: str = Field(
        min_length=2, max_length=100, description="Your full legal name"
    )
    email: EmailStr = Field(description="Professional email address")
    phone: str = Field(min_length=10, max_length=20, description="Contact phone number")
    experience_level: ExperienceLevel = Field(
        description="Your current experience level"
    )
    resume: FileUpload = Field(description="Upload your resume (PDF preferred)")
    photo: ImageUpload | None = Field(
        default=None, description="Professional headshot (optional)"
    )
    portfolio_url: HttpUrl | None = Field(
        default=None, description="Link to your portfolio"
    )
    linkedin_url: HttpUrl | None = Field(
        default=None, description="LinkedIn profile URL"
    )
    available_from: date = Field(description="Earliest start date")
    expected_salary: Decimal = Field(
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Expected annual salary in USD",
    )
    cover_letter: str | None = Field(
        default=None,
        max_length=2000,
        description="Why are you interested in this position?",
    )

    @field_validator("resume")
    @classmethod
    def validate_resume(cls, v):
        """Validate resume file type and size."""
        if v is None:
            return v

        # Check file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if v.size > max_size:
            raise ValueError("Resume file size must be under 5MB.")

        # Check file extension
        allowed_extensions = (".pdf", ".doc", ".docx")
        if not v.name.lower().endswith(allowed_extensions):
            raise ValueError(
                "Resume must be a PDF or Word document (.pdf, .doc, .docx)."
            )

        return v


# =============================================================================
# 6. Medical Appointment - Sensitive data and datetime
# =============================================================================


class MedicalDepartment(str, Enum):
    """Hospital departments for appointments."""

    GENERAL = "general"
    CARDIOLOGY = "cardiology"
    DERMATOLOGY = "dermatology"
    NEUROLOGY = "neurology"
    ORTHOPEDICS = "orthopedics"
    PEDIATRICS = "pediatrics"
    PSYCHIATRY = "psychiatry"


class MedicalAppointment(BaseSchema):
    """Medical appointment scheduling with patient information."""

    patient_name: str = Field(
        min_length=2, max_length=100, description="Patient's full name"
    )
    date_of_birth: PastDate = Field(description="Patient's date of birth")
    email: EmailStr = Field(description="Email for appointment confirmation")
    phone: str = Field(
        min_length=10, max_length=20, description="Emergency contact number"
    )
    department: MedicalDepartment = Field(description="Medical department")
    preferred_datetime: FutureDatetime = Field(
        description="Preferred appointment date and time (must be in the future)"
    )
    symptoms: str = Field(max_length=1000, description="Briefly describe your symptoms")
    is_new_patient: bool = Field(description="Is this your first visit?")
    insurance_id: str | None = Field(
        default=None, max_length=50, description="Insurance ID (if applicable)"
    )
    emergency: bool = Field(default=False, description="Is this an emergency?")
