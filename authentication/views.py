import os
import uuid
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permission.user_permission import UserGeneralAuthorization
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_403_FORBIDDEN,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_202_ACCEPTED
)
from core.mtn_service import (
    MTNService
)
from core.choices import (
    TransactionStatusChoices
)
from core.helpers import handle_serializer_exception
from core.jwt_token import generate_jwt_payload
from authentication.serializer import (
    UserLoginSerializer, 
    UserSignupSerializer,
    TransactionSerializer,
    MerchantQRSerializer,
    InitiatePaymentSerializer
)
from authentication.models import (
    UserModel,
    TransactionModel
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
        
class UserPaymentWithMTN(ModelViewSet):
    @action(detail=False, methods=["GET"], permission_classes=[UserGeneralAuthorization])
    def my_qr(self, request):
        if request.user_instance.role != UserModel.Role.MERCHANT:
            return Response({"error": "Only merchants can generate QR codes"}, status=HTTP_403_FORBIDDEN)
        serializer = MerchantQRSerializer(request.user_instance)
        return Response({
            "status": True,
            "message": "Qr code retrieve successfully",
            "data": serializer.data,
        }, status=HTTP_200_OK)
    
    @action(detail=False, methods=["POST"], permission_classes=[UserGeneralAuthorization])
    def payment(self, request):
        # 1. Validate Input
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response ({
                "status": False,
                "message": serializer.errors 
            }, status=HTTP_400_BAD_REQUEST)

        req_merchant_code = serializer.validated_data['merchant_code']
        amount = serializer.validated_data['amount']
        user = request.user_instance
        try:
            merchant = UserModel.objects.get(merchant_code=req_merchant_code, role=UserModel.Role.MERCHANT)
        except UserModel.DoesNotExist:
            return Response({"error": "Invalid Merchant Code."}, status=HTTP_400_BAD_REQUEST)
        transaction_ref_id = str(uuid.uuid4())
        transaction = TransactionModel.objects.create(
            sender=user,
            receiver=merchant,
            amount=amount,
            transaction_ref_id=transaction_ref_id,
            status=TransactionStatusChoices.PENDING
        )
        payer_phone = "56733123453" 
        token = MTNService.generate_access_token()
        if not token:
            return Response({"error": "MTN System error (Token Generation Failed)"}, status=HTTP_503_SERVICE_UNAVAILABLE)

        is_success, api_message = MTNService.request_to_pay(
            token=token,
            amount=amount,
            phone_number=payer_phone, 
            transaction_ref_id=transaction_ref_id
        )

        if is_success:
            return Response({
                "message": "Payment request sent. Waiting for approval.",
                "transaction_ref_id": transaction_ref_id,
                "status": "PENDING"
            }, status=HTTP_202_ACCEPTED)
        else:
            # Failed Case
            transaction.status = TransactionStatusChoices.FAILED
            transaction.mtn_response_data = {"error_detail": api_message}
            transaction.save()
            
            return Response({
                "status": False,
                "error": "Failed to initiate payment",
                "detail": api_message 
            }, status=HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['GET'], permission_classes=[UserGeneralAuthorization])
    def check_status(self, request):
        transaction_ref_id = request.query_params.get('transaction_ref_id')
        
        if not transaction_ref_id:
            return Response({"error": "ref_id is required"}, status=400)

        transaction = get_object_or_404(TransactionModel, transaction_ref_id=transaction_ref_id)

        if request.user_instance != transaction.sender and request.user_instance != transaction.receiver:
            return Response({"error": "Unauthorized"}, status=403)

        if transaction.status == TransactionStatusChoices.SUCCESS:
            return Response({"status": "SUCCESS", "data": TransactionSerializer(transaction).data})

        token = MTNService.generate_access_token()
        mtn_data = MTNService.check_status(token, transaction_ref_id)
        
        # --- DEBUGGING LINE (Terminal me check karein kya aa raha hai) ---
        print("MTN RESPONSE:", mtn_data) 

        if mtn_data:
            mtn_status = mtn_data.get("status")
            
            # === CHANGE IS HERE ===
            # MTN "SUCCESSFUL" bhejta hai, "SUCCESS" nahi.
            # Hum safety ke liye dono check kar lete hain.
            if mtn_status in ["SUCCESS", "SUCCESSFUL"]: 
                transaction.status = TransactionStatusChoices.SUCCESS
                transaction.mtn_response_data = mtn_data
                transaction.save()
                return Response({"status": "SUCCESS", "data": TransactionSerializer(transaction).data})
            
            elif mtn_status == "FAILED":
                transaction.status = TransactionStatusChoices.FAILED
                transaction.mtn_response_data = mtn_data
                transaction.save()
                return Response({"status": "FAILED", "reason": mtn_data.get("reason")})

        return Response({"status": "PENDING", "message": "Waiting for user approval..."})
