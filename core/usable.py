import re
import random
import string


def check_email_foramt(email):
    emailregix = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    if re.match(emailregix, email):

        return True

    else:
        return False


def password_length_validator(password):
    if not (
        re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
        and re.search(r"[A-Z]", password)
        and 8 <= len(password) <= 20
    ):
        return False
    return True


def execption_handler(val):
    if "error" in val.errors:
        error = val.errors["error"][0]
    else:
        key = next(iter(val.errors))
        custom_key = key
        if key == "non_field_errors":
            custom_key = "error"
        error = custom_key + ", " + val.errors[key][0]

    return error


def require_keys(require_fields, request_data):
    try:
        for j in require_fields:
            if not j in request_data:
                return False
        return True
    except:
        return False


def all_fields_required(require_fields, request_data):
    try:
        for j in require_fields:
            if len(request_data[j]) == 0:
                return False
        return True
    except:
        return False


def key_validation(key_status, req_status, request_data, require_fields):
    ##keys validation
    if key_status:
        keys_status = require_keys(require_fields, request_data)
        if not keys_status:
            return {
                "status": False,
                "message": f"{require_fields} all keys are required",
            }

    ##Required field validation
    if req_status:
        required_status = all_fields_required(require_fields, request_data)
        if not required_status:
            return {"status": False, "message": "All Fields are Required"}


def generate_random_password(length=18):
    if length <= 14:
        raise ValueError("Password length must be greater than 13 characters.")

    # Define character sets
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = string.punctuation

    # Ensure at least one of each required character type
    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special),
    ]

    # Fill the rest of the password length with a mix of characters
    all_characters = lower + upper + digits
    remaining_length = length - len(password)
    password += random.choices(all_characters, k=remaining_length)

    # Shuffle to ensure the special character is not always at a fixed position
    random.shuffle(password)

    return "".join(password)

def execptionhandler(val,custom_message="-"):
    if "error" in val.errors:
        error = val.errors["error"][0]
    else:
        key = next(iter(val.errors))
        error = key + ", " + val.errors[key][0]
        error = error.replace("non_field_errors, ", "")

    if custom_message != "-":
        if "unique" in str(error).lower():
            error = custom_message
    return error
