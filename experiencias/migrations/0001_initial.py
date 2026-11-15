
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('descripcion', models.TextField(blank=True)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Experiencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=150)),
                ('descripcion', models.TextField()),
                ('precio', models.PositiveIntegerField()),
                ('cupo_maximo', models.PositiveIntegerField()),
                ('fecha_hora', models.DateTimeField()),
                ('activa', models.BooleanField(default=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiencias', to='experiencias.categoria')),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiencias_creadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Experiencia',
                'verbose_name_plural': 'Experiencias',
                'ordering': ['fecha_hora'],
            },
        ),
        migrations.CreateModel(
            name='Inscripcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inscripcion', models.DateTimeField(auto_now_add=True)),
                ('estado_pago', models.CharField(choices=[('pendiente', 'Pendiente'), ('confirmado', 'Confirmado')], default='pendiente', max_length=20)),
                ('experiencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inscripciones', to='experiencias.experiencia')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inscripciones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Inscripcion',
                'verbose_name_plural': 'Inscripciones',
                'ordering': ['-fecha_inscripcion'],
                'unique_together': {('usuario', 'experiencia')},
            },
        ),
    ]
