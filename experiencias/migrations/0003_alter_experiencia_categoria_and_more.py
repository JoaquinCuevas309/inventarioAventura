
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiencias', '0002_experiencia_estado_inscripcion_asistio'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiencia',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='experiencias', to='experiencias.categoria'),
        ),
        migrations.AlterField(
            model_name='experiencia',
            name='creador',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='experiencias_creadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='inscripcion',
            name='experiencia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscripciones', to='experiencias.experiencia'),
        ),
        migrations.AlterField(
            model_name='inscripcion',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscripciones', to=settings.AUTH_USER_MODEL),
        ),
    ]
