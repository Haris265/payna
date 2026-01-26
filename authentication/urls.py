from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserAuthViewSet,
    UserPaymentWithMTN
)


client_router = DefaultRouter()
client_router.register(r'user', UserAuthViewSet, basename='user')
client_router.register(r'initiate/mtn', UserPaymentWithMTN, basename='initiate/mtn')

urlpatterns = [
    path('', include(client_router.urls)),
]