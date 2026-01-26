from django.contrib.auth.hashers import check_password
from passlib.hash import django_pbkdf2_sha256 as handler
from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    CharField,
    ValidationError
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
            "phone_number",  
            "password", 
            "confirm_password", 
            "role",          
            "merchant_code"
        ]
        
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
    """Response serializer"""
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)

    class Meta:
        model = TransactionModel
        fields = '__all__'
    