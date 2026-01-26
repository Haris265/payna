import random
from django.core.mail import send_mail

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(user_email, otp):
    subject = "Your OTP for Viewing Card Details"
    message = f"Your OTP is: {otp}"
    send_mail(subject, message, "no-reply@example.com", [user_email])
