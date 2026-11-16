import os
import tempfile

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from inventarioAventura.settings import (
    CLAVE_SECRETA_DE_DESARROLLO,
    cargar_env,
    elegir_backend_correo,
    elegir_clave_secreta,
    elegir_debug,
    elegir_hosts,
    elegir_remitente,
)


class CargarEnvTest(SimpleTestCase):
    def setUp(self):
        self.claves = ['PRUEBA_ENV_A', 'PRUEBA_ENV_B', 'PRUEBA_ENV_C']
        for clave in self.claves:
            os.environ.pop(clave, None)

    def tearDown(self):
        for clave in self.claves:
            os.environ.pop(clave, None)

    def escribir(self, contenido):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = os.path.join(carpeta.name, '.env')
        with open(ruta, 'w', encoding='utf-8') as archivo:
            archivo.write(contenido)
        return ruta

    def test_lee_las_variables_del_archivo(self):
        ruta = self.escribir('PRUEBA_ENV_A=valor\nPRUEBA_ENV_B="con comillas"\n')
        cargar_env(ruta)
        self.assertEqual(os.environ['PRUEBA_ENV_A'], 'valor')
        self.assertEqual(os.environ['PRUEBA_ENV_B'], 'con comillas')

    def test_ignora_lineas_vacias_y_sin_igual(self):
        ruta = self.escribir('\nlinea sin igual\n#PRUEBA_ENV_A=no\nPRUEBA_ENV_C=a=b\n')
        cargar_env(ruta)
        self.assertNotIn('PRUEBA_ENV_A', os.environ)
        self.assertEqual(os.environ['PRUEBA_ENV_C'], 'a=b')

    def test_no_pisa_variables_de_entorno_existentes(self):
        os.environ['PRUEBA_ENV_A'] = 'desde_el_sistema'
        ruta = self.escribir('PRUEBA_ENV_A=desde_el_archivo\n')
        cargar_env(ruta)
        self.assertEqual(os.environ['PRUEBA_ENV_A'], 'desde_el_sistema')

    def test_archivo_inexistente_no_falla(self):
        cargar_env(os.path.join(tempfile.gettempdir(), 'no_existe_en_ninguna_parte', '.env'))


class ConfiguracionDeCorreoTest(SimpleTestCase):
    def test_sin_credenciales_se_imprime_en_la_consola(self):
        self.assertEqual(elegir_backend_correo({}), 'cuentas.correo.ConsolaLegibleBackend')

    def test_con_clave_se_usa_smtp(self):
        entorno = {'EMAIL_USUARIO': 'a@b.cl', 'EMAIL_CLAVE': 'secreta'}
        self.assertEqual(elegir_backend_correo(entorno), 'django.core.mail.backends.smtp.EmailBackend')

    def test_el_backend_explicito_tiene_prioridad(self):
        entorno = {'EMAIL_BACKEND': 'otro.Backend', 'EMAIL_CLAVE': 'secreta'}
        self.assertEqual(elegir_backend_correo(entorno), 'otro.Backend')

    def test_el_remitente_por_defecto(self):
        self.assertEqual(elegir_remitente({}), 'Aventuras del Sur <no-responder@aventuradelsur.cl>')

    def test_el_remitente_usa_la_cuenta_autenticada(self):
        self.assertEqual(elegir_remitente({'EMAIL_USUARIO': 'cuenta@gmail.com'}), 'Aventuras del Sur <cuenta@gmail.com>')

    def test_el_remitente_explicito_tiene_prioridad(self):
        entorno = {'EMAIL_USUARIO': 'cuenta@gmail.com', 'EMAIL_REMITENTE': 'Otro <otro@correo.cl>'}
        self.assertEqual(elegir_remitente(entorno), 'Otro <otro@correo.cl>')


class ConfiguracionDeEntornoTest(SimpleTestCase):
    def test_por_defecto_se_trabaja_en_modo_desarrollo(self):
        self.assertTrue(elegir_debug({}))

    def test_el_modo_debug_se_apaga_con_cero(self):
        for valor in ['0', 'false', 'False', 'no', '']:
            with self.subTest(valor=valor):
                self.assertFalse(elegir_debug({'DJANGO_DEBUG': valor}))

    def test_el_modo_debug_se_enciende_con_valores_afirmativos(self):
        for valor in ['1', 'true', 'TRUE', 'si', 'yes', ' 1 ']:
            with self.subTest(valor=valor):
                self.assertTrue(elegir_debug({'DJANGO_DEBUG': valor}))

    def test_los_hosts_por_defecto_son_locales(self):
        self.assertEqual(elegir_hosts({}), ['localhost', '127.0.0.1'])

    def test_los_hosts_se_leen_separados_por_comas(self):
        entorno = {'DJANGO_ALLOWED_HOSTS': ' ejemplo.cl , www.ejemplo.cl,,'}
        self.assertEqual(elegir_hosts(entorno), ['ejemplo.cl', 'www.ejemplo.cl'])

    def test_sin_hosts_la_lista_queda_vacia(self):
        self.assertEqual(elegir_hosts({'DJANGO_ALLOWED_HOSTS': ''}), [])

    def test_en_desarrollo_se_acepta_la_clave_por_defecto(self):
        self.assertEqual(elegir_clave_secreta({}, True), CLAVE_SECRETA_DE_DESARROLLO)

    def test_una_clave_propia_tiene_prioridad(self):
        entorno = {'DJANGO_SECRET_KEY': 'mi-clave-larga-y-unica'}
        self.assertEqual(elegir_clave_secreta(entorno, True), 'mi-clave-larga-y-unica')
        self.assertEqual(elegir_clave_secreta(entorno, False), 'mi-clave-larga-y-unica')

    def test_sin_debug_exige_una_clave_propia(self):
        with self.assertRaises(ImproperlyConfigured):
            elegir_clave_secreta({}, False)
        with self.assertRaises(ImproperlyConfigured):
            elegir_clave_secreta({'DJANGO_SECRET_KEY': '   '}, False)

    def test_sin_debug_no_acepta_la_clave_de_desarrollo_escrita_a_mano(self):
        with self.assertRaises(ImproperlyConfigured):
            elegir_clave_secreta({'DJANGO_SECRET_KEY': CLAVE_SECRETA_DE_DESARROLLO}, False)
