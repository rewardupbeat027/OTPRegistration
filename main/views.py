import datetime
import json

from django.contrib.sites import requests
from django.shortcuts import render
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RegistrationModel
from .serializers import ProfileSerializer


# Create your views here.
def generate_transaction_id(username):
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y%m%d%H%M")

    return f"{username}{formatted_datetime}"


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')

        if not username:
            return Response({'message': 'Требуется имя пользователя.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = RegistrationModel.objects.get(user__username=username)
        except RegistrationModel.DoesNotExist:
            return Response({'message': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

        if student.status:
            return Response({'message': 'Пользователь уже подтвержден.'}, status=status.HTTP_400_BAD_REQUEST)

        phone = student.phone_numbers
        try:
            send_otp_code(generate_transaction_id(username), phone)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'OTP успешно отправлен.'}, status=status.HTTP_200_OK)


def save_token_to_server(transaction_id, token):
    try:
        student = RegistrationModel.objects.get(user__username=transaction_id)
        print(transaction_id)
        student.otp_token = token
        print(token)
        print(student.otp_token)
        student.save()
    except RegistrationModel.DoesNotExist:
        raise serializers.ValidationError("Неверный идентификатор транзакции")


def get_token_from_server(transaction_id):
    try:
        student = RegistrationModel.objects.get(user__username=transaction_id)
        return student.otp_token
    except RegistrationModel.DoesNotExist:
        return None


def send_otp_code(transaction_id, phone):
    url = 'https://smspro.nikita.kg/api/otp/send'
    api_key = '17cd096ba91b288e64ed6512661cb010'

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    data = {
        'transaction_id': transaction_id,
        'phone': phone
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_data = response.json()

    if response.status_code == 200 and response_data.get('status') == 0:
        token = response_data.get('token')
        print(token)
        save_token_to_server(transaction_id[:-12], token)
        return token
    else:
        error_message = f"Failed to send OTP. Response status code: {response.status_code}."
        if response_data.get('status') is not None:
            error_message += f" Server status: {response_data.get('status')}."
        if response_data.get('error_message'):
            error_message += f" Error details: {response_data.get('error_message')}."
        raise Exception(error_message)


def verify_otp_code(token, code):
    url = 'https://smspro.nikita.kg/api/otp/verify'
    api_key = '17cd096ba91b288e64ed6512661cb010'

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    data = {
        'token': token,
        'code': code
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_data = response.json()

    if response.status_code == 200 and response_data.get('status') == 0:
        return True
    else:
        return False


# class RegistrationAPIView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = ProfileSerializer
#     permission_classes = []
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#
#         if serializer.is_valid():
#             user = serializer.save()
#             data = {
#                 "user_id": user.id,
#                 "message": "User registered successfully."
#             }
#             return Response(data, status=status.HTTP_201_CREATED)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ProfileSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            transaction_id = serializer.validated_data['user']
            token = student.otp_token
            save_token_to_server(transaction_id, token)
            phone = serializer.validated_data['phone']
            send_otp_code(generate_transaction_id(transaction_id), phone)
            request.session['transaction_id'] = transaction_id

            student = RegistrationModel.objects.get(user__username=transaction_id)
            token = student.otp_token
            # Отправить токен вместе с сообщением об успешной регистрации
            return Response({
                "message": "User created successfully.",
                "token": token  # Включаем токен в ответ
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        code = request.data.get('code')

        if not token or not code:
            return Response({'message': 'Token and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        url = 'https://smspro.nikita.kg/api/otp/verify'
        api_key = '17cd096ba91b288e64ed6512661cb010'

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        try:
            student = RegistrationModel.objects.get(otp_token=token)
        except RegistrationModel.DoesNotExist:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'token': token,
            'code': code
        }

        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        print(response_data)

        if response_data.get('status') == 0 and response_data.get('description') == 'Valid Code':
            student.status = True
            student.save()

            return Response({'message': 'Проверка успешна. Статус пользователя обновлен на True.'},
                            status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Проверка неуспешна'}, status=status.HTTP_400_BAD_REQUEST)


# class UserRegistrationView(generics.CreateAPIView):
#     queryset = RegistrationModel.objects.all()
#     serializer_class = ProfileSerializer
#     permission_classes = []
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#
#         if serializer.is_valid():
#             phone = serializer.save()
#             data = {
#                 "phone_id": phone.id,
#                 "message": "User registered successfully."
#             }
#             return Response(data, status=status.HTTP_201_CREATED)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

