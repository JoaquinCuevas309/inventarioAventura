from django import forms
from django.db.models import Q
from django.utils import timezone

from cuentas.forms import BootstrapMixin
from cuentas.models import Usuario

from .models import Categoria, Experiencia, Inscripcion


class CategoriaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'activo']
        labels = {'nombre': 'Nombre', 'descripcion': 'Descripcion', 'activo': 'Categoria activa'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class ExperienciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Experiencia
        fields = ['titulo', 'descripcion', 'precio', 'cupo_maximo', 'fecha_hora', 'categoria', 'activa']
        labels = {
            'titulo': 'Titulo',
            'descripcion': 'Descripcion',
            'precio': 'Precio (CLP)',
            'cupo_maximo': 'Cupo maximo',
            'fecha_hora': 'Fecha y hora de realizacion',
            'categoria': 'Categoria',
            'activa': 'Experiencia activa',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'fecha_hora': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        condicion = Q(activo=True)
        if self.instance.pk:
            condicion |= Q(pk=self.instance.categoria_id)
        self.fields['categoria'].queryset = Categoria.objects.filter(condicion)
        self.fields['categoria'].empty_label = 'Seleccione una categoria'

    def clean_fecha_hora(self):
        fecha = self.cleaned_data['fecha_hora']
        if self.instance.pk:
            original = self.instance.fecha_hora
            sin_cambio = fecha.replace(second=0, microsecond=0) == original.replace(
                second=0, microsecond=0
            )
            if sin_cambio:
                return fecha
        if fecha <= timezone.now():
            raise forms.ValidationError('La fecha y hora deben ser posteriores al momento actual.')
        return fecha


class InscripcionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['usuario', 'experiencia', 'estado_pago']
        labels = {'usuario': 'Turista', 'experiencia': 'Experiencia', 'estado_pago': 'Estado de pago'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = Usuario.objects.filter(rol='turista')
        self.fields['usuario'].empty_label = 'Seleccione un turista'
        self.fields['experiencia'].empty_label = 'Seleccione una experiencia'

    def clean_experiencia(self):
        experiencia = self.cleaned_data['experiencia']
        cambio_experiencia = not self.instance.pk or 'experiencia' in self.changed_data
        if cambio_experiencia and experiencia.ya_realizada:
            raise forms.ValidationError('La experiencia ya se realizo y no admite reservas.')
        return experiencia
