import os

from django.conf import settings
from django.urls import reverse

from .tests import BaseCuentasTest

INCLUDES_PANEL = [
    'includes/estilos_panel.html',
    'includes/sidebar.html',
    'includes/topbar.html',
    'includes/mensajes_panel.html',
    'includes/footer_panel.html',
    'includes/scripts_panel.html',
]
INCLUDES_PUBLICO = [
    'includes/estilos_publico.html',
    'includes/header_publico.html',
    'includes/mensajes_publico.html',
    'includes/footer_publico.html',
    'includes/scripts_publico.html',
]


def carpeta_de_plantillas():
    return os.path.join(settings.BASE_DIR, 'templates')


def leer_plantilla(nombre):
    with open(os.path.join(carpeta_de_plantillas(), nombre), encoding='utf-8') as archivo:
        return archivo.read()


class EstructuraDeArchivosTest(BaseCuentasTest):
    def test_toda_pagina_extiende_una_de_las_dos_bases(self):
        for carpeta, _, archivos in os.walk(carpeta_de_plantillas()):
            relativa = os.path.relpath(carpeta, carpeta_de_plantillas()).replace('\\', '/')
            for archivo in archivos:
                if not archivo.endswith('.html') or relativa.startswith('includes') or archivo.startswith('base_'):
                    continue
                with self.subTest(plantilla=f'{relativa}/{archivo}'):
                    fuente = open(os.path.join(carpeta, archivo), encoding='utf-8').read()
                    self.assertTrue(
                        "{% extends 'base_panel.html' %}" in fuente
                        or "{% extends 'base_publico.html' %}" in fuente
                    )

    def test_las_bases_no_escriben_header_footer_estilos_ni_scripts_en_linea(self):
        for base in ('base_panel.html', 'base_publico.html'):
            fuente = leer_plantilla(base)
            for etiqueta in ('<footer', '<nav', '<link', '<script', '<style'):
                with self.subTest(base=base, etiqueta=etiqueta):
                    self.assertNotIn(etiqueta, fuente)

    def test_cada_base_incluye_todas_sus_piezas(self):
        for pieza in INCLUDES_PANEL:
            with self.subTest(pieza=pieza):
                self.assertIn(f"{{% include '{pieza}' %}}", leer_plantilla('base_panel.html'))
                self.assertTrue(os.path.exists(os.path.join(carpeta_de_plantillas(), pieza)))
        for pieza in INCLUDES_PUBLICO:
            with self.subTest(pieza=pieza):
                self.assertIn(f"{{% include '{pieza}' %}}", leer_plantilla('base_publico.html'))
                self.assertTrue(os.path.exists(os.path.join(carpeta_de_plantillas(), pieza)))

    def test_las_piezas_de_cada_diseno_no_se_mezclan(self):
        self.assertNotIn('data-bs-', leer_plantilla('includes/mensajes_panel.html'))
        self.assertIn('data-dismiss', leer_plantilla('includes/mensajes_panel.html'))
        self.assertNotIn('data-dismiss', leer_plantilla('includes/mensajes_publico.html'))
        self.assertIn('data-bs-dismiss', leer_plantilla('includes/mensajes_publico.html'))

    def test_las_bases_declaran_los_bloques_que_usan_las_paginas(self):
        for base in ('base_panel.html', 'base_publico.html'):
            fuente = leer_plantilla(base)
            for bloque in ('title', 'contenido', 'scripts'):
                with self.subTest(base=base, bloque=bloque):
                    self.assertIn(f'{{% block {bloque} %}}', fuente)


