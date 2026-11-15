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
            activa=True, categoria__activo=True, fecha_hora__gt=timezone.now()
        )


class Experiencia(models.Model):
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    precio = models.PositiveIntegerField()
    cupo_maximo = models.PositiveIntegerField()
    fecha_hora = models.DateTimeField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='experiencias')
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='experiencias_creadas'
    )
    activa = models.BooleanField(default=True)

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

    def __str__(self):
        return self.titulo


class Inscripcion(models.Model):
    ESTADOS_PAGO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscripciones'
    )
    experiencia = models.ForeignKey(Experiencia, on_delete=models.CASCADE, related_name='inscripciones')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO_CHOICES, default='pendiente')

    class Meta:
        ordering = ['-fecha_inscripcion']
        unique_together = ('usuario', 'experiencia')
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'

    def __str__(self):
        return f"{self.usuario.username} - {self.experiencia.titulo}"
