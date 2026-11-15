from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    roles_permitidos = ()

    def test_func(self):
        return self.request.user.rol in self.roles_permitidos


class AdminRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('admin',)


class AdminOGuiaRequiredMixin(RolRequeridoMixin):
    roles_permitidos = ('admin', 'guia')


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
