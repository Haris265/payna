import hashlib
from datetime import datetime, timedelta
import jwt
from authentication.models import UserWhitelistTokenModel

def save_jwt_token(entity_instance,access_token,refresh_token):
    """Saves the access and refresh tokens to the database"""
    try:
        access_token_fingerprint = hashlib.sha256(access_token.encode()).hexdigest()
        refresh_token_fingerprint = hashlib.sha256(refresh_token.encode()).hexdigest()
        UserWhitelistTokenModel.objects.create(user=entity_instance,token_fingerprint=access_token_fingerprint,refresh_token_fingerprint=refresh_token_fingerprint)
        return {
            "status": True,
            "message": "Tokens saved successfully.",
        }
    except Exception as error:
        return {
            "status": False,
            "message": "An error occurred while saving tokens.",
            "details": str(error),
        }


def generate_jwt_token(jwt_key, entity_id, entity_email, role, expiry_duration) -> str:
    """Generates a JWT token with the specified payload and expiry duration """
    access_token_payload = {
        "id": entity_id,
        "email": entity_email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(**expiry_duration),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(access_token_payload, jwt_key, algorithm="HS256")



def generate_jwt_payload(
        entity_instance, 
        roles, 
        jwt_key, 
        access_token_duration = {"days": 30},
        refresh_token_duration = {"days": 90}
):
    # """Generates the JWT payload including access and refresh tokens, and user agent info"""
    try:
        entity_id = str(entity_instance.id)
        entity_email = entity_instance.email
        access_token = generate_jwt_token(
            jwt_key, entity_id, entity_email, roles, access_token_duration
        )
        refresh_token = generate_jwt_token(
            jwt_key, entity_id, entity_email, roles, refresh_token_duration
        )
        token_saving_response = save_jwt_token(entity_instance = entity_instance,access_token=access_token,refresh_token=refresh_token)
        if not token_saving_response["status"]:
            return token_saving_response

        return {
            "status": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    except Exception as error:
        return {
            "status": False,
            "message": "An error occurred during token creation.",
            "details": str(error),
        }
