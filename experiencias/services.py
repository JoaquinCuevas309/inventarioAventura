from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Experiencia, Inscripcion


class ReservaError(Exception):
    pass


def bloquear_experiencia(experiencia_pk):
    try:
        return Experiencia.objects.select_for_update().get(pk=experiencia_pk)
    except Experiencia.DoesNotExist:
        raise ReservaError('La experiencia no existe.')


def validar_experiencia_reservable(experiencia):
    if not experiencia.activa or not experiencia.categoria.activo:
        raise ReservaError('La experiencia no esta disponible.')
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
