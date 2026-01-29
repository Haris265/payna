import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.core.validators import FileExtensionValidator
from core.choices import (
    TransactionStatusChoices
)


# Create your models here.

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class CustomUserManager(BaseUserManager):
    # def create_user(self, email, password=None, **extra_fields):
    #     if not email:
    #         raise ValueError("The Email field must be set")
    #     email = self.normalize_email(email)
    #     user = self.model(email=email, **extra_fields)
    #     user.set_password(password)
    #     user.save()
    #     return user

    # def create_superuser(self, email, password=None, **extra_fields):
    #     extra_fields.setdefault("is_staff", True)
    #     extra_fields.setdefault("is_superuser", True)
    #     extra_fields.setdefault("role", UserModel.Role.SUPER_ADMIN)
    #     return self.create_user(email, password, **extra_fields)
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserModel.Role.ADMIN)  # Superuser is Admin
        return self.create_user(phone_number, password, **extra_fields)
        
        
class UserModel(AbstractUser):
    
    class Role(models.IntegerChoices):
        ADMIN = 0, 'Admin'         
        NORMAL_USER = 1, 'Normal User' 
        MERCHANT = 2, 'Merchant'                
                        
    username = None  # Remove username
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="Phone Number")
    full_name = models.CharField(max_length=100, verbose_name="Full Name")
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True, verbose_name="Email Address")
    role = models.IntegerField(choices=Role.choices, default=Role.NORMAL_USER, verbose_name="Role Name")
    password = models.CharField(max_length=255, verbose_name="Password")
    is_active = models.BooleanField(default=True)
    otp = models.IntegerField(blank=True, null=True)
    otp_status = models.BooleanField(default=False)
    otp_count = models.IntegerField(default=0)   
    merchant_code = models.CharField(max_length=50, blank=True, null=True, help_text="MTN Merchant ID for QR Code") 
    image = models.ImageField(
        upload_to='profile/image/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name="Profile Image", default="/profile/image/1.jpg"
    )
    def save(self, *args, **kwargs):
        """Password is hashed before saving"""
        if self.password and not self.password.startswith("pbkdf2_sha256$"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()
        
    
    def __str__(self):
            return self.full_name
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        
        
        
class UserWhitelistTokenModel(models.Model):
    """Model representing hashed whitelist tokens for user authentication"""
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="whitelist_tokens", blank=True, null=True)
    token_fingerprint = models.CharField(blank=False,null=False,default="e99a18c428cb38d5f",max_length=64, unique=True, verbose_name="Token Fingerprint")
    refresh_token_fingerprint = models.CharField(blank=False,null=False,default="e99a18c428cb38d5f",max_length=64, unique=True, verbose_name="Refresh Token Fingerprint")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Token for {self.user.phone_number}"  

    class Meta:
        verbose_name = "User Whitelist Token"
        verbose_name_plural = "User Whitelist Tokens"
        ordering = ["user"]


class TransactionModel(BaseModel):
    sender = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="sent_transactions")
    receiver = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="received_transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD") 
    transaction_ref_id = models.CharField(max_length=100, unique=True)
    status = models.IntegerField(choices=TransactionStatusChoices.choices, default=TransactionStatusChoices.PENDING)
    mtn_response_data = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.transaction_ref_id} - {self.status}"
    
    class Meta:
        verbose_name = "User Transaction"
        verbose_name_plural = "User Transactions"
        ordering = ['-created_at']
        




