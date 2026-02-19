from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserAuthViewSet,
    UserPaymentWithMTN,
    UserPaymentWithOrange
)
from .views import OrangeWebhookView


client_router = DefaultRouter()
client_router.register(r'user', UserAuthViewSet, basename='user')
client_router.register(r'initiate/mtn', UserPaymentWithMTN, basename='initiate/mtn')
client_router.register(r'initiate/orange', UserPaymentWithOrange, basename='initiate/orange')


urlpatterns = [
    path('', include(client_router.urls)),
    path('api/webhook/', OrangeWebhookView.as_view(), name='orange-webhook'),
]