class EstructuraRenderizadaTest(BaseCuentasTest):
    def paginas_del_panel(self):
        return {
            self.turista: [reverse('panel'), reverse('perfil'), reverse('mis_reservas')],
            self.guia: [
                reverse('panel'),
                reverse('perfil'),
                reverse('calendario'),
                reverse('experiencia_lista'),
                reverse('experiencia_crear'),
                reverse('grupo_detalle', args=[self.exp.pk]),
                reverse('registrar_visitantes', args=[self.exp.pk]),
            ],
            self.admin: [
                reverse('panel'),
                reverse('usuario_lista'),
                reverse('usuario_crear'),
                reverse('categoria_lista'),
                reverse('inscripcion_lista'),
            ],
        }

    def paginas_publicas_anonimas(self):
        return [
            reverse('inicio'),
            reverse('catalogo'),
            reverse('experiencia_detalle', args=[self.exp.pk]),
            reverse('login'),
            reverse('registro'),
            reverse('recuperar_clave'),
            '/esta-pagina-no-existe/',
        ]

    def test_las_paginas_del_panel_usan_todas_las_piezas_del_panel(self):
        for usuario, rutas in self.paginas_del_panel().items():
            self.client.logout()
            self.ingresar(usuario)
            for ruta in rutas:
                with self.subTest(usuario=usuario.username, ruta=ruta):
                    respuesta = self.client.get(ruta)
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertTemplateUsed(respuesta, 'base_panel.html')
                    for pieza in INCLUDES_PANEL:
                        self.assertTemplateUsed(respuesta, pieza)
                    self.assertTemplateNotUsed(respuesta, 'base_publico.html')

    def test_las_paginas_publicas_usan_todas_las_piezas_publicas(self):
        for ruta in self.paginas_publicas_anonimas():
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertTemplateUsed(respuesta, 'base_publico.html')
                for pieza in INCLUDES_PUBLICO:
                    self.assertTemplateUsed(respuesta, pieza)
                self.assertTemplateNotUsed(respuesta, 'base_panel.html')

    def test_la_pagina_de_acceso_denegado_usa_el_diseno_publico(self):
        self.ingresar(self.turista)
        respuesta = self.client.get(reverse('categoria_lista'))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTemplateUsed(respuesta, 'includes/header_publico.html')
        self.assertTemplateUsed(respuesta, 'includes/footer_publico.html')

    def test_cada_pagina_tiene_exactamente_un_footer_y_un_header(self):
        paginas = [(None, ruta) for ruta in self.paginas_publicas_anonimas()]
        for usuario, rutas in self.paginas_del_panel().items():
            paginas.extend((usuario, ruta) for ruta in rutas)
        for usuario, ruta in paginas:
            self.client.logout()
            if usuario:
                self.ingresar(usuario)
            with self.subTest(usuario=getattr(usuario, 'username', 'anonimo'), ruta=ruta):
                contenido = self.client.get(ruta).content.decode()
                self.assertEqual(contenido.count('<footer'), 1)
                self.assertEqual(contenido.count('<nav'), 1)

    def test_el_footer_muestra_el_nombre_y_el_anio_en_ambos_disenos(self):
        for ruta in (reverse('inicio'), reverse('login')):
            self.assertContains(self.client.get(ruta), 'Aventuras del Sur &copy;')
        self.ingresar(self.turista)
        self.assertContains(self.client.get(reverse('panel')), 'Aventuras del Sur &copy;')

    def test_los_disenos_no_se_mezclan_en_pantalla(self):
        self.assertNotContains(self.client.get(reverse('inicio')), 'id="accordionSidebar"')
        self.ingresar(self.turista)
        panel = self.client.get(reverse('panel'))
        self.assertContains(panel, 'id="accordionSidebar"')
        self.assertNotContains(panel, 'id="menuPrincipal"')

    def test_los_estilos_y_scripts_se_cargan_una_sola_vez(self):
        self.ingresar(self.turista)
        panel = self.client.get(reverse('perfil')).content.decode()
        for archivo in ('sb-admin-2.min.css', 'jquery.min.js', 'dataTables.bootstrap4.min.js', 'function encadenarModales'):
            with self.subTest(archivo=archivo):
                self.assertEqual(panel.count(archivo), 1)
        publico = self.client.get(reverse('inicio')).content.decode()
        for archivo in ('bootstrap.min.css', 'bootstrap.bundle.min.js'):
            with self.subTest(archivo=archivo):
                self.assertEqual(publico.count(archivo), 1)

    def test_los_scripts_de_la_pagina_van_despues_de_jquery(self):
        self.ingresar(self.turista)
        contenido = self.client.get(reverse('perfil')).content.decode()
        self.assertLess(contenido.index('jquery.min.js'), contenido.index("$('#abrirEliminarCuenta')"))

    def test_los_mensajes_usan_el_marcado_de_cada_diseno(self):
        self.ingresar(self.turista)
        self.client.post(reverse('eliminar_cuenta'), {'password': 'incorrecta'})
        panel = self.client.get(reverse('perfil'))
        self.assertContains(panel, 'La contraseña ingresada no es correcta.')
        self.assertContains(panel, 'data-dismiss="alert"')
        self.assertNotContains(panel, 'data-bs-dismiss')
        self.client.logout()
        publico = self.client.post(reverse('recuperar_clave'), {
            'username': 'turista1',
            'email': 'turista1@correo.cl',
            'new_password1': 'ClaveNueva2025x',
            'new_password2': 'ClaveNueva2025x',
        }, follow=True)
        self.assertContains(publico, 'Tu contraseña fue actualizada.')
        self.assertContains(publico, 'data-bs-dismiss="alert"')
        self.assertNotContains(publico, 'data-dismiss="alert"')
