from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):

    ROLE_CHOICES = (
        ('citizen', 'Ciudadano'),
        ('staff', 'Personal'),
        ('admin', 'Administrador'),
        ('superadmin', 'Super Admin'),
    )

    # ✅ UUID como primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    ci    = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)  # 👈 AGREGAR

    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    department_id = models.UUIDField(null=True, blank=True)

    is_verified       = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    activation_token = models.CharField(max_length=100, null=True, blank=True)
    reset_token      = models.CharField(max_length=100, null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True
    )

    def __str__(self):
        return f"{self.email} - {self.role}"