from django.contrib.auth.hashers import check_password
from passlib.hash import django_pbkdf2_sha256 as handler
from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    CharField,
    ValidationError
)
from authentication.utils import (
    validate_mtn_phone_format
)
from authentication.models import (
    UserModel,
    TransactionModel
)

class UserSignupSerializer(ModelSerializer):
    """Serializer for user signup with validations based on New Model"""
    password = CharField(write_only=True, min_length=8, required=True)
    confirm_password = CharField(write_only=True, required=True)
    
    class Meta:
        model = UserModel  
        fields = [
            "id", 
            "full_name",  
            "email",   
            "phone_number",  
            "password", 
            "confirm_password", 
            "role",          
            "merchant_code"
        ]
        extra_kwargs = {
            "email": {
                "required": True,
                "allow_null": False,
                "allow_blank": False,
                "error_messages": {
                    "required": "Email is required.",
                    "null": "Email cannot be null.",
                    "blank": "Email cannot be blank."
                }
            }
        }

    def validate_email(self, value):
        """
        Custom validation to ensure the email is unique,
        preventing duplicate accounts.
        """
        value = value.strip()
        if UserModel.objects.filter(email=value).exists():
            raise ValidationError("This email is already registered.")
        return value
    
    def validate_phone_number(self, value):
        """
        DRF automatically calls this method for the 'phone_number' field.
        """
        try:
            cleaned_phone = validate_mtn_phone_format(value)
            if UserModel.objects.filter(phone_number=cleaned_phone).exists():
                raise ValidationError("This phone number is already registered.")
            return cleaned_phone
        except ValidationError as e:
            raise ValidationError(e.detail)
        
    def validate(self, data): 
        """Custom validation for password matching"""
        if "phone_number" in data:
            data["phone_number"] = data["phone_number"].strip()
        
        if data["password"] != data["confirm_password"]:
            raise ValidationError({"confirm_password": "Passwords do not match."})
            
        return data

    def create(self, validated_data):
        """Create a new user"""
        validated_data.pop("confirm_password")  
        return UserModel.objects.create(**validated_data)


class UserLoginSerializer(Serializer):
    """User Login Serializer using Phone Number"""
    phone_number = CharField(required=True)
    password = CharField(write_only=True, required=True)

    def validate(self, data):
        """Validate phone_number and password"""
        phone_number = data["phone_number"].strip()
        password = data["password"]

        # Check if user exists with this phone number
        user = UserModel.objects.filter(phone_number=phone_number).first()
        
        if not user:
            raise ValidationError({"phone_number": "User with this phone number does not exist"})

        # Check Password
        if not check_password(password, user.password):
            raise ValidationError({"password": "Incorrect password"})
        
        if not user.is_active:
            raise ValidationError({"phone_number": "This account is disabled"})
        
        return user


class MerchantQRSerializer(serializers.ModelSerializer):
    """Serializer to show Merchant details in QR"""
    class Meta:
        model = UserModel
        fields = ['id', 'full_name', 'merchant_code', 'phone_number']

class InitiatePaymentSerializer(serializers.Serializer):
    """Input validation for paying"""
    # merchant_id = serializers.UUIDField(required=True)
    merchant_code = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

class TransactionSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TransactionModel
        fields = [
            'id',
            'sender_name',
            'receiver_name',
            'amount',
            'currency',
            'transaction_ref_id',
            'status',
            'mtn_response_data',
            # 'created_at', 
        ]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        return data


class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = UserModel
        fields = ['full_name', 'phone_number', 'image'] 
        
    def validate_phone_number(self, value):
        user_instance = self.context['request'].user_instance
        cleaned_phone = value.strip()
        if UserModel.objects.filter(phone_number=cleaned_phone).exclude(id=user_instance.id).exists():
            raise ValidationError("This phone number is already registered to another account.")
        
        return cleaned_phone
    