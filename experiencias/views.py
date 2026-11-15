from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from cuentas.mixins import (
    AdminOGuiaRequiredMixin,
    AdminRequiredMixin,
    ContextoFormularioMixin,
    TuristaRequiredMixin,
)

from .forms import CategoriaForm, ExperienciaForm, InscripcionForm
from .models import Categoria, Experiencia, Inscripcion
from .services import (
    ReservaError,
    bloquear_experiencia,
    crear_reserva,
    validar_cupo,
    validar_experiencia_reservable,
)


class CategoriaListView(AdminRequiredMixin, ListView):
    model = Categoria
    template_name = 'experiencias/categoria_lista.html'
    context_object_name = 'categorias'


class CategoriaCreateView(AdminRequiredMixin, ContextoFormularioMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('categoria_lista')
    titulo = 'Nueva categoria'
    url_volver = 'categoria_lista'


class CategoriaUpdateView(AdminRequiredMixin, ContextoFormularioMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('categoria_lista')
    titulo = 'Editar categoria'
    url_volver = 'categoria_lista'


class CategoriaDeleteView(AdminRequiredMixin, ContextoFormularioMixin, DeleteView):
    model = Categoria
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('categoria_lista')
    titulo = 'Eliminar categoria'
    url_volver = 'categoria_lista'
    aviso = 'Se eliminaran tambien las experiencias de esta categoria y sus reservas.'


class ExperienciaPanelQuerysetMixin:
    def get_queryset(self):
        consulta = Experiencia.objects.select_related('categoria', 'creador').con_inscritos()
        if self.request.user.rol == 'guia':
            consulta = consulta.filter(creador=self.request.user)
        return consulta


class ExperienciaListView(AdminOGuiaRequiredMixin, ExperienciaPanelQuerysetMixin, ListView):
    template_name = 'experiencias/experiencia_lista.html'
    context_object_name = 'experiencias'


class ExperienciaCreateView(AdminOGuiaRequiredMixin, ContextoFormularioMixin, CreateView):
    model = Experiencia
    form_class = ExperienciaForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('experiencia_lista')
    titulo = 'Nueva experiencia'
    url_volver = 'experiencia_lista'

    def form_valid(self, form):
        form.instance.creador = self.request.user
        return super().form_valid(form)


class ExperienciaUpdateView(
    AdminOGuiaRequiredMixin, ExperienciaPanelQuerysetMixin, ContextoFormularioMixin, UpdateView
):
    form_class = ExperienciaForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('experiencia_lista')
    titulo = 'Editar experiencia'
    url_volver = 'experiencia_lista'

    def form_valid(self, form):
        try:
            with transaction.atomic():
                experiencia = bloquear_experiencia(self.object.pk)
                reservas = experiencia.inscripciones.count()
                if form.cleaned_data['cupo_maximo'] < reservas:
                    raise ReservaError(
                        f'El cupo maximo no puede ser menor a las reservas actuales ({reservas}).'
                    )
                return super().form_valid(form)
        except ReservaError as error:
            form.add_error('cupo_maximo', str(error))
            return self.form_invalid(form)


class ExperienciaDeleteView(AdminRequiredMixin, ContextoFormularioMixin, DeleteView):
    model = Experiencia
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('experiencia_lista')
    titulo = 'Eliminar experiencia'
    url_volver = 'experiencia_lista'
    aviso = 'Se eliminaran tambien las reservas asociadas a esta experiencia.'


class CatalogoView(ListView):
    template_name = 'experiencias/catalogo.html'
    context_object_name = 'experiencias'

    def get_queryset(self):
        return Experiencia.objects.disponibles().select_related('categoria').con_inscritos()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        ids = self.request.session.get('experiencias_vistas', [])
        vistas = {e.pk: e for e in Experiencia.objects.filter(pk__in=ids)}
        contexto['ultimas_vistas'] = [vistas[pk] for pk in ids if pk in vistas]
        return contexto


class ExperienciaDetalleView(DetailView):
    template_name = 'experiencias/experiencia_detalle.html'
    context_object_name = 'experiencia'

    def get_queryset(self):
        return (
            Experiencia.objects.filter(activa=True, categoria__activo=True)
            .select_related('categoria', 'creador')
            .con_inscritos()
        )

    def get(self, request, *args, **kwargs):
        respuesta = super().get(request, *args, **kwargs)
        vistas = request.session.get('experiencias_vistas', [])
        if self.object.pk in vistas:
            vistas.remove(self.object.pk)
        vistas.insert(0, self.object.pk)
        request.session['experiencias_vistas'] = vistas[:5]
        return respuesta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        contexto['ya_reservada'] = (
            usuario.is_authenticated
            and Inscripcion.objects.filter(usuario=usuario, experiencia=self.object).exists()
        )
        return contexto


class ReservarView(TuristaRequiredMixin, View):
    def post(self, request, pk):
        experiencia = get_object_or_404(Experiencia, pk=pk, activa=True, categoria__activo=True)
        try:
            crear_reserva(request.user, experiencia.pk)
        except ReservaError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, 'Reserva registrada. Estado de pago: Pendiente.')
        return redirect('mis_reservas')


class MisReservasView(TuristaRequiredMixin, ListView):
    template_name = 'experiencias/mis_reservas.html'
    context_object_name = 'reservas'

    def get_queryset(self):
        return Inscripcion.objects.filter(usuario=self.request.user).select_related(
            'experiencia__categoria'
        )


class InscripcionListView(AdminOGuiaRequiredMixin, ListView):
    template_name = 'experiencias/inscripcion_lista.html'
    context_object_name = 'inscripciones'

    def get_queryset(self):
        consulta = Inscripcion.objects.select_related('usuario', 'experiencia')
        if self.request.user.rol == 'guia':
            consulta = consulta.filter(experiencia__creador=self.request.user)
        return consulta


class InscripcionGuardarMixin:
    def form_valid(self, form):
        try:
            with transaction.atomic():
                experiencia = bloquear_experiencia(form.cleaned_data['experiencia'].pk)
                cambio_experiencia = not form.instance.pk or 'experiencia' in form.changed_data
                if cambio_experiencia:
                    validar_experiencia_reservable(experiencia)
                    validar_cupo(experiencia, excluir_pk=form.instance.pk)
                return super().form_valid(form)
        except ReservaError as error:
            form.add_error('experiencia', str(error))
            return self.form_invalid(form)


class InscripcionCreateView(
    AdminRequiredMixin, InscripcionGuardarMixin, ContextoFormularioMixin, CreateView
):
    model = Inscripcion
    form_class = InscripcionForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('inscripcion_lista')
    titulo = 'Nueva reserva'
    url_volver = 'inscripcion_lista'


class InscripcionUpdateView(
    AdminRequiredMixin, InscripcionGuardarMixin, ContextoFormularioMixin, UpdateView
):
    model = Inscripcion
    form_class = InscripcionForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('inscripcion_lista')
    titulo = 'Editar reserva'
    url_volver = 'inscripcion_lista'


class InscripcionDeleteView(AdminRequiredMixin, ContextoFormularioMixin, DeleteView):
    model = Inscripcion
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('inscripcion_lista')
    titulo = 'Eliminar reserva'
    url_volver = 'inscripcion_lista'
    aviso = 'La reserva se eliminara y el cupo quedara disponible.'
