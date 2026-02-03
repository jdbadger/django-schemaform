"""URL configuration for showcase app."""

from django.urls import path

from . import views

app_name = "showcase"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    # Contact form
    path("contact/", views.ContactFormView.as_view(), name="contact"),
    path("contact/success/", views.SuccessView.as_view(), name="contact-success"),
    # User registration form
    path(
        "registration/", views.UserRegistrationFormView.as_view(), name="registration"
    ),
    path(
        "registration/success/",
        views.SuccessView.as_view(),
        name="registration-success",
    ),
    # Event booking form
    path("booking/", views.EventBookingFormView.as_view(), name="booking"),
    path("booking/success/", views.SuccessView.as_view(), name="booking-success"),
    # Product review form
    path("review/", views.ProductReviewFormView.as_view(), name="review"),
    path("review/success/", views.SuccessView.as_view(), name="review-success"),
    # Job application form
    path("application/", views.JobApplicationFormView.as_view(), name="application"),
    path(
        "application/success/", views.SuccessView.as_view(), name="application-success"
    ),
    # Medical appointment form
    path("medical/", views.MedicalAppointmentFormView.as_view(), name="medical"),
    path("medical/success/", views.SuccessView.as_view(), name="medical-success"),
]
