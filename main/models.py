from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class RegistrationModel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='registration')
    phone = models.CharField("Номер телефона", max_length=25)
    otp_token = models.CharField("KOd", max_length=255)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.user