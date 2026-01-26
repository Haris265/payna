from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserAuthViewSet


client_router = DefaultRouter()
client_router.register(r'user', UserAuthViewSet, basename='user')


urlpatterns = [
    path('', include(client_router.urls)),
]