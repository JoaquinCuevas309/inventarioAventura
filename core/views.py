from django.views.generic import TemplateView

from experiencias.models import Categoria, Experiencia


class InicioView(TemplateView):
    template_name = 'core/inicio.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['categorias'] = Categoria.objects.filter(activo=True)
        contexto['destacadas'] = Experiencia.objects.disponibles().select_related('categoria')[:3]
        return contexto
