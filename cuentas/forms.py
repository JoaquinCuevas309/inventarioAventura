from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Usuario


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs['class'] = 'form-check-input'
            else:
                campo.widget.attrs['class'] = 'form-control'


class RegistroTuristaForm(BootstrapMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('first_name', 'last_name', 'email'):
            self.fields[campo].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = 'turista'
        if commit:
            usuario.save()
        return usuario


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput, required=False)

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'is_active']
        labels = {
            'username': 'Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'email': 'Correo electronico',
            'telefono': 'Telefono',
            'rol': 'Rol',
            'is_active': 'Usuario activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('first_name', 'last_name', 'email'):
            self.fields[campo].required = True
        if self.instance.pk:
            self.fields['password1'].help_text = 'Dejala en blanco para no cambiar la contraseña.'

    def clean(self):
        datos = super().clean()
        if datos.get('password1') != datos.get('password2'):
            self.add_error('password2', 'Las contraseñas no coinciden.')
        elif not self.instance.pk and not datos.get('password1'):
            self.add_error('password1', 'Este campo es obligatorio.')
        elif datos.get('password1'):
            candidato = Usuario(
                username=datos.get('username', ''),
                first_name=datos.get('first_name', ''),
                last_name=datos.get('last_name', ''),
                email=datos.get('email', ''),
            )
            try:
                password_validation.validate_password(datos['password1'], candidato)
            except ValidationError as error:
                self.add_error('password1', error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario
