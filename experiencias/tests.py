from datetime import timedelta

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .models import Categoria, Experiencia, Inscripcion
from .services import ReservaError, crear_reserva


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BaseTest(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user('admin1', password='clave12345', rol='admin')
        self.guia1 = Usuario.objects.create_user('guia1', password='clave12345', rol='guia')
        self.guia2 = Usuario.objects.create_user('guia2', password='clave12345', rol='guia')
        self.turista1 = Usuario.objects.create_user('turista1', password='clave12345', rol='turista')
        self.turista2 = Usuario.objects.create_user('turista2', password='clave12345', rol='turista')
        self.categoria = Categoria.objects.create(nombre='Trekking')
        self.fecha = timezone.now() + timedelta(days=5)
        self.exp1 = Experiencia.objects.create(
            titulo='Ruta uno', descripcion='d', precio=1000, cupo_maximo=2,
            fecha_hora=self.fecha, categoria=self.categoria, creador=self.guia1,
        )
        self.exp2 = Experiencia.objects.create(
            titulo='Ruta dos', descripcion='d', precio=2000, cupo_maximo=5,
            fecha_hora=self.fecha, categoria=self.categoria, creador=self.guia2,
        )

    def ingresar(self, usuario):
        self.client.login(username=usuario.username, password='clave12345')

    def datos_experiencia(self, experiencia, **cambios):
        datos = {
            'titulo': experiencia.titulo,
            'descripcion': experiencia.descripcion,
            'precio': experiencia.precio,
            'cupo_maximo': experiencia.cupo_maximo,
            'fecha_hora': timezone.localtime(experiencia.fecha_hora).strftime('%Y-%m-%dT%H:%M'),
            'categoria': experiencia.categoria_id,
            'activa': 'on',
        }
        datos.update(cambios)
        return datos

    def pasar_a_pasado(self, experiencia):
        Experiencia.objects.filter(pk=experiencia.pk).update(
            fecha_hora=timezone.now() - timedelta(days=2)
        )
        experiencia.refresh_from_db()


class PermisosTest(BaseTest):
    def test_anonimo_es_redirigido_al_login(self):
        respuesta = self.client.get(reverse('experiencia_lista'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_turista_no_accede_a_categorias(self):
        self.ingresar(self.turista1)
        self.assertEqual(self.client.get(reverse('categoria_lista')).status_code, 403)

    def test_guia_no_accede_a_categorias_ni_usuarios(self):
        self.ingresar(self.guia1)
        self.assertEqual(self.client.get(reverse('categoria_lista')).status_code, 403)
        self.assertEqual(self.client.get(reverse('usuario_lista')).status_code, 403)

    def test_admin_ve_todas_las_experiencias(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('experiencia_lista'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['experiencias']), 2)

    def test_guia_ve_solo_sus_experiencias(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('experiencia_lista'))
        self.assertEqual(list(respuesta.context['experiencias']), [self.exp1])

    def test_guia_no_puede_editar_experiencia_ajena(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('experiencia_actualizar', args=[self.exp2.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_guia_no_puede_eliminar(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Experiencia.objects.filter(pk=self.exp1.pk).exists())

    def test_guia_no_ve_boton_eliminar(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('experiencia_lista'))
        self.assertNotContains(respuesta, reverse('experiencia_borrar', args=[self.exp1.pk]))

    def test_admin_puede_eliminar(self):
        self.ingresar(self.admin)
        self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertFalse(Experiencia.objects.filter(pk=self.exp1.pk).exists())

    def test_guia_crea_experiencia_con_su_autoria(self):
        self.ingresar(self.guia1)
        self.client.post(reverse('experiencia_crear'), {
            'titulo': 'Nueva ruta',
            'descripcion': 'Descripcion',
            'precio': 3000,
            'cupo_maximo': 4,
            'fecha_hora': '2030-01-10T10:00',
            'categoria': self.categoria.pk,
            'activa': 'on',
        })
        nueva = Experiencia.objects.get(titulo='Nueva ruta')
        self.assertEqual(nueva.creador, self.guia1)

    def test_guia_ve_solo_reservas_de_sus_experiencias(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp2)
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('inscripcion_lista'))
        self.assertEqual(len(respuesta.context['inscripciones']), 1)

    def test_superusuario_queda_con_rol_admin(self):
        superusuario = Usuario.objects.create_superuser('super1', password='clave12345')
        self.assertEqual(superusuario.rol, 'admin')


class ReservasTest(BaseTest):
    def test_turista_reserva_con_pago_pendiente(self):
        self.ingresar(self.turista1)
        self.client.post(reverse('reservar', args=[self.exp1.pk]))
        reserva = Inscripcion.objects.get(usuario=self.turista1, experiencia=self.exp1)
        self.assertEqual(reserva.estado_pago, 'pendiente')

    def test_no_se_duplica_la_reserva(self):
        self.ingresar(self.turista1)
        self.client.post(reverse('reservar', args=[self.exp1.pk]))
        self.client.post(reverse('reservar', args=[self.exp1.pk]))
        self.assertEqual(Inscripcion.objects.filter(usuario=self.turista1).count(), 1)

    def test_no_se_reserva_sin_cupos(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp1)
        otro = Usuario.objects.create_user('turista3', password='clave12345', rol='turista')
        self.client.login(username='turista3', password='clave12345')
        self.client.post(reverse('reservar', args=[self.exp1.pk]))
        self.assertFalse(Inscripcion.objects.filter(usuario=otro).exists())

    def test_guia_no_puede_reservar(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('reservar', args=[self.exp2.pk]))
        self.assertEqual(respuesta.status_code, 403)

    def test_turista_ve_solo_sus_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp2)
        self.ingresar(self.turista1)
        respuesta = self.client.get(reverse('mis_reservas'))
        self.assertEqual(len(respuesta.context['reservas']), 1)


class CuposTest(BaseTest):
    def test_ultima_plaza_la_toma_solo_un_turista(self):
        Experiencia.objects.filter(pk=self.exp1.pk).update(cupo_maximo=1)
        crear_reserva(self.turista1, self.exp1.pk)
        with self.assertRaises(ReservaError):
            crear_reserva(self.turista2, self.exp1.pk)
        self.assertEqual(Inscripcion.objects.filter(experiencia=self.exp1).count(), 1)

    def test_servicio_rechaza_doble_reserva_del_mismo_turista(self):
        crear_reserva(self.turista1, self.exp1.pk)
        with self.assertRaises(ReservaError):
            crear_reserva(self.turista1, self.exp1.pk)
        self.assertEqual(Inscripcion.objects.filter(usuario=self.turista1).count(), 1)

    def test_admin_no_mueve_reserva_a_experiencia_llena(self):
        Experiencia.objects.filter(pk=self.exp1.pk).update(cupo_maximo=1)
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        reserva = Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp2)
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('inscripcion_actualizar', args=[reserva.pk]), {
            'usuario': self.turista2.pk,
            'experiencia': self.exp1.pk,
            'estado_pago': 'pendiente',
        })
        self.assertEqual(respuesta.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.experiencia, self.exp2)

    def test_admin_no_crea_reserva_en_experiencia_llena(self):
        Experiencia.objects.filter(pk=self.exp1.pk).update(cupo_maximo=1)
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('inscripcion_crear'), {
            'usuario': self.turista2.pk,
            'experiencia': self.exp1.pk,
            'estado_pago': 'pendiente',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Inscripcion.objects.filter(experiencia=self.exp1).count(), 1)

    def test_admin_cambia_estado_de_pago_en_experiencia_llena(self):
        Experiencia.objects.filter(pk=self.exp1.pk).update(cupo_maximo=1)
        reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        self.client.post(reverse('inscripcion_actualizar', args=[reserva.pk]), {
            'usuario': self.turista1.pk,
            'experiencia': self.exp1.pk,
            'estado_pago': 'confirmado',
        })
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_pago, 'confirmado')

    def test_no_se_reduce_el_cupo_bajo_las_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp1)
        self.ingresar(self.guia1)
        respuesta = self.client.post(
            reverse('experiencia_actualizar', args=[self.exp1.pk]),
            self.datos_experiencia(self.exp1, cupo_maximo=1),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.cupo_maximo, 2)

    def test_se_puede_reducir_el_cupo_hasta_las_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.guia1)
        self.client.post(
            reverse('experiencia_actualizar', args=[self.exp1.pk]),
            self.datos_experiencia(self.exp1, cupo_maximo=1),
        )
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.cupo_maximo, 1)


