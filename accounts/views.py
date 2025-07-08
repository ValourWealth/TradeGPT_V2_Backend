# accounts/views.py

from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import SignupSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

class LoginView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
