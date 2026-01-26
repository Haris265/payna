from .base_permissions import BaseUserAuthorization


class UserGeneralAuthorization(BaseUserAuthorization):
    def has_permission(self, request, view):
        bearer_token = self.extract_bearer_token(request)
        decoded_token, token_instance = self.get_token_instance(bearer_token, "token")
        request.auth_token = decoded_token
        request.user_instance = token_instance.user
        return True