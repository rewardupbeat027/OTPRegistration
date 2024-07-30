
from django.urls import path
from . import views

urlpatterns = [
    path('v1/register/', views.RegistrationAPIView.as_view(), name='register'),
    path('v1/verify/otp/', views.OTPVerificationView.as_view(), name='otp_verification'),
    path('v1/verify/', views.ResendOTPView.as_view(), name='verification'),
]
