# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    AsignarAdminDepartamentoView,
    QuitarAdminDepartamentoView,
    RegisterView,
    LoginView,
    LogoutView,
    PerfilView,
    CambiarPasswordView,
    ListarUsuariosView,
    CrearUsuarioStaffAdminView,
    ResumenDepartamentosView,
    ToggleActivarUsuarioView,
    ActivarCuentaView,          # ← nuevo
    SolicitarResetPasswordView, # ← nuevo
    ResetPasswordView,          # ← nuevo
    PagosPorDepartamentoIdView,
)

urlpatterns = [
    # Públicas
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Autenticado
    path('logout/', LogoutView.as_view(), name='logout'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),
    path('activar/<str:token>/',   ActivarCuentaView.as_view(),          name='activar-cuenta'),       # ← nuevo
    path('reset-password/',        SolicitarResetPasswordView.as_view(), name='reset-password'),       # ← nuevo
    path('reset-password/confirmar/', ResetPasswordView.as_view(),       name='reset-password-confirmar'), # ← nuevo

    # Solo admin
    path('admin/todos/', ListarUsuariosView.as_view(), name='listar-usuarios'),
    path('admin/crear-usuario/', CrearUsuarioStaffAdminView.as_view(), name='crear-usuario'),
    path('admin/<uuid:pk>/activar/', ToggleActivarUsuarioView.as_view(), name='toggle-activar'),
    path('admin/departamentos/', ResumenDepartamentosView.as_view(), name='resumen-departamentos'),
    path('admin/asignar-admin/', AsignarAdminDepartamentoView.as_view(), name='asignar-admin'),
    path('admin/quitar-admin/', QuitarAdminDepartamentoView.as_view(), name='quitar-admin'),
    path('departamento-id/', PagosPorDepartamentoIdView.as_view(), name='pagos-por-departamento-id'),
]