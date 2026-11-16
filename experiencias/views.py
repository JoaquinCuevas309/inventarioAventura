import calendar
import datetime

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from cuentas.mixins import (
    AdminOGuiaRequiredMixin,
    AdminRequiredMixin,
    ContextoFormularioMixin,
    EliminarProtegidoMixin,
    GuiaRequiredMixin,
    TuristaRequiredMixin,
)

from .forms import CategoriaForm, ExperienciaForm, InscripcionForm
from .models import Categoria, Experiencia, Inscripcion
from .services import (
    ReservaError,
    RutaError,
    bloquear_experiencia,
    cambiar_estado,
    crear_reserva,
    registrar_asistencia,
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


class CategoriaDeleteView(
    AdminRequiredMixin, EliminarProtegidoMixin, ContextoFormularioMixin, DeleteView
):
    model = Categoria
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('categoria_lista')
    titulo = 'Eliminar categoria'
    url_volver = 'categoria_lista'
    aviso = 'Solo se puede eliminar si no tiene experiencias. Si las tiene, desactivala desde Editar.'
    mensaje_protegido = (
        'No se puede eliminar: la categoria tiene experiencias asociadas. '
        'Desactivala desde Editar para conservar el historial.'
    )


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


class ExperienciaDeleteView(
    AdminRequiredMixin, EliminarProtegidoMixin, ContextoFormularioMixin, DeleteView
):
    model = Experiencia
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('experiencia_lista')
    titulo = 'Eliminar experiencia'
    url_volver = 'experiencia_lista'
    aviso = 'Solo se puede eliminar si no tiene reservas. Si las tiene, elimina las reservas primero o desactiva la experiencia desde Editar.'
    mensaje_protegido = (
        'No se puede eliminar: la experiencia tiene reservas asociadas. '
        'Elimina las reservas primero o desactiva la experiencia desde Editar.'
    )


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


class CancelarReservaView(TuristaRequiredMixin, View):
    def post(self, request, pk):
        reserva = get_object_or_404(Inscripcion.objects.select_related('experiencia'), pk=pk, usuario=request.user)
        if reserva.experiencia.estado in ('en_curso', 'finalizada'):
            messages.error(request, 'No se puede cancelar: la ruta ya comenzo.')
        elif reserva.estado_pago != 'pendiente':
            messages.error(
                request,
                'Solo se pueden cancelar reservas con pago pendiente. Contacta al administrador.',
            )
        else:
            reserva.delete()
            messages.success(request, 'Reserva cancelada. El cupo quedo disponible.')
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


class ConfirmarPagoView(AdminRequiredMixin, View):
    def post(self, request, pk):
        reserva = get_object_or_404(Inscripcion.objects.select_related('usuario', 'experiencia'), pk=pk)
        if reserva.estado_pago == 'confirmado':
            messages.info(request, 'Esta reserva ya tenia el pago confirmado.')
        else:
            reserva.estado_pago = 'confirmado'
            reserva.save(update_fields=['estado_pago'])
            messages.success(
                request,
                f'Pago confirmado: {reserva.usuario.username} en {reserva.experiencia.titulo}.',
            )
        return redirect('inscripcion_lista')


class InscripcionDeleteView(AdminRequiredMixin, ContextoFormularioMixin, DeleteView):
    model = Inscripcion
    template_name = 'confirmar_borrar.html'
    success_url = reverse_lazy('inscripcion_lista')
    titulo = 'Eliminar reserva'
    url_volver = 'inscripcion_lista'
    aviso = 'La reserva se eliminara y el cupo quedara disponible.'


MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
DIAS_SEMANA = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']


class CalendarioView(GuiaRequiredMixin, TemplateView):
    template_name = 'experiencias/calendario.html'

    def mes_solicitado(self):
        try:
            anio, mes = (int(valor) for valor in self.request.GET.get('mes', '').split('-'))
            if not 2000 <= anio <= 2100:
                raise ValueError
            return datetime.date(anio, mes, 1)
        except ValueError:
            return timezone.localdate().replace(day=1)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        primero = self.mes_solicitado()
        anterior = (primero - datetime.timedelta(days=1)).replace(day=1)
        siguiente = (primero + datetime.timedelta(days=32)).replace(day=1)
        zona = timezone.get_current_timezone()
        inicio = datetime.datetime.combine(primero, datetime.time.min, tzinfo=zona)
        fin = datetime.datetime.combine(siguiente, datetime.time.min, tzinfo=zona)
        por_dia = {}
        rutas = Experiencia.objects.filter(
            creador=self.request.user, fecha_hora__gte=inicio, fecha_hora__lt=fin
        ).select_related('categoria')
        for ruta in rutas:
            por_dia.setdefault(timezone.localtime(ruta.fecha_hora).date(), []).append(ruta)
        semanas = []
        for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(primero.year, primero.month):
            semanas.append([
                {
                    'fecha': dia,
                    'en_mes': dia.month == primero.month,
                    'es_hoy': dia == hoy,
                    'rutas': por_dia.get(dia, []),
                }
                for dia in semana
            ])
        contexto['semanas'] = semanas
        contexto['titulo_mes'] = f'{MESES[primero.month - 1]} {primero.year}'
        contexto['mes_anterior'] = anterior.strftime('%Y-%m')
        contexto['mes_siguiente'] = siguiente.strftime('%Y-%m')
        contexto['dias_semana'] = DIAS_SEMANA
        contexto['total_del_mes'] = sum(len(lista) for lista in por_dia.values())
        return contexto


class GrupoDetalleView(GuiaRequiredMixin, DetailView):
    template_name = 'experiencias/grupo_detalle.html'
    context_object_name = 'experiencia'

    def get_queryset(self):
        return Experiencia.objects.filter(creador=self.request.user).select_related('categoria')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        inscripciones = list(self.object.inscripciones.select_related('usuario'))
        contexto['inscripciones'] = inscripciones
        contexto['total_reservas'] = len(inscripciones)
        contexto['confirmados'] = sum(1 for i in inscripciones if i.estado_pago == 'confirmado')
        contexto['asistentes'] = sum(1 for i in inscripciones if i.asistio)
        contexto['cupos_libres'] = max(self.object.cupo_maximo - len(inscripciones), 0)
        contexto['siguientes'] = self.object.estados_siguientes
        return contexto


class CambiarEstadoView(GuiaRequiredMixin, View):
    def post(self, request, pk):
        experiencia = get_object_or_404(Experiencia, pk=pk, creador=request.user)
        try:
            actualizada = cambiar_estado(experiencia.pk, request.user, request.POST.get('estado', ''))
        except RutaError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Estado de la ruta actualizado: {actualizada.get_estado_display()}.')
        return redirect('grupo_detalle', pk=experiencia.pk)


class RegistrarVisitantesView(GuiaRequiredMixin, TemplateView):
    template_name = 'experiencias/visitantes_registro.html'

    def get_experiencia(self):
        return get_object_or_404(
            Experiencia.objects.select_related('categoria'),
            pk=self.kwargs['pk'],
            creador=self.request.user,
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        experiencia = self.get_experiencia()
        contexto['experiencia'] = experiencia
        contexto['inscripciones'] = experiencia.inscripciones.select_related('usuario')
        return contexto

    def post(self, request, *args, **kwargs):
        experiencia = self.get_experiencia()
        try:
            ids = [int(valor) for valor in request.POST.getlist('asistieron')]
        except ValueError:
            messages.error(request, 'La lista de visitantes no es valida.')
            return redirect('registrar_visitantes', pk=experiencia.pk)
        try:
            total = registrar_asistencia(experiencia.pk, request.user, ids)
        except RutaError as error:
            messages.error(request, str(error))
            return redirect('grupo_detalle', pk=experiencia.pk)
        messages.success(request, f'Asistencia registrada: {total} visitante(s) presente(s).')
        return redirect('grupo_detalle', pk=experiencia.pk)
