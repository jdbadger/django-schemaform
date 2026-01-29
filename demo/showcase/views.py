"""Showcase views for demonstrating SchemaForm with real-world examples."""

from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import (
    ContactForm,
    EventBookingForm,
    JobApplicationForm,
    MedicalAppointmentForm,
    ProductReviewForm,
    UserRegistrationForm,
)
from .schema import (
    ContactRequest,
    EventBooking,
    JobApplication,
    MedicalAppointment,
    ProductReview,
    UserRegistration,
)


class IndexView(TemplateView):
    """Index page listing all available form demonstrations."""

    template_name = "showcase/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["forms"] = [
            {
                "name": "Contact Form",
                "description": "Simple contact form with email, choices, and validation",
                "url": "showcase:contact",
                "badges": ["✉️ Email", "🕐 Time", "💬 Choices"],
            },
            {
                "name": "User Registration",
                "description": "Registration with password confirmation and terms acceptance",
                "url": "showcase:registration",
                "badges": ["🔒 Password", "📅 Date", "✅ Cross-Validation"],
            },
            {
                "name": "Event Booking",
                "description": "Book events with dates, times, budget, and guest limits",
                "url": "showcase:booking",
                "badges": ["📅 Date/Time", "💰 Decimal", "🔢 Constraints"],
            },
            {
                "name": "Product Review",
                "description": "Submit reviews with star ratings and optional photos",
                "url": "showcase:review",
                "badges": ["⭐ Rating", "🖼️ Image", "🆔 UUID"],
            },
            {
                "name": "Job Application",
                "description": "Apply with resume upload, portfolio links, and salary expectations",
                "url": "showcase:application",
                "badges": ["📁 File Upload", "🔗 URL", "💼 Enum"],
            },
            {
                "name": "Medical Appointment",
                "description": "Schedule appointments with patient info and department selection",
                "url": "showcase:medical",
                "badges": ["🏥 DateTime", "📋 Enum", "🔐 Sensitive"],
            },
        ]
        return context


class BaseSchemaFormView(FormView):
    """Base view for schema form demonstrations."""

    template_name = "showcase/form.html"
    schema_class = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = self.form_title
        context["form_description"] = self.form_description
        if self.schema_class:
            context["schema_source"] = self.schema_class.get_source_code()
            context["schema_name"] = self.schema_class.__name__
        if self.form_class and hasattr(self.form_class, "get_source_code"):
            context["form_source"] = self.form_class.get_source_code()
        return context

    def form_valid(self, form):
        # Convert form data to session-storable format
        cleaned_data = {}
        for key, value in form.cleaned_data.items():
            if hasattr(value, "name"):  # File objects
                cleaned_data[key] = f"📎 {value.name}"
            elif hasattr(value, "get_secret_value"):  # SecretStr
                cleaned_data[key] = "••••••••"
            elif value is None:
                cleaned_data[key] = None
            else:
                cleaned_data[key] = str(value)
        self.request.session["form_data"] = cleaned_data
        self.request.session["form_title"] = self.form_title
        return super().form_valid(form)


class ContactFormView(BaseSchemaFormView):
    """Contact form demonstration."""

    form_class = ContactForm
    schema_class = ContactRequest
    success_url = reverse_lazy("showcase:contact-success")
    form_title = "Contact Form"
    form_description = "A simple contact form with email, phone preference, and message fields."


class UserRegistrationFormView(BaseSchemaFormView):
    """User registration form demonstration."""

    form_class = UserRegistrationForm
    schema_class = UserRegistration
    success_url = reverse_lazy("showcase:registration-success")
    form_title = "User Registration"
    form_description = "Registration form with password confirmation, date of birth, and terms acceptance."


class EventBookingFormView(BaseSchemaFormView):
    """Event booking form demonstration."""

    form_class = EventBookingForm
    schema_class = EventBooking
    success_url = reverse_lazy("showcase:booking-success")
    form_title = "Event Booking"
    form_description = "Book events with date/time selection, guest counts, room preferences, and budget."


class ProductReviewFormView(BaseSchemaFormView):
    """Product review form demonstration."""

    form_class = ProductReviewForm
    schema_class = ProductReview
    success_url = reverse_lazy("showcase:review-success")
    form_title = "Product Review"
    form_description = "Submit product reviews with 1-5 star rating, review text, and optional photo."


class JobApplicationFormView(BaseSchemaFormView):
    """Job application form demonstration."""

    form_class = JobApplicationForm
    schema_class = JobApplication
    success_url = reverse_lazy("showcase:application-success")
    form_title = "Job Application"
    form_description = "Apply for jobs with resume upload, portfolio/LinkedIn links, and salary expectations."


class MedicalAppointmentFormView(BaseSchemaFormView):
    """Medical appointment form demonstration."""

    form_class = MedicalAppointmentForm
    schema_class = MedicalAppointment
    success_url = reverse_lazy("showcase:medical-success")
    form_title = "Medical Appointment"
    form_description = "Schedule medical appointments with patient info, department, and preferred datetime."


class SuccessView(TemplateView):
    """Generic success page showing submitted form data."""

    template_name = "showcase/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_data"] = self.request.session.get("form_data", {})
        context["form_title"] = self.request.session.get("form_title", "Form")
        return context
