from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROLES_CHOICES = (
        ('admin', 'Administrador'),
        ('guia', 'Guia / Operador'),
        ('turista', 'Turista / Cliente'),
    )

    rol = models.CharField(max_length=20, choices=ROLES_CHOICES, default='turista')
    telefono = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.rol = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"
