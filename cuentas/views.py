from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from experiencias.models import Categoria, Experiencia, Inscripcion

from .forms import RegistroTuristaForm, UsuarioForm
from .mixins import AdminRequiredMixin, ContextoFormularioMixin
from .models import Usuario


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
            contexto['total_experiencias'] = Experiencia.objects.filter(creador=usuario).count()
            contexto['total_reservas'] = Inscripcion.objects.filter(experiencia__creador=usuario).count()
        else:
            contexto['total_reservas'] = Inscripcion.objects.filter(usuario=usuario).count()
            contexto['total_disponibles'] = Experiencia.objects.disponibles().count()
        return contexto


class PerfilView(LoginRequiredMixin, TemplateView):
    template_name = 'cuentas/perfil.html'


class UsuarioListView(AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'cuentas/usuario_lista.html'
    context_object_name = 'usuarios'


class UsuarioCreateView(AdminRequiredMixin, ContextoFormularioMixin, CreateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Registrar usuario'
    url_volver = 'usuario_lista'


class UsuarioUpdateView(AdminRequiredMixin, ContextoFormularioMixin, UpdateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Editar usuario'
    url_volver = 'usuario_lista'


class UsuarioDeleteView(AdminRequiredMixin, ContextoFormularioMixin, DeleteView):
    model = Usuario
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('usuario_lista')
    titulo = 'Eliminar usuario'
    url_volver = 'usuario_lista'
    aviso = 'Se eliminaran tambien sus experiencias y reservas. Esta accion no se puede deshacer.'

    def get_queryset(self):
        return Usuario.objects.exclude(pk=self.request.user.pk)
