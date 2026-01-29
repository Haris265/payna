import re
from rest_framework.exceptions import ValidationError

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