import io
import re
from datetime import timedelta
from smtplib import SMTPAuthenticationError, SMTPException
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from experiencias.models import Categoria, Experiencia, Inscripcion

from .models import Usuario
from .views import MENSAJE_SIN_CUENTA


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BaseCuentasTest(TestCase):
    clave = 'clave12345'

    def crear(self, username, rol, **extra):
        return Usuario.objects.create_user(
            username, email=f'{username}@correo.cl', password=self.clave, rol=rol, **extra
        )

    def setUp(self):
        self.admin = self.crear('admin1', 'admin')
        self.guia = self.crear('guia1', 'guia')
        self.turista = self.crear('turista1', 'turista')
        self.otro_turista = self.crear('turista2', 'turista')
        categoria = Categoria.objects.create(nombre='Trekking')
        self.exp = Experiencia.objects.create(
            titulo='Ruta uno', descripcion='d', precio=1000, cupo_maximo=5,
            fecha_hora=timezone.now() + timedelta(days=5), categoria=categoria, creador=self.guia,
        )

    def ingresar(self, usuario):
        self.client.login(username=usuario.username, password=self.clave)


class EliminarCuentaTest(BaseCuentasTest):
    def eliminar(self, clave=None):
        return self.client.post(reverse('eliminar_cuenta'), {'password': self.clave if clave is None else clave})

    def test_turista_elimina_su_cuenta_y_sus_reservas(self):
        Inscripcion.objects.create(usuario=self.turista, experiencia=self.exp)
        self.ingresar(self.turista)
        respuesta = self.eliminar()
        self.assertRedirects(respuesta, reverse('inicio'))
        self.assertFalse(Usuario.objects.filter(pk=self.turista.pk).exists())
        self.assertFalse(Inscripcion.objects.filter(experiencia=self.exp).exists())

    def test_la_sesion_se_cierra_al_eliminar(self):
        self.ingresar(self.turista)
        self.eliminar()
        respuesta = self.client.get(reverse('panel'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_se_muestra_el_mensaje_de_confirmacion(self):
        self.ingresar(self.turista)
        respuesta = self.client.post(reverse('eliminar_cuenta'), {'password': self.clave}, follow=True)
        self.assertContains(respuesta, 'Tu cuenta fue eliminada correctamente.')

    def test_con_clave_incorrecta_no_se_elimina(self):
        self.ingresar(self.turista)
        respuesta = self.eliminar('otra_clave')
        self.assertRedirects(respuesta, reverse('perfil'))
        self.assertTrue(Usuario.objects.filter(pk=self.turista.pk).exists())

    def test_sin_clave_no_se_elimina(self):
        self.ingresar(self.turista)
        respuesta = self.client.post(reverse('eliminar_cuenta'), {})
        self.assertRedirects(respuesta, reverse('perfil'))
        self.assertTrue(Usuario.objects.filter(pk=self.turista.pk).exists())

    def test_el_superusuario_no_puede_eliminar_su_cuenta(self):
        superusuario = Usuario.objects.create_superuser('super1', password=self.clave)
        self.ingresar(superusuario)
        self.eliminar()
        self.assertTrue(Usuario.objects.filter(pk=superusuario.pk).exists())

    def test_el_unico_administrador_no_puede_eliminarse(self):
        self.ingresar(self.admin)
        self.eliminar()
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_un_administrador_puede_eliminarse_si_hay_otro(self):
        self.crear('admin2', 'admin')
        self.ingresar(self.admin)
        self.eliminar()
        self.assertFalse(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_un_guia_con_tours_no_puede_eliminar_su_cuenta(self):
        Inscripcion.objects.create(usuario=self.turista, experiencia=self.exp)
        self.ingresar(self.guia)
        respuesta = self.client.post(reverse('eliminar_cuenta'), {'password': self.clave}, follow=True)
        self.assertContains(respuesta, 'Tu cuenta tiene tours creados')
        self.assertTrue(Usuario.objects.filter(pk=self.guia.pk).exists())
        self.assertTrue(Experiencia.objects.filter(pk=self.exp.pk).exists())
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_un_guia_sin_tours_si_puede_eliminar_su_cuenta(self):
        otro_guia = self.crear('guia_sin_tours', 'guia')
        self.ingresar(otro_guia)
        self.eliminar()
        self.assertFalse(Usuario.objects.filter(pk=otro_guia.pk).exists())

    def test_al_eliminar_su_cuenta_el_turista_conserva_las_reservas_de_otros(self):
        Inscripcion.objects.create(usuario=self.turista, experiencia=self.exp)
        Inscripcion.objects.create(usuario=self.otro_turista, experiencia=self.exp)
        self.ingresar(self.turista)
        self.eliminar()
        self.assertEqual(list(Inscripcion.objects.values_list('usuario__username', flat=True)), ['turista2'])
        self.assertTrue(Experiencia.objects.filter(pk=self.exp.pk).exists())

    def test_no_se_pueden_eliminar_cuentas_ajenas(self):
        self.ingresar(self.turista)
        self.eliminar()
        self.assertTrue(Usuario.objects.filter(pk=self.otro_turista.pk).exists())

    def test_anonimo_es_redirigido_al_login(self):
        respuesta = self.eliminar()
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_eliminar_requiere_post(self):
        self.ingresar(self.turista)
        self.assertEqual(self.client.get(reverse('eliminar_cuenta')).status_code, 405)

    def test_el_perfil_muestra_los_dos_modales(self):
        self.ingresar(self.turista)
        respuesta = self.client.get(reverse('perfil'))
        for fragmento in ['id="abrirEliminarCuenta"', 'id="modalEliminarPaso1"', 'id="modalEliminarPaso2"',
                          'id="claveEliminar"', 'id="confirmarEliminacion" disabled']:
            self.assertContains(respuesta, fragmento)

    def test_el_perfil_bloquea_el_boton_al_superusuario(self):
        superusuario = Usuario.objects.create_superuser('super1', password=self.clave)
        self.ingresar(superusuario)
        respuesta = self.client.get(reverse('perfil'))
        self.assertNotContains(respuesta, 'id="modalEliminarPaso2"')
        self.assertContains(respuesta, 'no se pueden eliminar desde la aplicacion')

    def test_el_perfil_avisa_cuantas_reservas_se_eliminaran(self):
        Inscripcion.objects.create(usuario=self.turista, experiencia=self.exp)
        self.ingresar(self.turista)
        respuesta = self.client.get(reverse('perfil'))
        self.assertContains(respuesta, 'Se eliminaran tus 1 reserva ')


class RecuperarClaveTest(BaseCuentasTest):
    nueva = 'ClaveNueva2025x'

    def setUp(self):
        super().setUp()
        cache.clear()

    def recuperar(self, username='turista1', email='turista1@correo.cl', clave=None):
        clave = self.nueva if clave is None else clave
        return self.client.post(reverse('recuperar_clave'), {
            'username': username,
            'email': email,
            'new_password1': clave,
            'new_password2': clave,
        })

    def test_el_login_ofrece_recuperar_la_contrasena(self):
        respuesta = self.client.get(reverse('login'))
        self.assertContains(respuesta, reverse('recuperar_clave'))
        self.assertContains(respuesta, 'Olvidaste tu contraseña?')

    def test_el_formulario_pide_usuario_correo_y_la_clave_nueva(self):
        respuesta = self.client.get(reverse('recuperar_clave'))
        self.assertTemplateUsed(respuesta, 'registration/recuperar_clave.html')
        for campo in ['username', 'email', 'new_password1', 'new_password2']:
            self.assertContains(respuesta, f'name="{campo}"')
        self.assertContains(respuesta, 'class="form-control"')

    def test_con_usuario_y_correo_correctos_se_cambia_la_contrasena(self):
        respuesta = self.recuperar()
        self.assertRedirects(respuesta, reverse('login'))
        self.assertTrue(self.client.login(username='turista1', password=self.nueva))
        self.client.logout()
        self.assertFalse(self.client.login(username='turista1', password=self.clave))

    def test_se_muestra_el_mensaje_de_exito(self):
        respuesta = self.client.post(reverse('recuperar_clave'), {
            'username': 'turista1', 'email': 'turista1@correo.cl',
            'new_password1': self.nueva, 'new_password2': self.nueva,
        }, follow=True)
        self.assertContains(respuesta, 'Tu contraseña fue actualizada.')

    def test_el_correo_no_distingue_mayusculas(self):
        self.recuperar(email='TURISTA1@Correo.CL')
        self.assertTrue(self.client.login(username='turista1', password=self.nueva))

    def test_con_correo_incorrecto_no_se_cambia(self):
        respuesta = self.recuperar(email='otro@correo.cl')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, MENSAJE_SIN_CUENTA)
        self.assertTrue(self.client.login(username='turista1', password=self.clave))

    def test_con_usuario_ajeno_y_correo_propio_no_se_cambia(self):
        self.recuperar(username='turista2', email='turista1@correo.cl')
        self.assertTrue(self.client.login(username='turista2', password=self.clave))

    def test_el_mensaje_es_el_mismo_si_el_usuario_no_existe_o_el_correo_no_coincide(self):
        sin_usuario = self.recuperar(username='fantasma', email='fantasma@correo.cl')
        sin_correo = self.recuperar(email='otro@correo.cl')
        self.assertContains(sin_usuario, MENSAJE_SIN_CUENTA)
        self.assertContains(sin_correo, MENSAJE_SIN_CUENTA)

    def test_se_rechaza_una_contrasena_debil_con_datos_correctos(self):
        respuesta = self.recuperar(clave='12345678')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self.client.login(username='turista1', password=self.clave))

    def test_la_contrasena_debil_se_rechaza_igual_con_datos_falsos(self):
        verdadero = self.recuperar(clave='12345678')
        falso = self.recuperar(username='fantasma', email='fantasma@correo.cl', clave='12345678')
        self.assertEqual(
            verdadero.context['form'].errors.get('new_password1'),
            falso.context['form'].errors.get('new_password1'),
        )
        self.assertNotContains(falso, MENSAJE_SIN_CUENTA)

    def test_las_contrasenas_deben_coincidir(self):
        respuesta = self.client.post(reverse('recuperar_clave'), {
            'username': 'turista1', 'email': 'turista1@correo.cl',
            'new_password1': self.nueva, 'new_password2': 'ClaveDistinta2025x',
        })
        self.assertContains(respuesta, 'Las contraseñas no coinciden.')
        self.assertTrue(self.client.login(username='turista1', password=self.clave))

    def test_los_superusuarios_no_se_pueden_recuperar_por_esta_via(self):
        Usuario.objects.create_superuser('super1', email='super1@correo.cl', password=self.clave)
        respuesta = self.recuperar(username='super1', email='super1@correo.cl')
        self.assertContains(respuesta, MENSAJE_SIN_CUENTA)
        self.assertTrue(self.client.login(username='super1', password=self.clave))

    def test_los_administradores_no_se_pueden_recuperar_por_esta_via(self):
        respuesta = self.recuperar(username='admin1', email='admin1@correo.cl')
        self.assertContains(respuesta, MENSAJE_SIN_CUENTA)
        self.assertTrue(self.client.login(username='admin1', password=self.clave))

    def test_las_cuentas_con_acceso_staff_no_se_pueden_recuperar(self):
        self.crear('personal1', 'guia', is_staff=True)
        respuesta = self.recuperar(username='personal1', email='personal1@correo.cl')
        self.assertContains(respuesta, MENSAJE_SIN_CUENTA)
        self.assertTrue(self.client.login(username='personal1', password=self.clave))

    def test_las_cuentas_inactivas_no_se_pueden_recuperar(self):
        Usuario.objects.filter(pk=self.turista.pk).update(is_active=False)
        respuesta = self.recuperar()
        self.assertContains(respuesta, MENSAJE_SIN_CUENTA)

    def test_tras_cinco_intentos_fallidos_se_bloquea_incluso_con_datos_correctos(self):
        for _ in range(5):
            self.recuperar(email='otro@correo.cl')
        respuesta = self.recuperar()
        self.assertContains(respuesta, 'Demasiados intentos fallidos.')
        self.assertTrue(self.client.login(username='turista1', password=self.clave))

    def test_pasado_el_bloqueo_se_puede_volver_a_intentar(self):
        for _ in range(5):
            self.recuperar(email='otro@correo.cl')
        cache.clear()
        respuesta = self.recuperar()
        self.assertRedirects(respuesta, reverse('login'))

    def test_un_exito_reinicia_el_contador_de_intentos(self):
        for _ in range(3):
            self.recuperar(email='otro@correo.cl')
        self.recuperar()
        self.client.logout()
        for _ in range(4):
            respuesta = self.recuperar(email='otro@correo.cl', clave='OtraClave2025x')
            self.assertNotContains(respuesta, 'Demasiados intentos fallidos.')

    def test_los_intentos_fallidos_se_cuentan_por_usuario(self):
        for _ in range(5):
            self.recuperar(username='turista2', email='otro@correo.cl')
        respuesta = self.recuperar(username='turista2', email='turista2@correo.cl')
        self.assertContains(respuesta, 'Demasiados intentos fallidos.')

    def test_las_sesiones_abiertas_se_cierran_al_cambiar_la_contrasena(self):
        otro_cliente = self.client_class()
        otro_cliente.login(username='turista1', password=self.clave)
        self.assertEqual(otro_cliente.get(reverse('panel')).status_code, 200)
        self.recuperar()
        self.assertEqual(otro_cliente.get(reverse('panel')).status_code, 302)

    def test_el_flujo_antiguo_por_enlace_ya_no_existe(self):
        self.assertEqual(self.client.get('/accounts/password_reset/').status_code, 404)
        self.assertEqual(self.client.get('/accounts/reset/MQ/token/').status_code, 404)

    def test_cerrar_sesion_sigue_funcionando(self):
        self.ingresar(self.turista)
        respuesta = self.client.post(reverse('logout'))
        self.assertRedirects(respuesta, reverse('inicio'))


class CorreoLegibleTest(BaseCuentasTest):
    @override_settings(EMAIL_BACKEND='cuentas.correo.ConsolaLegibleBackend')
    def test_un_enlace_largo_se_imprime_completo_y_sin_cortes(self):
        class Salida(io.StringIO):
            encoding = 'utf-8'

        enlace = 'http://dominio-largo-de-prueba.aventuradelsur.example.com/enlace/' + 'a' * 60 + '/'
        salida = Salida()
        with mock.patch('sys.stdout', salida):
            mail.send_mail('Asunto', f'Hola, contraseña nueva: {enlace}', None, ['turista1@correo.cl'])
        texto = salida.getvalue()
        self.assertIn(enlace, texto)
        self.assertNotIn('=\n', texto)
        self.assertIn('Para: turista1@correo.cl', texto)

    def test_los_modales_comparten_la_funcion_que_evita_el_atasco(self):
        self.ingresar(self.turista)
        base = self.client.get(reverse('perfil'))
        self.assertContains(base, 'function encadenarModales')
        self.assertContains(base, "encadenarModales('#modalEliminarPaso1', '#modalEliminarPaso2')")
        Inscripcion.objects.create(usuario=self.turista, experiencia=self.exp)
        reservas = self.client.get(reverse('mis_reservas'))
        self.assertContains(reservas, "encadenarModales('#modalCancelarPaso1', '#modalCancelarPaso2')")


class EnvioDeCorreoTest(BaseCuentasTest):
    def test_el_comando_de_prueba_envia_el_correo(self):
        salida = io.StringIO()
        call_command('probar_correo', 'destino@correo.cl', stdout=salida)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['destino@correo.cl'])
        self.assertIn('Correo enviado a destino@correo.cl', salida.getvalue())

    def test_el_comando_explica_el_rechazo_de_credenciales(self):
        error = SMTPAuthenticationError(535, b'credenciales invalidas')
        with mock.patch('cuentas.management.commands.probar_correo.send_mail', side_effect=error):
            with self.assertRaisesMessage(CommandError, 'clave de aplicacion'):
                call_command('probar_correo', 'destino@correo.cl')

    def test_el_comando_informa_los_fallos_de_conexion(self):
        with mock.patch('cuentas.management.commands.probar_correo.send_mail', side_effect=ConnectionRefusedError('rechazada')):
            with self.assertRaisesMessage(CommandError, 'No se pudo enviar el correo'):
                call_command('probar_correo', 'destino@correo.cl')

    @override_settings(EMAIL_BACKEND='cuentas.correo.ConsolaLegibleBackend')
    def test_el_comando_avisa_si_el_envio_real_no_esta_configurado(self):
        salida = io.StringIO()
        with mock.patch('sys.stdout', salida):
            call_command('probar_correo', 'destino@correo.cl', stdout=salida)
        self.assertIn('El envio real no esta configurado', salida.getvalue())
