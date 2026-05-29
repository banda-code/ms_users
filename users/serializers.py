from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

class DepartmentResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'password',
            'first_name',
            'last_name',
            'ci',
            'phone',
        )


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'ci',
            'phone',
            'role',
            'is_verified',
            'profile_completed',
        )
        read_only_fields = ('role', 'is_verified')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField()
    password_nueva = serializers.CharField(min_length=8)


class PerfilSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'ci',
            'phone',
            'role',
            'is_verified',
            'profile_completed',
            'department',
            'created_at',
        )
        read_only_fields = ('email', 'role', 'is_verified', 'created_at')

    @extend_schema_field(DepartmentResumenSerializer)
    def get_department(self, obj):
        if obj.department:
            return {'id': obj.department.id, 'name': obj.department.name}
        return None
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # ✅ Estos datos viajan en el JWT a todos los microservicios
        token['user_id']     = str(user.id)
        token['email']       = user.email
        token['role']        = user.role
        token['is_verified'] = user.is_verified

        return token