class FechasTest(BaseTest):
    def test_turista_no_reserva_experiencia_pasada(self):
        self.pasar_a_pasado(self.exp1)
        self.ingresar(self.turista1)
        self.client.post(reverse('reservar', args=[self.exp1.pk]))
        self.assertFalse(Inscripcion.objects.filter(usuario=self.turista1).exists())

    def test_admin_no_crea_reserva_en_experiencia_pasada(self):
        self.pasar_a_pasado(self.exp1)
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('inscripcion_crear'), {
            'usuario': self.turista1.pk,
            'experiencia': self.exp1.pk,
            'estado_pago': 'pendiente',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Inscripcion.objects.filter(usuario=self.turista1).exists())

    def test_no_se_crea_experiencia_con_fecha_pasada(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('experiencia_crear'), {
            'titulo': 'Ruta vieja',
            'descripcion': 'Descripcion',
            'precio': 3000,
            'cupo_maximo': 4,
            'fecha_hora': '2020-01-10T10:00',
            'categoria': self.categoria.pk,
            'activa': 'on',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Experiencia.objects.filter(titulo='Ruta vieja').exists())

    def test_no_se_edita_a_una_fecha_pasada(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(
            reverse('experiencia_actualizar', args=[self.exp1.pk]),
            self.datos_experiencia(self.exp1, fecha_hora='2020-01-10T10:00'),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.exp1.refresh_from_db()
        self.assertGreater(self.exp1.fecha_hora, timezone.now())

    def test_se_edita_experiencia_pasada_sin_tocar_la_fecha(self):
        self.pasar_a_pasado(self.exp1)
        self.ingresar(self.guia1)
        self.client.post(
            reverse('experiencia_actualizar', args=[self.exp1.pk]),
            self.datos_experiencia(self.exp1, titulo='Ruta uno editada'),
        )
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.titulo, 'Ruta uno editada')

    def test_catalogo_oculta_experiencias_pasadas(self):
        self.pasar_a_pasado(self.exp1)
        respuesta = self.client.get(reverse('catalogo'))
        self.assertEqual(list(respuesta.context['experiencias']), [self.exp2])

    def test_detalle_de_experiencia_pasada_no_ofrece_reserva(self):
        self.pasar_a_pasado(self.exp1)
        self.ingresar(self.turista1)
        respuesta = self.client.get(reverse('experiencia_detalle', args=[self.exp1.pk]))
        self.assertNotContains(respuesta, reverse('reservar', args=[self.exp1.pk]))


class CategoriasInactivasTest(BaseTest):
    def test_se_edita_experiencia_con_categoria_inactiva(self):
        self.categoria.activo = False
        self.categoria.save()
        self.ingresar(self.guia1)
        respuesta = self.client.post(
            reverse('experiencia_actualizar', args=[self.exp1.pk]),
            self.datos_experiencia(self.exp1, titulo='Ruta uno editada'),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.titulo, 'Ruta uno editada')
        self.assertEqual(self.exp1.categoria, self.categoria)

    def test_en_creacion_solo_se_ofrecen_categorias_activas(self):
        inactiva = Categoria.objects.create(nombre='Cerrada', activo=False)
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('experiencia_crear'))
        opciones = list(respuesta.context['form'].fields['categoria'].queryset)
        self.assertIn(self.categoria, opciones)
        self.assertNotIn(inactiva, opciones)


class PasswordPanelTest(BaseTest):
    def datos_usuario(self, clave):
        return {
            'username': 'nuevo_guia',
            'first_name': 'Nuevo',
            'last_name': 'Guia',
            'email': 'nuevo@correo.cl',
            'telefono': '',
            'rol': 'guia',
            'is_active': 'on',
            'password1': clave,
            'password2': clave,
        }

    def test_se_rechaza_contrasena_debil(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('usuario_crear'), self.datos_usuario('12345678'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username='nuevo_guia').exists())

    def test_se_acepta_contrasena_segura(self):
        self.ingresar(self.admin)
        self.client.post(reverse('usuario_crear'), self.datos_usuario('ClaveSegura2025'))
        self.assertEqual(Usuario.objects.get(username='nuevo_guia').rol, 'guia')

    def test_editar_sin_contrasena_no_la_cambia(self):
        self.ingresar(self.admin)
        clave_anterior = self.turista1.password
        self.client.post(reverse('usuario_actualizar', args=[self.turista1.pk]), {
            'username': 'turista1',
            'first_name': 'Cambiado',
            'last_name': 'Turista',
            'email': 'turista1@correo.cl',
            'telefono': '',
            'rol': 'turista',
            'is_active': 'on',
            'password1': '',
            'password2': '',
        })
        self.turista1.refresh_from_db()
        self.assertEqual(self.turista1.first_name, 'Cambiado')
        self.assertEqual(self.turista1.password, clave_anterior)


class ConsultasTest(BaseTest):
    def crear_experiencias(self, cantidad):
        for indice in range(cantidad):
            experiencia = Experiencia.objects.create(
                titulo=f'Extra {indice}', descripcion='d', precio=500, cupo_maximo=5,
                fecha_hora=self.fecha, categoria=self.categoria, creador=self.guia1,
            )
            Inscripcion.objects.create(usuario=self.turista1, experiencia=experiencia)

    def consultas_del_catalogo(self):
        with CaptureQueriesContext(connection) as contexto:
            self.client.get(reverse('catalogo'))
        return len(contexto)

    def test_el_catalogo_no_crece_en_consultas_con_mas_experiencias(self):
        self.crear_experiencias(2)
        pocas = self.consultas_del_catalogo()
        self.crear_experiencias(6)
        muchas = self.consultas_del_catalogo()
        self.assertEqual(pocas, muchas)

    def test_conteo_de_cupos_con_cero_una_y_varias_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp2)
        Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp2)
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        respuesta = self.client.get(reverse('catalogo'))
        ocupados = {e.pk: e.cupos_ocupados for e in respuesta.context['experiencias']}
        self.assertEqual(ocupados, {self.exp1.pk: 1, self.exp2.pk: 2})
        nueva = Experiencia.objects.create(
            titulo='Sin reservas', descripcion='d', precio=1, cupo_maximo=3,
            fecha_hora=self.fecha, categoria=self.categoria, creador=self.guia1,
        )
        respuesta = self.client.get(reverse('catalogo'))
        ocupados = {e.pk: e.cupos_ocupados for e in respuesta.context['experiencias']}
        self.assertEqual(ocupados[nueva.pk], 0)

    def test_el_panel_muestra_los_cupos_anotados(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('experiencia_lista'))
        ocupados = {e.pk: e.cupos_ocupados for e in respuesta.context['experiencias']}
        self.assertEqual(ocupados, {self.exp1.pk: 1, self.exp2.pk: 0})


