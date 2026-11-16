from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Experiencia, Inscripcion


class ReservaError(Exception):
    pass


class RutaError(Exception):
    pass


def bloquear_experiencia(experiencia_pk):
    try:
        return Experiencia.objects.select_for_update().get(pk=experiencia_pk)
    except Experiencia.DoesNotExist:
        raise ReservaError('La experiencia no existe.')


def validar_experiencia_reservable(experiencia):
    if not experiencia.activa or not experiencia.categoria.activo:
        raise ReservaError('La experiencia no esta disponible.')
    if experiencia.estado != 'programada':
        raise ReservaError(f'La ruta esta {experiencia.get_estado_display().lower()} y no admite reservas.')
    if experiencia.fecha_hora <= timezone.now():
        raise ReservaError('La experiencia ya se realizo y no admite reservas.')


def validar_cupo(experiencia, excluir_pk=None):
    inscripciones = experiencia.inscripciones.all()
    if excluir_pk:
        inscripciones = inscripciones.exclude(pk=excluir_pk)
    if inscripciones.count() >= experiencia.cupo_maximo:
        raise ReservaError('La experiencia no tiene cupos disponibles.')


def crear_reserva(usuario, experiencia_pk):
    try:
        with transaction.atomic():
            experiencia = bloquear_experiencia(experiencia_pk)
            validar_experiencia_reservable(experiencia)
            if Inscripcion.objects.filter(usuario=usuario, experiencia=experiencia).exists():
                raise ReservaError('Ya tienes una reserva para esta experiencia.')
            validar_cupo(experiencia)
            return Inscripcion.objects.create(usuario=usuario, experiencia=experiencia)
    except IntegrityError:
        raise ReservaError('Ya tienes una reserva para esta experiencia.')


def bloquear_ruta_del_guia(experiencia_pk, guia):
    experiencia = Experiencia.objects.select_for_update().filter(pk=experiencia_pk, creador=guia).first()
    if experiencia is None:
        raise RutaError('La ruta no existe o no te pertenece.')
    return experiencia


def cambiar_estado(experiencia_pk, guia, nuevo_estado):
    with transaction.atomic():
        experiencia = bloquear_ruta_del_guia(experiencia_pk, guia)
        permitidos = [valor for valor, _ in experiencia.estados_siguientes]
        if nuevo_estado not in permitidos:
            raise RutaError('No se puede cambiar la ruta a ese estado.')
        experiencia.estado = nuevo_estado
        experiencia.save(update_fields=['estado'])
        return experiencia


def registrar_asistencia(experiencia_pk, guia, ids_asistentes):
    with transaction.atomic():
        experiencia = bloquear_ruta_del_guia(experiencia_pk, guia)
        if not experiencia.admite_registro_de_visitantes:
            raise RutaError('Inicia la ruta antes de registrar visitantes.')
        validos = set(experiencia.inscripciones.values_list('pk', flat=True))
        if not set(ids_asistentes) <= validos:
            raise RutaError('Hay visitantes que no pertenecen a esta ruta.')
        experiencia.inscripciones.filter(pk__in=ids_asistentes).update(asistio=True)
        experiencia.inscripciones.exclude(pk__in=ids_asistentes).update(asistio=False)
        return len(ids_asistentes)
