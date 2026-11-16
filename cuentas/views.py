from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, ListView, TemplateView, UpdateView

from experiencias.models import Categoria, Experiencia, Inscripcion

from .forms import MiPerfilForm, RecuperarClaveForm, RegistroTuristaForm, UsuarioForm
from .mixins import AdminRequiredMixin, ContextoFormularioMixin, EliminarProtegidoMixin
from .models import Usuario


INTENTOS_MAXIMOS_RECUPERACION = 5
VENTANA_RECUPERACION = 900
MENSAJE_SIN_CUENTA = (
    'No encontramos una cuenta que se pueda recuperar con esos datos. '
    'Verifica el usuario y el correo, o contacta al administrador.'
)


def usuario_recuperable(username, email):
    return Usuario.objects.filter(
        username=username,
        email__iexact=email,
        is_active=True,
        is_superuser=False,
        is_staff=False,
    ).exclude(rol='admin').first()


class RecuperarClaveView(FormView):
    form_class = RecuperarClaveForm
    template_name = 'registration/recuperar_clave.html'
    success_url = reverse_lazy('login')

    def claves_de_intentos(self, username):
        direccion = self.request.META.get('REMOTE_ADDR', '')
        return [f'recuperar_ip_{direccion}', f'recuperar_usuario_{username.lower()}']

    def limite_excedido(self, username):
        return any(cache.get(clave, 0) >= INTENTOS_MAXIMOS_RECUPERACION for clave in self.claves_de_intentos(username))

    def registrar_intento_fallido(self, username):
        for clave in self.claves_de_intentos(username):
            cache.add(clave, 0, VENTANA_RECUPERACION)
            cache.incr(clave)

    def limpiar_intentos(self, username):
        cache.delete_many(self.claves_de_intentos(username))

    def form_valid(self, form):
        username = form.cleaned_data['username']
        if self.limite_excedido(username):
            form.add_error(None, 'Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentarlo.')
            return self.form_invalid(form)
        usuario = usuario_recuperable(username, form.cleaned_data['email'])
        if usuario is None:
            self.registrar_intento_fallido(username)
            form.add_error(None, MENSAJE_SIN_CUENTA)
            return self.form_invalid(form)
        usuario.set_password(form.cleaned_data['new_password1'])
        usuario.save(update_fields=['password'])
        self.limpiar_intentos(username)
        messages.success(self.request, 'Tu contraseña fue actualizada. Ya puedes iniciar sesion.')
        return super().form_valid(form)


class RegistroView(CreateView):
    form_class = RegistroTuristaForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'cuentas/dashboard.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        if usuario.rol == 'admin':
            contexto['total_usuarios'] = Usuario.objects.count()
            contexto['total_categorias'] = Categoria.objects.count()
            contexto['total_experiencias'] = Experiencia.objects.count()
            contexto['total_reservas'] = Inscripcion.objects.count()
        elif usuario.rol == 'guia':
            propias = Experiencia.objects.filter(creador=usuario)
            contexto['total_experiencias'] = propias.count()
            contexto['total_reservas'] = Inscripcion.objects.filter(experiencia__creador=usuario).count()
            contexto['rutas_en_curso'] = propias.filter(estado='en_curso').count()
            contexto['proximas'] = propias.filter(
                Q(estado='en_curso') | Q(estado='programada', fecha_hora__gte=timezone.now())
            ).select_related('categoria').order_by('fecha_hora')[:5]
        else:
            contexto['total_reservas'] = Inscripcion.objects.filter(usuario=usuario).count()
            contexto['total_disponibles'] = Experiencia.objects.disponibles().count()
        return contexto


def motivo_bloqueo_eliminacion(usuario):
    if usuario.is_superuser or usuario.is_staff:
        return 'Las cuentas con acceso al sitio de administracion de Django no se pueden eliminar desde la aplicacion.'
    if usuario.rol == 'admin':
        otros = Usuario.objects.filter(rol='admin', is_active=True).exclude(pk=usuario.pk)
        if not otros.exists():
            return 'Eres el unico administrador activo. Crea otro administrador antes de eliminar tu cuenta.'
    if usuario.experiencias_creadas.exists():
        return 'Tu cuenta tiene tours creados y no se puede eliminar. Pide a un administrador que la desactive para conservar el historial.'
    return ''


class PerfilView(LoginRequiredMixin, UpdateView):
    form_class = MiPerfilForm
    template_name = 'cuentas/perfil.html'
    success_url = reverse_lazy('perfil')

    def get_object(self, queryset=None):
        return Usuario.objects.get(pk=self.request.user.pk)

    def form_valid(self, form):
        messages.success(self.request, 'Tus datos fueron actualizados.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        contexto['motivo_bloqueo'] = motivo_bloqueo_eliminacion(usuario)
        contexto['total_reservas'] = Inscripcion.objects.filter(usuario=usuario).count()
        return contexto


class EliminarCuentaView(LoginRequiredMixin, View):
    def post(self, request):
        usuario = Usuario.objects.get(pk=request.user.pk)
        if not usuario.check_password(request.POST.get('password', '')):
            messages.error(request, 'La contraseña ingresada no es correcta. Tu cuenta no fue eliminada.')
            return redirect('perfil')
        motivo = motivo_bloqueo_eliminacion(usuario)
        if motivo:
            messages.error(request, motivo)
            return redirect('perfil')
        with transaction.atomic():
            logout(request)
            usuario.inscripciones.all().delete()
            usuario.delete()
        messages.success(request, 'Tu cuenta fue eliminada correctamente.')
        return redirect('inicio')


class UsuariosGestionablesMixin:
    def get_queryset(self):
        consulta = Usuario.objects.all()
        if not self.request.user.is_superuser:
            consulta = consulta.exclude(Q(is_superuser=True) | Q(is_staff=True))
        return consulta


class UsuarioListView(AdminRequiredMixin, UsuariosGestionablesMixin, ListView):
    template_name = 'cuentas/usuario_lista.html'
    context_object_name = 'usuarios'


class UsuarioCreateView(AdminRequiredMixin, ContextoFormularioMixin, CreateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Registrar usuario'
    url_volver = 'usuario_lista'


class UsuarioUpdateView(
    AdminRequiredMixin, UsuariosGestionablesMixin, ContextoFormularioMixin, UpdateView
):
    form_class = UsuarioForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Editar usuario'
    url_volver = 'usuario_lista'


class UsuarioDeleteView(
    AdminRequiredMixin,
    UsuariosGestionablesMixin,
    EliminarProtegidoMixin,
    ContextoFormularioMixin,
    DeleteView,
):
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Eliminar usuario'
    url_volver = 'usuario_lista'
    aviso = 'Solo se puede eliminar si no tiene reservas ni tours asociados. Si los tiene, desactiva la cuenta desde Editar.'
    mensaje_protegido = (
        'No se puede eliminar: el usuario tiene reservas o tours asociados. '
        'Desactivalo desde Editar para conservar el historial.'
    )

    def get_queryset(self):
        return super().get_queryset().exclude(pk=self.request.user.pk)
