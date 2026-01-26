import os
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from core.helpers import handle_serializer_exception
from core.jwt_token import generate_jwt_payload
from .serializer import (
    UserLoginSerializer, 
    UserSignupSerializer
)

# Create your views here.
CLIENT_JWT_KEY = os.getenv('CLIENT_JWT_KEY')
"""JWT Token"""

class UserAuthViewSet(ModelViewSet):
    @action(detail= False,methods= ['POST']) 
    def register(self, request):
        try:
            user_seriralizer = UserSignupSerializer(data = request.data)
            if not user_seriralizer.is_valid():
                return Response ({
                    "status": False,
                    "message": handle_serializer_exception(user_seriralizer)
                },status= HTTP_400_BAD_REQUEST)
            user_instance = user_seriralizer.save()
            token_payload = generate_jwt_payload(
                entity_instance = user_instance,
                roles = user_instance.role,
                jwt_key = CLIENT_JWT_KEY
            )
            if not token_payload["status"]:
                user_instance.delete()
                return Response ({
                    "status": False,
                    "message": token_payload["message"],
                    "details": token_payload["details"]
                },status= HTTP_500_INTERNAL_SERVER_ERROR)
            return Response ({
                "status": True,
                "message": "User created successfully",
                "access_token": token_payload["access_token"],
                "refresh_token": token_payload["refresh_token"],
                "data": user_seriralizer.data
            },status= HTTP_200_OK)
        except Exception as swr:
            return Response({
                "status": False, 
                "message": str(swr)
            },status=HTTP_500_INTERNAL_SERVER_ERROR,)
            
   
    """User Login with model view set with token"""
    @action(detail= False,methods= ['POST'])
    def login(self, request):
        try:
            user_instance = UserLoginSerializer(data=request.data)
            print(user_instance)
            if not user_instance.is_valid():
                error = handle_serializer_exception(user_instance)
                return Response({"status":False,"message":error}, status=HTTP_400_BAD_REQUEST)
            user_data = user_instance.validated_data
            token_payload = generate_jwt_payload(
                entity_instance = user_data,
                roles = "Client",
                jwt_key = CLIENT_JWT_KEY
            )
            message = (
                "User login successfully" if user_data.role == 1 else
                "Merchant login successfully" if user_data.role == 2 else
                "Admin login successfully"
            )
            return Response({
                "status": True,
                "message": message,
                "access_token": token_payload["access_token"],
                "refresh_token": token_payload["refresh_token"],
                "data": {
                    "id":user_data.id,
                    "first_name":user_data.full_name,
                    "phone_number":user_data.phone_number,
                    "role":user_data.role,
                    "image": user_data.image.url if user_data.image else None,
                    "is_active":user_data.is_active}
                    },status= HTTP_200_OK)  
        except Exception as swr:
            return Response({
                "status": False, "message": str(swr)
                },status=HTTP_500_INTERNAL_SERVER_ERROR,)
