import re
from rest_framework.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_otp_email(email, name, otp):
    subject = 'Welcome to LibLink - Verify Your Account'
    context = {'name': name, 'otp': otp}
    
    html_content = render_to_string('emails/otp_email.html', context)
    text_content = strip_tags(html_content) 

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def validate_mtn_phone_format(phone):
    """
    Validates that the phone number is numeric and has correct length.
    Returns the cleaned phone number or raises ValidationError.
    """
    if not phone:
        raise ValidationError("Phone number is required.")
    
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    # if not phone.isdigit():
    #     raise ValidationError("Phone number must contain only digits.")

    if len(phone) < 10 or len(phone) > 15:
        raise ValidationError("Invalid phone number length. It must be between 10-15 digits.")
    
    return phone