class SesionYRegistroTest(BaseTest):
    def test_catalogo_es_publico(self):
        self.assertEqual(self.client.get(reverse('catalogo')).status_code, 200)

    def test_sesion_guarda_experiencias_vistas(self):
        self.client.get(reverse('experiencia_detalle', args=[self.exp1.pk]))
        self.client.get(reverse('experiencia_detalle', args=[self.exp2.pk]))
        respuesta = self.client.get(reverse('catalogo'))
        self.assertEqual(
            [e.pk for e in respuesta.context['ultimas_vistas']], [self.exp2.pk, self.exp1.pk]
        )

    def test_experiencia_inactiva_no_aparece_en_catalogo(self):
        self.exp1.activa = False
        self.exp1.save()
        respuesta = self.client.get(reverse('catalogo'))
        self.assertEqual(list(respuesta.context['experiencias']), [self.exp2])

    def test_registro_crea_turista(self):
        self.client.post(reverse('registro'), {
            'username': 'nuevo',
            'first_name': 'Nuevo',
            'last_name': 'Turista',
            'email': 'nuevo@correo.cl',
            'password1': 'ClaveSegura2025',
            'password2': 'ClaveSegura2025',
        })
        self.assertEqual(Usuario.objects.get(username='nuevo').rol, 'turista')

    def test_login_redirige_al_panel(self):
        respuesta = self.client.post(reverse('login'), {'username': 'guia1', 'password': 'clave12345'})
        self.assertRedirects(respuesta, reverse('panel'))
