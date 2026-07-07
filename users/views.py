# users/views.py
import sys

from .serializers import (
    LoginSerializer,
    CambiarPasswordSerializer,
    PerfilSerializer,
    UserCreateSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,  # ✅ agregado
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import request, status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from rest_framework import serializers as drf_serializers
from django.core.paginator import Paginator
import secrets
import requests as http_requests  # ✅ para llamadas HTTP a otros servicios
import os

# ── URLs de otros microservicios ─────────────────────────────────────
CERTIFICATES_SERVICE_URL = os.environ.get('CERTIFICATES_SERVICE_URL', 'http://localhost:8002')
PAYMENTS_SERVICE_URL     = os.environ.get('PAYMENTS_SERVICE_URL',     'http://localhost:8003')


# ── Helpers HTTP ─────────────────────────────────────────────────────

def get_department(dept_id, token=None):
    """Consulta ms_certificates para obtener un departamento por id"""
    try:
        internal_token = os.environ.get('INTERNAL_SERVICE_TOKEN', '')
        headers = {
            "Authorization": f"Internal {internal_token}",
            "Host": "test.armada.mil.bo"
        }
        all_depts = get_all_departments(token)
        for d in all_depts:
            if str(d.get('id')) == str(dept_id):
                return d
        return None
    except Exception:
        return None


def get_all_departments(token=None):
    """Consulta ms_certificates para obtener todos los departamentos"""
    try:
        internal_token = os.environ.get('INTERNAL_SERVICE_TOKEN', '')
        headers = {
            "Authorization": f"Internal {internal_token}",
            "Host": "test.armada.mil.bo"
        }
        response = http_requests.get(
            f"{CERTIFICATES_SERVICE_URL}/api/certificates/departments/",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return []
    except http_requests.exceptions.RequestException:
        return []


def get_pagos_departamento(dept_id, token=None):
    """Consulta ms_payments para obtener pagos de un departamento"""
    try:
        internal_token = os.environ.get('INTERNAL_SERVICE_TOKEN', '')
        headers = {
            "Authorization": f"Internal {internal_token}",
            "Host": "test.armada.mil.bo"
        }
        response = http_requests.get(
            f"{PAYMENTS_SERVICE_URL}/api/payments/departamento-id/?department_id={dept_id}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return []
    except http_requests.exceptions.RequestException:
        return []


# ── Serializer auxiliar ───────────────────────────────────────────────

class LogoutSerializer(drf_serializers.Serializer):
    refresh = drf_serializers.CharField()


# ── Vistas ────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = UserCreateSerializer

    def post(self, request):
        data = request.data

        required = ['email', 'password', 'first_name']
        for field in required:
            if not data.get(field):
                return Response(
                    {'error': f'El campo {field} es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if User.objects.filter(email=data['email']).exists():
            return Response(
                {'error': 'El email ya está registrado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            data['email'],
            data['email'],
            data['password'],
            first_name  = data.get('first_name', ''),
            last_name   = data.get('last_name',  ''),
            ci          = data.get('ci',          ''),
            phone       = data.get('phone',       ''),
            role        = 'citizen',
            is_active   = False,
            is_verified = False,
        )
        # ✅ Marca profile_completed si tiene los datos necesarios
        if user.first_name and user.last_name and user.ci:
            user.profile_completed = True
            user.save()

        token = secrets.token_urlsafe(32)
        user.activation_token = token
        user.save()

        url_activacion = f"{settings.FRONTEND_URL}/activar/{token}"
        try:
            send_mail(
                subject      = "Activa tu cuenta",
                message      = f"Hola {user.first_name},\n\nActiva tu cuenta aquí:\n{url_activacion}",
                from_email   = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [user.email],
                fail_silently  = False,
            )
        except Exception as e:
            import sys

            print(f">>> ERROR EMAIL: {e}", file=sys.stderr)
            user.delete()
            return Response(
                {'error': f'No se pudo enviar el email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {'message': 'Cuenta creada. Revisa tu email para activarla.'},
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = LoginSerializer

    def post(self, request):
        email    = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email y password son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {'error': 'Credenciales incorrectas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Cuenta desactivada'},
                status=status.HTTP_403_FORBIDDEN
            )

        # ✅ Usamos el serializer personalizado para incluir role, email, user_id en el JWT
        refresh = CustomTokenObtainPairSerializer.get_token(user)

        return Response({
            'user': {
                'id':                user.id,
                'email':             user.email,
                'username':          user.username,
                'first_name':        user.first_name,
                'last_name':         user.last_name,
                'ci':                user.ci,
                'phone':             user.phone,
                'fecha_nacimiento':  user.fecha_nacimiento.isoformat() if hasattr(user.fecha_nacimiento, 'isoformat') else user.fecha_nacimiento,
                'role':              user.role,
                'is_verified':       user.is_verified,
                'profile_completed': user.profile_completed,
            },
            'tokens': {
                'refresh': str(refresh),
                'access':  str(refresh.access_token),
            }
        })


class LogoutView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = LogoutSerializer

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Sesión cerrada correctamente'})
        except Exception:
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PerfilSerializer

    def get(self, request):
        user = request.user
        return Response({
            'id':                user.id,
            'email':             user.email,
            'username':          user.username,
            'first_name':        user.first_name,
            'last_name':         user.last_name,
            'ci':                user.ci,
            'phone':             user.phone,
            'fecha_nacimiento':  user.fecha_nacimiento.isoformat() if hasattr(user.fecha_nacimiento, 'isoformat') else user.fecha_nacimiento,
            'role':              user.role,
            'is_verified':       user.is_verified,
            'profile_completed': user.profile_completed,
            # ✅ department_id ya no es FK, consultamos si es necesario
            'department_id':     str(user.department_id) if user.department_id else None,
            'created_at':        user.created_at,
        })

    def put(self, request):
        print(">>> ENTRÓ AL PUT PERFIL")
        print(">>> USUARIO:", request.user.id, request.user.email)
        print(">>> DATA:", request.data)
        user = request.user
        data = request.data

        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name',  user.last_name)
        user.ci         = data.get('ci',         user.ci)
        user.phone      = data.get('phone',      user.phone)
        user.fecha_nacimiento = data.get('fecha_nacimiento', user.fecha_nacimiento)

        if user.first_name and user.last_name and user.ci:
            user.profile_completed = True

        user.save()
        print(">>> DESPUÉS DE SAVE:", user.first_name, user.last_name, user.ci, user.phone)

        return Response({
            'id':                user.id,
            'email':             user.email,
            'username':          user.username,
            'first_name':        user.first_name,
            'last_name':         user.last_name,
            'ci':                user.ci,
            'phone':             user.phone,
            'fecha_nacimiento':  user.fecha_nacimiento.isoformat() if hasattr(user.fecha_nacimiento, 'isoformat') else user.fecha_nacimiento,
            'role':              user.role,
            'is_verified':       user.is_verified,
            'profile_completed': user.profile_completed,
        })


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = CambiarPasswordSerializer

    def post(self, request):
        user            = request.user
        password_actual = request.data.get('password_actual')
        password_nueva  = request.data.get('password_nueva')

        if not password_actual or not password_nueva:
            return Response(
                {'error': 'Debes enviar password_actual y password_nueva'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password_actual):
            return Response(
                {'error': 'La contraseña actual es incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password_nueva) < 8:
            return Response(
                {'error': 'La nueva contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(password_nueva)
        user.save()
        return Response({'message': 'Contraseña actualizada correctamente'})


class ListarUsuariosView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def get(self, request):
        if request.user.role not in ['admin', 'superadmin']:
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        page        = int(request.query_params.get('page',      1))
        page_size   = int(request.query_params.get('page_size', 10))
        search      = request.query_params.get('search', '')
        role_filter = request.query_params.get('role',   '')

        qs = User.objects.order_by('-created_at')

        if request.user.role == 'admin':
            qs = qs.filter(role='citizen')

        if search:
            qs = qs.filter(email__icontains=search)

        if role_filter:
            qs = qs.filter(role=role_filter)

        paginator = Paginator(qs, page_size)
        pagina    = paginator.get_page(page)

        data = [
            {
                'id':          u.id,
                'email':       u.email,
                'username':    u.username,
                'first_name':  u.first_name,
                'last_name':   u.last_name,
                'role':        u.role,
                'is_active':   u.is_active,
                'is_verified': u.is_verified,
                # ✅ ya no navegamos u.department.name
                'department_id': str(u.department_id) if u.department_id else None,
                'created_at':  u.created_at,
            }
            for u in pagina
        ]

        return Response({
            'count':    paginator.count,
            'next':     pagina.has_next(),
            'previous': pagina.has_previous(),
            'results':  data,
        })


class CrearUsuarioStaffAdminView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserCreateSerializer

    def post(self, request):
        if request.user.role != 'superadmin':
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        rol  = data.get('role')

        if rol not in ['staff', 'admin']:
            return Response(
                {'error': 'Solo puedes crear usuarios staff o admin'},
                status=status.HTTP_400_BAD_REQUEST
            )

        required = ['email', 'password', 'username', 'department_id']
        for field in required:
            if not data.get(field):
                return Response(
                    {'error': f'El campo {field} es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if User.objects.filter(email=data['email']).exists():
            return Response(
                {'error': 'El email ya está registrado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Verificamos que el departamento existe via HTTP
        token      = request.auth
        department = get_department(data['department_id'], token)
        if not department:
            return Response(
                {'error': 'Departamento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = User.objects.create_user(
            email       = data['email'],
            username    = data['username'],
            password    = data['password'],
            first_name  = data.get('first_name', ''),
            last_name   = data.get('last_name',  ''),
            role        = rol,
            department_id = data['department_id'],  # ✅ solo el UUID
            is_verified = True,
        )

        return Response({
            'message':    f'Usuario {rol} creado exitosamente',
            'user': {
                'id':         user.id,
                'email':      user.email,
                'role':       user.role,
                'department': department.get('name'),  # ✅ del JSON del microservicio
            }
        }, status=status.HTTP_201_CREATED)


class ToggleActivarUsuarioView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def put(self, request, pk):
        if request.user.role not in ['admin', 'superadmin']:
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if user == request.user:
            return Response(
                {'error': 'No puedes desactivar tu propia cuenta'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = not user.is_active
        user.save()

        estado = 'activado' if user.is_active else 'desactivado'
        return Response({
            'message':   f'Usuario {estado} correctamente',
            'is_active': user.is_active,
        })


class ActivarCuentaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(activation_token=token)
        except User.DoesNotExist:
            return Response(
                {'error': 'Token inválido o expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active        = True
        user.is_verified      = True
        user.activation_token = None
        user.save()

        return Response({'message': 'Cuenta activada correctamente. Ya puedes iniciar sesión.'})


class SolicitarResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'El email es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'Si el email existe, recibirás un enlace.'})

        token          = secrets.token_urlsafe(32)
        user.reset_token = token
        user.save()

        url_reset = f"{settings.FRONTEND_URL}/reset-password/{token}"
        try:
            send_mail(
                subject        = "Recuperar contraseña",
                message        = f"Hola {user.first_name},\n\nRecupera tu contraseña aquí:\n{url_reset}",
                from_email     = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [user.email],
                fail_silently  = False,
            )
        except Exception as e:
            return Response(
                {'error': f'No se pudo enviar el email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'message': 'Si el email existe, recibirás un enlace.'})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token        = request.data.get('token')
        new_password = request.data.get('password')

        if not token or not new_password:
            return Response(
                {'error': 'Token y nueva contraseña son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'La contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(reset_token=token)
        except User.DoesNotExist:
            return Response(
                {'error': 'Token inválido o expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.reset_token = None
        user.save()

        return Response({'message': 'Contraseña actualizada correctamente.'})


class ResumenDepartamentosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'superadmin':
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        token       = request.auth
        # ✅ Una sola llamada HTTP para todos los departamentos
        departamentos = get_all_departments(token)

        data = []
        for dept in departamentos:
            # ✅ Admins del departamento — esto sí lo tenemos en nuestra BD
            admins = User.objects.filter(
                department_id = dept['id'],
                role          = 'admin'
            ).values('id', 'email', 'first_name', 'last_name', 'is_active')

            # ✅ Pagos — consultamos ms_payments
            pagos = get_pagos_departamento(dept['id'], token)
            pagos_completados = [p for p in pagos if p.get('estado') == 'pagado']
            monto_total       = sum(float(p.get('monto', 0)) for p in pagos_completados)

            data.append({
                'id':                dept['id'],
                'nombre':            dept['name'],
                'admins':            list(admins),
                'total_pagos':       len(pagos),
                'pagos_completados': len(pagos_completados),
                'monto_total':       monto_total,
            })

        return Response(data)


class AsignarAdminDepartamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'superadmin':
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id       = request.data.get('user_id')
        department_id = request.data.get('department_id')

        if not user_id or not department_id:
            return Response(
                {'error': 'user_id y department_id son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ Verificamos departamento via HTTP
        token      = request.auth
        department = get_department(department_id, token)
        if not department:
            return Response(
                {'error': 'Departamento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        user.role          = 'admin'
        user.department_id = department_id  # ✅ solo el UUID
        user.save()

        return Response({
            'message':    f'{user.email} asignado como admin de {department["name"]}',
            'user_id':    user.id,
            'email':      user.email,
            'role':       user.role,
            'department': department['name'],
        })


class QuitarAdminDepartamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'superadmin':
            return Response(
                {'error': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        user.role          = 'citizen'
        user.department_id = None  # ✅ limpiamos el UUID
        user.save()

        return Response({
            'message': f'{user.email} ya no es administrador',
            'user_id': user.id,
            'email':   user.email,
            'role':    user.role,
        })

class PagosPorDepartamentoIdView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        auth_header    = request.META.get('HTTP_AUTHORIZATION', '')
        internal_token = os.environ.get('INTERNAL_SERVICE_TOKEN', '')
        if auth_header != f"Internal {internal_token}":
            return Response({'error': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response([])

        try:
            resp_c = http_requests.get(
                f"{settings.CERTIFICATES_SERVICE_URL}/api/certificates/tipos/",
                headers={"Authorization": f"Internal {internal_token}", "Host": "test.armada.mil.bo"},
                timeout=5
            )
            cert_ids_dept = []
            if resp_c.status_code == 200:
                cert_ids_dept = [
                    c['id'] for c in resp_c.json()
                    if c.get('department', {}).get('id') == str(dept_id)
                ]

            resp_s = http_requests.get(
                f"{settings.SOLICITUDES_SERVICE_URL}/api/solicitudes/admin/todas/",
                headers={"Authorization": f"Internal {internal_token}", "Host": "test.armada.mil.bo"},
                timeout=5
            )
            solic_ids_dept = []
            if resp_s.status_code == 200:
                solic_ids_dept = [
                    s['id'] for s in resp_s.json()
                    if s.get('certificate_type_id') in cert_ids_dept
                ]

            pagos = Payment.objects.filter(estado__in=['en_proceso', 'pagado'])
            data = []
            for p in pagos:
                if any(sid in solic_ids_dept for sid in (p.solicitud_ids or [])):
                    data.append({'id': p.id, 'estado': p.estado, 'monto': float(p.monto)})
            return Response(data)
        except Exception:
            return Response([])