from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cuentas.models import Usuario
from experiencias.models import Categoria, Experiencia, Inscripcion

CLAVE_PRUEBA = 'Aventura2025!'

CATEGORIAS = [
    ('Trekking', 'Rutas de caminata guiadas por senderos del ecoparque.'),
    ('Canopy', 'Circuitos de tirolesas entre los arboles nativos.'),
    ('Arriendo de equipos', 'Arriendo de equipo tecnico para actividades al aire libre.'),
    ('Kayak', 'Recorridos en kayak por el lago y el rio.'),
]

GUIAS = [
    ('guia_marcela', 'Marcela', 'Rojas'),
    ('guia_tomas', 'Tomas', 'Vidal'),
]

TURISTAS = [
    ('turista_ana', 'Ana', 'Soto'),
    ('turista_luis', 'Luis', 'Pino'),
]

EXPERIENCIAS = [
    ('Trekking Sendero del Bosque Nativo', 'Trekking', 15, 12000),
    ('Trekking Cumbre del Mirador', 'Trekking', 10, 18000),
    ('Canopy Circuito Alto', 'Canopy', 8, 25000),
    ('Arriendo de Equipo Completo de Montaña', 'Arriendo de equipos', 20, 9000),
    ('Kayak Laguna Esmeralda', 'Kayak', 12, 20000),
    ('Kayak Rio Sereno al Atardecer', 'Kayak', 10, 22000),
    ('Canopy Circuito Infantil', 'Canopy', 12, 15000),
    ('Trekking Nocturno de Fauna', 'Trekking', 8, 16000),
]


class Command(BaseCommand):
    help = 'Crea usuarios, categorias, experiencias y reservas de prueba'

    def handle(self, *args, **options):
        admin, creado = Usuario.objects.get_or_create(
            username='admin_aventura',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Aventura',
                'email': 'admin@aventuradelsur.cl',
                'rol': 'admin',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if creado:
            admin.set_password(CLAVE_PRUEBA)
            admin.save()

        guias = []
        for username, nombre, apellido in GUIAS:
            guia, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'email': f'{username}@aventuradelsur.cl',
                    'rol': 'guia',
                },
            )
            if creado:
                guia.set_password(CLAVE_PRUEBA)
                guia.save()
            guias.append(guia)

        turistas = []
        for username, nombre, apellido in TURISTAS:
            turista, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'email': f'{username}@correo.cl',
                    'rol': 'turista',
                },
            )
            if creado:
                turista.set_password(CLAVE_PRUEBA)
                turista.save()
            turistas.append(turista)

        categorias = {}
        for nombre, descripcion in CATEGORIAS:
            categoria, _ = Categoria.objects.get_or_create(
                nombre=nombre, defaults={'descripcion': descripcion}
            )
            categorias[nombre] = categoria

        ahora = timezone.now()
        experiencias = []
        for indice, (titulo, categoria, cupo, precio) in enumerate(EXPERIENCIAS):
            fecha = ahora + timedelta(days=90 + indice)
            experiencia, creada = Experiencia.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'descripcion': f'{titulo}. Actividad guiada con equipo de seguridad incluido.',
                    'precio': precio,
                    'cupo_maximo': cupo,
                    'fecha_hora': fecha,
                    'categoria': categorias[categoria],
                    'creador': guias[0 if indice < 4 else 1],
                },
            )
            if not creada and experiencia.fecha_hora <= ahora:
                experiencia.fecha_hora = fecha
                experiencia.save(update_fields=['fecha_hora'])
            experiencias.append(experiencia)

        for numero, turista in enumerate(turistas):
            for desplazamiento in range(3):
                experiencia = experiencias[(numero * 3 + desplazamiento) % len(experiencias)]
                Inscripcion.objects.get_or_create(
                    usuario=turista,
                    experiencia=experiencia,
                    defaults={'estado_pago': 'confirmado' if desplazamiento == 0 else 'pendiente'},
                )

        self.stdout.write(self.style.SUCCESS('Datos de prueba creados correctamente.'))
        self.stdout.write(f'Clave de prueba para todos los usuarios: {CLAVE_PRUEBA}')
