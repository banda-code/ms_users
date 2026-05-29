from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('id', 'email', 'role', 'is_verified', 'is_active')  # ✅ quitamos 'department'
    list_filter   = ('role', 'is_verified', 'is_active')                  # ✅ quitamos 'department'
    search_fields = ('email', 'username')
    ordering      = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {
            'fields': (
                'role', 'department_id', 'ci', 'phone',
                'is_verified', 'profile_completed',
                'activation_token', 'reset_token',
            )
        }),
    )