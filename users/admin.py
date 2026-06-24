from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User
import requests
import os

def get_departamentos():
    try:
        url = os.environ.get('CERTIFICATES_SERVICE_URL', 'http://ms_certificates:8000')
        resp = requests.get(
            f"{url}/api/certificates/departments/publico/",
            headers={"Host": "test.armada.mil.bo"},
            timeout=3
        )
        if resp.status_code == 200:
            return [(str(d['id']), d['name']) for d in resp.json()]
    except:
        pass
    return []

class UserAdminForm(forms.ModelForm):
    department_id = forms.ChoiceField(
        choices=[],
        required=False,
        label='Departamento'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        departamentos = get_departamentos()
        self.fields['department_id'].choices = [('', '— Sin departamento —')] + departamentos
        if self.instance and self.instance.department_id:
            self.fields['department_id'].initial = str(self.instance.department_id)

    def clean_department_id(self):
        val = self.cleaned_data.get('department_id')
        return val if val else None

    class Meta:
        model  = User
        fields = '__all__'

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    form          = UserAdminForm
    list_display  = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active')
    list_filter   = ('role', 'is_verified', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'ci')
    ordering      = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {
            'fields': (
                'role',
                'department_id',
                'ci',
                'phone',
                'fecha_nacimiento',
                'is_verified',
                'profile_completed',
            )
        }),
    )