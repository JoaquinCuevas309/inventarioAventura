from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nombre


class ExperienciaQuerySet(models.QuerySet):
    def con_inscritos(self):
        return self.annotate(total_inscritos=Count('inscripciones'))

    def disponibles(self):
        return self.filter(
            activa=True,
            categoria__activo=True,
            estado='programada',
            fecha_hora__gt=timezone.now(),
        )


class Experiencia(models.Model):
    ESTADOS_CHOICES = (
        ('programada', 'Programada'),
        ('en_curso', 'En curso'),
        ('finalizada', 'Finalizada'),
        ('suspendida', 'Suspendida'),
    )
    HORAS_PREVIAS_PARA_INICIAR = 1

    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    precio = models.PositiveIntegerField()
    cupo_maximo = models.PositiveIntegerField()
    fecha_hora = models.DateTimeField()
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='experiencias')
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='experiencias_creadas'
    )
    activa = models.BooleanField(default=True)
    estado = models.CharField(max_length=15, choices=ESTADOS_CHOICES, default='programada')

    objects = ExperienciaQuerySet.as_manager()

    class Meta:
        ordering = ['fecha_hora']
        verbose_name = 'Experiencia'
        verbose_name_plural = 'Experiencias'

    @property
    def cupos_ocupados(self):
        if hasattr(self, 'total_inscritos'):
            return self.total_inscritos
        return self.inscripciones.count()

    @property
    def cupos_disponibles(self):
        return max(self.cupo_maximo - self.cupos_ocupados, 0)

    @property
    def ya_realizada(self):
        return self.fecha_hora <= timezone.now()

    @property
    def puede_iniciarse(self):
        anticipacion = timedelta(hours=self.HORAS_PREVIAS_PARA_INICIAR)
        return self.fecha_hora - anticipacion <= timezone.now()

    @property
    def estados_siguientes(self):
        if self.estado == 'programada':
            siguientes = ['en_curso', 'suspendida', 'finalizada'] if self.puede_iniciarse else ['suspendida']
        elif self.estado == 'en_curso':
            siguientes = ['finalizada', 'suspendida']
        elif self.estado == 'suspendida':
            siguientes = ['programada']
        else:
            siguientes = []
        return [(valor, etiqueta) for valor, etiqueta in self.ESTADOS_CHOICES if valor in siguientes]

    @property
    def admite_registro_de_visitantes(self):
        return self.estado in ('en_curso', 'finalizada')

    def __str__(self):
        return self.titulo


class Inscripcion(models.Model):
    ESTADOS_PAGO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inscripciones'
    )
    experiencia = models.ForeignKey(Experiencia, on_delete=models.PROTECT, related_name='inscripciones')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO_CHOICES, default='pendiente')
    asistio = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_inscripcion']
        unique_together = ('usuario', 'experiencia')
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'

    def __str__(self):
        return f"{self.usuario.username} - {self.experiencia.titulo}"
