import os
import hashlib
import jwt
from django.contrib.auth.hashers import check_password
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_401_UNAUTHORIZED
from authentication.models import UserWhitelistTokenModel

CLIENT_JWT_KEY = os.getenv('CLIENT_JWT_KEY')

class BaseUserAuthorization(BasePermission):
    def extract_bearer_token(self, request):
        authorization_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not authorization_header.startswith("Bearer "):
            raise NeedLogin()
        return authorization_header[7:]

    def get_token_instance(self, bearer_token, token_field):
        try:
            decoded_token = jwt.decode(bearer_token, CLIENT_JWT_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise NeedLogin({"status": False, "message": "Session Expired !!"})
        except jwt.DecodeError:
            raise NeedLogin({"status": False, "message": "Invalid token decoded !!!"})
        except Exception as error:
            raise NeedLogin({"status": False, "message": str(error)})

        # Generate fingerprint for lookup
        token_fingerprint = hashlib.sha256(bearer_token.encode()).hexdigest()
        
        # Fetch only the matching fingerprint
        token_instance = UserWhitelistTokenModel.objects.filter(
            user=decoded_token["id"], 
            **{f"{token_field}_fingerprint": token_fingerprint}
        ).first()
        
        # If no matching fingerprint found, reject
        if not token_instance:
            raise NeedLogin({"status": False, "message": "Invalid authentication token"})

        return decoded_token, token_instance


class NeedLogin(APIException):
    status_code =  HTTP_401_UNAUTHORIZED
    default_detail = {"status": False, "message": "Unauthorized"}
    default_code = "not_authenticated"
