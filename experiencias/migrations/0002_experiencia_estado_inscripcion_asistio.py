
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiencias', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiencia',
            name='estado',
            field=models.CharField(choices=[('programada', 'Programada'), ('en_curso', 'En curso'), ('finalizada', 'Finalizada'), ('suspendida', 'Suspendida')], default='programada', max_length=15),
        ),
        migrations.AddField(
            model_name='inscripcion',
            name='asistio',
            field=models.BooleanField(default=False),
        ),
    ]
