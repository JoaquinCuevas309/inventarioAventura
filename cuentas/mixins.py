from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    roles_permitidos = ()

    def test_func(self):
        return self.request.user.rol in self.roles_permitidos


class AdminRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('admin',)


class AdminOGuiaRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('admin', 'guia')


class GuiaRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('guia',)


class TuristaRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('turista',)


class ContextoFormularioMixin:
    titulo = ''
    url_volver = ''
    aviso = ''

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = self.titulo
        contexto['url_volver'] = reverse(self.url_volver)
        contexto['aviso'] = self.aviso
        return contexto


class EliminarProtegidoMixin:
    mensaje_protegido = 'No se puede eliminar: el registro esta asociado a otros datos. Desactivalo para conservar el historial.'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.mensaje_protegido)
            return redirect(self.get_success_url())
