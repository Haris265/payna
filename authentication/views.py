import base64
import random
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
import os
import uuid
import logging
from random import randint
import requests
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from django.db.models import Q  
from rest_framework.response import Response
from rest_framework import status
from core.permission.user_permission import UserGeneralAuthorization
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_403_FORBIDDEN,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_202_ACCEPTED
)
from core.mtn_service import (
    MTNService
)
from core.orange_service import (
    OrangePaymentService
)
from core.choices import (
    TransactionStatusChoices
)
from core.helpers import handle_serializer_exception
from core.jwt_token import generate_jwt_payload
from authentication.serializer import (
    UserLoginSerializer,
    UserProfileSerializer, 
    UserSignupSerializer,
    TransactionSerializer,
    MerchantQRSerializer,
    InitiatePaymentSerializer,
    ChangePasswordSerializer
)
from authentication.models import (
    UserModel,
    TransactionModel
)
from dotenv import load_dotenv

from core.utils import send_otp_email
load_dotenv()

# Create your views here.
CLIENT_JWT_KEY = os.getenv('CLIENT_JWT_KEY')
"""JWT Token"""



class UserAuthViewSet(ModelViewSet):
    @action(detail=False, methods=['POST']) 
    def register(self, request):
        try:
            user_seriralizer = UserSignupSerializer(data=request.data)
            if not user_seriralizer.is_valid():
                return Response({
                    "status": False,
                    "message": handle_serializer_exception(user_seriralizer)
                }, status=HTTP_400_BAD_REQUEST)
                
            user_instance = user_seriralizer.save()
            
            # OTP Generation & Caching
            otp_code = str(randint(100000, 999999))            
            cache.set(f"otp_{user_instance.email}", otp_code, timeout=300) # 5 minutes expiry
            
            # Inline Email Dispatch
            subject = 'Welcome to LibLink - Verify Your Account'
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
                    .container {{ background-color: #ffffff; padding: 30px; border-radius: 8px; max-width: 500px; margin: auto; }}
                    .otp-box {{ background-color: #eef2f5; padding: 15px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 5px; margin: 25px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>LibLink Verification</h2>
                    <p>Thank you for registering. Please use the following One-Time Password (OTP) to verify your account:</p>
                    <div class="otp-box">{otp_code}</div>
                    <p>This code is valid for 5 minutes.</p>
                </div>
            </body>
            </html>
            """
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_instance.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # Response Formatting
            response_data = user_seriralizer.data
            response_data['created_at'] = user_instance.date_joined if user_instance.date_joined else None
            
            return Response({
                "status": True,
                "message": "User created successfully. OTP has been sent to the registered email.",                
                "data": response_data
            }, status=HTTP_200_OK)
            
        except Exception as swr:
            return Response({
                "status": False, 
                "message": str(swr)
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def verify_otp(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')

            if not email or not otp:
                return Response({
                    "status": False,
                    "message": "Email and OTP are required."
                }, status=HTTP_400_BAD_REQUEST)

            cached_otp = cache.get(f"otp_{email}")

            if not cached_otp:
                return Response({
                    "status": False,
                    "message": "OTP has expired or is invalid. Please request a new one."
                }, status=HTTP_400_BAD_REQUEST)

            if str(cached_otp) != str(otp):
                return Response({
                    "status": False,
                    "message": "Invalid OTP. Please try again."
                }, status=HTTP_400_BAD_REQUEST)

            try:
                # User ko find karein (UserModel ki jagah apna model name use karein agar zaroorat ho)
                user_instance = UserModel.objects.get(email=email)
                
                # Zaroori Step: User ko active/verified mark kar dein taake wo login kar sake
                user_instance.is_active = True 
                user_instance.save()

                # Cache se OTP hata dein
                cache.delete(f"otp_{email}")

                return Response({
                    "status": True,
                    "message": "Account verified successfully. You can now proceed to login."
                }, status=HTTP_200_OK)

            except UserModel.DoesNotExist:
                return Response({
                    "status": False,
                    "message": "User not found."
                }, status=HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)
            
   
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
            # image_url = None
            # if user_data.image:
            #     image_url = request.build_absolute_uri(user_data.image.url)
            base_url = "https://jj2lk5nn-8000.asse.devtunnels.ms"
            image_url = None
            if user_data.image:
                image_url = f"{base_url}{user_data.image.url}"
            return Response({
                "status": True,
                "message": message,
                "access_token": token_payload["access_token"],
                "refresh_token": token_payload["refresh_token"],
                "data": {
                    "id":user_data.id,
                    "first_name":user_data.full_name,
                    "phone_number":user_data.phone_number,
                    "email":user_data.email,
                    "role":user_data.role,
                    # "image": user_data.image.url if user_data.image else None,
                    "image": image_url,
                    "created_at": user_data.date_joined,                    
                    "is_active":user_data.is_active}
                    },status= HTTP_200_OK)  
        except Exception as swr:
            return Response({
                "status": False, "message": str(swr)
                },status=HTTP_500_INTERNAL_SERVER_ERROR,)

    @action(detail=False, methods=['POST'], permission_classes=[UserGeneralAuthorization])
    def change_password(self, request):
        try:
            user = request.user_instance
            serializer = ChangePasswordSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    "status": False,
                    "message": handle_serializer_exception(serializer) 
                }, status=HTTP_400_BAD_REQUEST)
                
            old_password = serializer.validated_data.get("old_password")
            new_password = serializer.validated_data.get("new_password")
            
            if not user.check_password(old_password):
                return Response({
                    "status": False,
                    "message": "Old password is incorrect."
                }, status=HTTP_400_BAD_REQUEST)
                
            user.set_password(new_password)
            user.save()
            
            return Response({
                "status": True,
                "message": "Password changed successfully."
            }, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def forgot_password(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response({"status": False, "message": "Email is required."}, status=HTTP_400_BAD_REQUEST)

            try:
                user_instance = UserModel.objects.get(email=email)
            except UserModel.DoesNotExist:
                return Response({"status": False, "message": "No account found with this email."}, status=HTTP_404_NOT_FOUND)

            otp_code = str(randint(100000, 999999))            
            cache.set(f"reset_otp_{email}", otp_code, timeout=300) # 5 minutes expiry
            
            subject = 'LibLink - Password Reset Request'
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body>
                <h2>Password Reset</h2>
                <p>Hello {user_instance.full_name},</p>
                <p>Your password reset OTP is: <strong>{otp_code}</strong></p>
                <p>This code is valid for 5 minutes.</p>
            </body>
            </html>
            """
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            return Response({
                "status": True,
                "message": "Password reset OTP has been sent to your email."
            }, status=HTTP_200_OK)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def verify_reset_otp(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')

            if not email or not otp:
                return Response({"status": False, "message": "Email and OTP are required."}, status=HTTP_400_BAD_REQUEST)

            cached_otp = cache.get(f"reset_otp_{email}")

            if not cached_otp:
                return Response({
                    "status": False,
                    "message": "OTP has expired or is invalid. Please request a new one."
                }, status=HTTP_400_BAD_REQUEST)

            if str(cached_otp) != str(otp):
                return Response({"status": False, "message": "Invalid OTP. Please try again."}, status=HTTP_400_BAD_REQUEST)

            cache.delete(f"reset_otp_{email}")
            
            cache.set(f"allow_reset_{email}", True, timeout=600)

            return Response({
                "status": True,
                "message": "OTP verified successfully. You can now set a new password."
            }, status=HTTP_200_OK)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def set_new_password(self, request):
        try:
            email = request.data.get('email')
            new_password = request.data.get('new_password')
            confirm_password = request.data.get('confirm_password')

            if not all([email, new_password, confirm_password]):
                return Response({
                    "status": False, 
                    "message": "Email, new_password, and confirm_password are required."
                }, status=HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({"status": False, "message": "Passwords do not match."}, status=HTTP_400_BAD_REQUEST)

            if len(new_password) < 8:
                return Response({"status": False, "message": "Password must be at least 8 characters long."}, status=HTTP_400_BAD_REQUEST)

            is_reset_allowed = cache.get(f"allow_reset_{email}")

            if not is_reset_allowed:
                return Response({
                    "status": False,
                    "message": "Session expired or OTP not verified. Please restart the password reset process."
                }, status=HTTP_400_BAD_REQUEST)

            # User ka password update karein
            try:
                user_instance = UserModel.objects.get(email=email)
                user_instance.set_password(new_password)
                user_instance.save()

                cache.delete(f"allow_reset_{email}")

                return Response({
                    "status": True,
                    "message": "Your password has been reset successfully. You can now login."
                }, status=HTTP_200_OK)

            except UserModel.DoesNotExist:
                return Response({"status": False, "message": "User not found."}, status=HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], permission_classes=[UserGeneralAuthorization])
    def get_profile(self, request):
        try:
            user_instance = request.user_instance
            base_url = "https://payna.hnhsofttechsolutions.com"
            image_url = None
            if user_instance.image:
                image_url = f"{base_url}{user_instance.image.url}"
                
            return Response({
                "status": True,
                "message": "Profile retrieve successfully",
                "data": {
                    "id": user_instance.id,
                    "first_name": user_instance.full_name,
                    "phone_number": user_instance.phone_number,
                    "email": user_instance.email,
                    "role": user_instance.role,
                    "image": image_url,
                    "created_at": user_instance.date_joined,                    
                    "is_active": user_instance.is_active
                }
            }, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": False, 
                "message": str(e)
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['PUT', 'PATCH'], permission_classes=[UserGeneralAuthorization])
    def update_profile(self, request):
        try:
            user_instance = request.user_instance
            
            serializer = UserProfileSerializer(
                user_instance, 
                data=request.data, 
                partial=True, 
                context={'request': request} 
            )
            
            if not serializer.is_valid():
                return Response({
                    "status": False,
                    "message": handle_serializer_exception(serializer)
                }, status=HTTP_400_BAD_REQUEST)
                
            updated_user = serializer.save()
            
            base_url = "https://payna.hnhsofttechsolutions.com"
            image_url = None
            if updated_user.image:
                image_url = f"{base_url}{updated_user.image.url}"
                
            return Response({
                "status": True,
                "message": "Profile updated successfully",
                "data": {
                    "id": updated_user.id,
                    "first_name": updated_user.full_name,
                    "phone_number": updated_user.phone_number,
                    "email": updated_user.email,
                    "role": updated_user.role,
                    "image": image_url,
                    "created_at": updated_user.date_joined,                    
                    "is_active": updated_user.is_active
                }
            }, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": False, 
                "message": str(e)
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserPaymentWithMTN(ModelViewSet):
    COLLECT_KEY = os.getenv('MTN_COLLECTION_SUB_KEY')
    DISBURSE_KEY = os.getenv('MTN_DISBURSEMENT_SUB_KEY')
    API_USER = os.getenv('MTN_API_USER_ID')
    API_KEY = os.getenv('MTN_API_KEY')
    BASE_URL = os.getenv('MTN_BASE_URL')
    ENV = os.getenv('MTN_ENVIRONMENT')
    NGROK = os.getenv('MTN_NGROK_URL')

    def _get_token(self, product):
        """Helper to get Access Token based on product type"""
        sub_key = self.COLLECT_KEY if product == 'collection' else self.DISBURSE_KEY
        auth_str = f"{self.API_USER}:{self.API_KEY}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        
        url = f"{self.BASE_URL}/{product}/token/"
        headers = {
            "Ocp-Apim-Subscription-Key": sub_key,
            "Authorization": f"Basic {encoded_auth}"
        }
        
        try:
            res = requests.post(url, headers=headers)
            if res.status_code == 200:
                return res.json().get('access_token'), sub_key
        except Exception as e:
            print(f"Token Error: {str(e)}")
        return None, None

    # 1. COLLECT: User ke mobile par offline PIN prompt bhejega
    @action(detail=False, methods=['post'])
    def collect(self, request):
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        
        token, sub_key = self._get_token('collection')
        if not token:
            return Response({"error": "Auth Failed"}, status=401)
            
        ref_id = str(uuid.uuid4())
        url = f"{self.BASE_URL}/collection/v1_0/requesttopay"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": ref_id,
            "X-Target-Environment": self.ENV, # Sandbox mein 'sandbox' hona chahiye
            "Ocp-Apim-Subscription-Key": sub_key,
            # IMPORTANT: Sandbox mein ye URL aksar ignored hota hai agar Host match na kare
            "X-Callback-Url": f"{self.NGROK}/authentication/v1/initiate/mtn/callback/",            
            "Content-Type": "application/json"
        }
        
        payload = {
            "amount": amount, 
            "currency": "EUR", # Sandbox sirf EUR accept karta hai
            "externalId": str(uuid.uuid4().hex[:10]),
            "payer": {"partyIdType": "MSISDN", "partyId": phone},
            "payerMessage": "Testing MTN Payment", 
            "payeeNote": "Django Sandbox Test"
        }
        
        res = requests.post(url, json=payload, headers=headers)

        if res.status_code == 202:
            # Pakistan mein baith kar test karne ke liye ye Ref ID bohot zaroori hai
            return Response({
                "reference_id": ref_id, 
                "status": "Initiated",
                "instruction": "Ab is reference_id ko MTN Sandbox tool mein approve karein"
            }, status=202)
        return Response({"error": "Failed", "raw": res.text}, status=res.status_code)

    # 2. CALLBACK: MTN khud is URL ko hit karega jab payment ho jayegi
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def callback(self, request):
        # Yeh terminal mein print hoga jab payment confirm hogi
        print("!!! MTN NOTIFICATION RECEIVED !!!")
        print("Transaction Data:", request.data)
        
        status_received = request.data.get('status')
        if status_received == 'SUCCESSFUL':
            # Yahan aap Database update kar sakte hain
            print("Payment Successful in DB!")
            
        return Response({"status": "Accepted"}, status=200)

    # 3. CHECK STATUS: Manual check karne ke liye
    @action(detail=False, methods=['get'])
    def check_status(self, request):
        ref_id = request.query_params.get('ref_id')
        token, sub_key = self._get_token('collection')
        
        url = f"{self.BASE_URL}/collection/v1_0/requesttopay/{ref_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.ENV,
            "Ocp-Apim-Subscription-Key": sub_key,
        }
        
        res = requests.get(url, headers=headers)
        return Response(res.json() if res.status_code == 200 else {"error": res.text})

    # 4. DISBURSE: Kisi user ko paise bhejna
    @action(detail=False, methods=['post'])
    def disburse(self, request):
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        
        token, sub_key = self._get_token('disbursement')
        if not token:
            return Response({"error": "Auth Failed"}, status=401)

        ref_id = str(uuid.uuid4())
        url = f"{self.BASE_URL}/disbursement/v1_0/transfer"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": ref_id,
            "X-Target-Environment": self.ENV,
            "Ocp-Apim-Subscription-Key": sub_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "amount": amount, "currency": "EUR",
            "externalId": str(uuid.uuid4().hex[:10]),
            "payee": {"partyIdType": "MSISDN", "partyId": phone},
            "payerMessage": "Payout sent", "payeeNote": "Transfer"
        }
        
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 202:
            return Response({"status": "Sent", "reference_id": ref_id}, status=202)
        return Response(res.json(), status=res.status_code)
    
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
    
    # @action(detail=False, methods=["POST"], permission_classes=[UserGeneralAuthorization])
    # def payment(self, request):
    #     # 1. Validate Input
    #     serializer = InitiatePaymentSerializer(data=request.data)
    #     if not serializer.is_valid():
    #         return Response ({
    #             "status": False,
    #             "message": serializer.errors 
    #         }, status=HTTP_400_BAD_REQUEST)

    #     req_merchant_code = serializer.validated_data['merchant_code']
    #     amount = serializer.validated_data['amount']
    #     user = request.user_instance
    #     try:
    #         merchant = UserModel.objects.get(merchant_code=req_merchant_code, role=UserModel.Role.MERCHANT)
    #     except UserModel.DoesNotExist:
    #         return Response({"error": "Invalid Merchant Code."}, status=HTTP_400_BAD_REQUEST)
    #     transaction_ref_id = str(uuid.uuid4())
    #     transaction = TransactionModel.objects.create(
    #         sender=user,
    #         receiver=merchant,
    #         amount=amount,
    #         transaction_ref_id=transaction_ref_id,
    #         status=TransactionStatusChoices.PENDING
    #     )
    #     # payer_phone = "56733123453" 
    #     payer_phone = user.phone_number 
    #     if not payer_phone:
    #         return Response({"error": "User phone number not found."}, status=HTTP_400_BAD_REQUEST)
    #     token = MTNService.generate_access_token()
    #     if not token:
    #         return Response({"error": "MTN System error (Token Generation Failed)"}, status=HTTP_503_SERVICE_UNAVAILABLE)

    #     is_success, api_message = MTNService.request_to_pay(
    #         token=token,
    #         amount=amount,
    #         phone_number=payer_phone, 
    #         transaction_ref_id=transaction_ref_id
    #     )

    #     if is_success:
    #         return Response({
    #             "message": "Payment request sent. Waiting for approval.",
    #             "transaction_ref_id": transaction_ref_id,
    #             "status": "PENDING"
    #         }, status=HTTP_202_ACCEPTED)
    #     else:
    #         # Failed Case
    #         transaction.status = TransactionStatusChoices.FAILED
    #         transaction.mtn_response_data = {"error_detail": api_message}
    #         transaction.save()
            
    #         return Response({
    #             "status": False,
    #             "error": "Failed to initiate payment",
    #             "detail": api_message 
    #         }, status=HTTP_400_BAD_REQUEST)

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

        payer_phone = user.phone_number 
        if not payer_phone:
            return Response({"error": "User phone number not found."}, status=HTTP_400_BAD_REQUEST)
        
        mock_mtn_response = {
            "financialTransactionId": "1458036634",
            "externalId": transaction_ref_id,
            "amount": str(amount),
            "currency": "USD",
            "payer": {
                "partyIdType": "MSISDN", 
                "partyId": payer_phone or "56733123453"
            },
            "payerMessage": "Payment via App",
            "payeeNote": "Merchant Payment",
            "status": "SUCCESSFUL"
        }

        transaction.status = TransactionStatusChoices.SUCCESS 
        transaction.mtn_response_data = mock_mtn_response
        transaction.save()

        return Response({
            "status": True,
            "message": "Payment Successful",
            "transaction_ref_id": transaction_ref_id,
            "mtn_data": mock_mtn_response
        }, status=HTTP_200_OK)
        
    @action(detail=False, methods=['GET'], permission_classes=[UserGeneralAuthorization])
    def transactions(self, request):
        transaction_ref_id = request.query_params.get('transaction_ref_id')
        user = request.user_instance

        if not transaction_ref_id:
            transactions = TransactionModel.objects.filter(
                Q(sender=user) | Q(receiver=user)
            ).order_by('-created_at')  
            
            serializer = TransactionSerializer(transactions, many=True)
            return Response({
                "status": True,
                "message": "All transactions retrieve successfully",
                "count": transactions.count(),
                "data": serializer.data
            })

        transaction = get_object_or_404(TransactionModel, transaction_ref_id=transaction_ref_id)
        if user != transaction.sender and user != transaction.receiver:
            return Response({"error": "Unauthorized"}, status=403)
        if transaction.status == TransactionStatusChoices.SUCCESS:
            return Response({"status": "SUCCESS", "data": TransactionSerializer(transaction).data})
        if transaction.status == TransactionStatusChoices.FAILED:
            return Response({"status": "FAILED", "data": TransactionSerializer(transaction).data})
        try:
            token = MTNService.generate_access_token()
            if not token:
                return Response({"error": "MTN Token Error"}, status=503)

            mtn_data = MTNService.check_status(token, transaction_ref_id)
            print("MTN RESPONSE:", mtn_data)  # Debugging

            if mtn_data:
                mtn_status = mtn_data.get("status")
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

        except Exception as e:
            print(f"Error checking MTN status: {e}")
            pass

        return Response({"status": "PENDING", "message": "Waiting for user approval...", "data": TransactionSerializer(transaction).data})

class UserPaymentWithOrange(ModelViewSet):
    @action(detail=False, methods=['POST'], permission_classes=[UserGeneralAuthorization])
    def initiate_orange_payment(self, request):
        amount = request.data.get('amount')
        
        if not amount:
            return Response({"error": "Payment amount is required."}, status=HTTP_400_BAD_REQUEST)

        import uuid
        order_id = str(uuid.uuid4()) 
        
        ngrok_base_url = "https://d766-103-121-41-213.ngrok-free.app" 
        
        return_url = f"{ngrok_base_url}/payment/success/"
        cancel_url = f"{ngrok_base_url}/payment/cancel/"
        notif_url = f"{ngrok_base_url}/api/webhook/" 
        
        try:
            result = OrangePaymentService.create_payment_url(
                order_id, amount, return_url, cancel_url, notif_url
            )
            
            if "error" in result:
                return Response(result, status=HTTP_400_BAD_REQUEST)
                
            return Response(result, status=HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
   


class OrangeWebhookView(APIView):
    # Orange server se request aayegi isliye auth band karna zaroori hai
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Orange jo data bhejay ga woh request.data mein hoga
        orange_data = request.data
        
        # Terminal mein print kar ke dekhein ke Orange ne kya bheja hai
        print("====== ORANGE WEBHOOK RECEIVED ======")
        print(orange_data)
        print("=====================================")

        # Yahan aap check kar sakte hain:
        payment_status = orange_data.get("status") # e.g., 'SUCCESS' or 'FAILED'
        order_id = orange_data.get("order_id") # Jo UUID humne bheja tha
        txnid = orange_data.get("txnid") # Orange ka transaction ID

        if payment_status == "SUCCESS":
            # TODO: Apne database mein payment ko 'Paid' mark karein
            # Order.objects.filter(id=order_id).update(status='Paid', transaction_id=txnid)
            pass
        
        # Orange ko humesha 200 OK return karna lazmi hai, warna wo retry karta rahega
        return Response({"message": "Webhook received successfully"}, status=status.HTTP_200_OK)
    
    
