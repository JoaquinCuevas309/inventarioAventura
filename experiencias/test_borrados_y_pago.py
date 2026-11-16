from django.db import models
from django.db.models import ProtectedError
from django.urls import reverse

from cuentas.models import Usuario

from .models import Categoria, Experiencia, Inscripcion
from .test_flujo_guia import BaseGuiaTest


class PoliticaDeBorradoTest(BaseGuiaTest):
    def test_las_relaciones_con_historial_estan_protegidas(self):
        relaciones = [
            Experiencia._meta.get_field('categoria'),
            Experiencia._meta.get_field('creador'),
            Inscripcion._meta.get_field('usuario'),
            Inscripcion._meta.get_field('experiencia'),
        ]
        for campo in relaciones:
            with self.subTest(campo=campo.name):
                self.assertIs(campo.remote_field.on_delete, models.PROTECT)

    def test_el_modelo_impide_borrar_una_categoria_con_experiencias(self):
        with self.assertRaises(ProtectedError):
            self.categoria.delete()
        self.assertEqual(Experiencia.objects.count(), 2)

    def test_el_modelo_impide_borrar_una_experiencia_con_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        with self.assertRaises(ProtectedError):
            self.exp1.delete()

    def test_el_modelo_impide_borrar_un_usuario_con_reservas_o_tours(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        for usuario in (self.turista1, self.guia1):
            with self.subTest(usuario=usuario.username):
                with self.assertRaises(ProtectedError):
                    usuario.delete()
        self.assertEqual(Inscripcion.objects.count(), 1)


class BorrarCategoriaTest(BaseGuiaTest):
    def test_no_se_elimina_una_categoria_con_experiencias_y_se_explica_el_motivo(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('categoria_borrar', args=[self.categoria.pk]), follow=True)
        self.assertRedirects(respuesta, reverse('categoria_lista'))
        self.assertContains(respuesta, 'la categoria tiene experiencias asociadas')
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())
        self.assertEqual(Experiencia.objects.count(), 2)

    def test_se_elimina_una_categoria_sin_experiencias(self):
        vacia = Categoria.objects.create(nombre='Vacia')
        self.ingresar(self.admin)
        self.client.post(reverse('categoria_borrar', args=[vacia.pk]))
        self.assertFalse(Categoria.objects.filter(pk=vacia.pk).exists())

    def test_la_confirmacion_explica_la_regla(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('categoria_borrar', args=[self.categoria.pk]))
        self.assertContains(respuesta, 'Solo se puede eliminar si no tiene experiencias')
        self.assertNotContains(respuesta, 'Se eliminaran tambien')

    def test_en_su_lugar_se_puede_desactivar_y_se_conserva_el_historial(self):
        self.ingresar(self.admin)
        self.client.post(reverse('categoria_actualizar', args=[self.categoria.pk]), {'nombre': 'Trekking'})
        self.categoria.refresh_from_db()
        self.assertFalse(self.categoria.activo)
        self.assertEqual(Experiencia.objects.count(), 2)
        self.assertEqual(list(self.client.get(reverse('catalogo')).context['experiencias']), [])


class BorrarExperienciaTest(BaseGuiaTest):
    def test_no_se_elimina_una_experiencia_con_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]), follow=True)
        self.assertContains(respuesta, 'la experiencia tiene reservas asociadas')
        self.assertTrue(Experiencia.objects.filter(pk=self.exp1.pk).exists())
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_se_elimina_una_experiencia_sin_reservas(self):
        self.ingresar(self.admin)
        self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertFalse(Experiencia.objects.filter(pk=self.exp1.pk).exists())

    def test_eliminando_primero_las_reservas_ya_se_puede_eliminar_la_experiencia(self):
        reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        self.client.post(reverse('inscripcion_borrar', args=[reserva.pk]))
        self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertFalse(Experiencia.objects.filter(pk=self.exp1.pk).exists())

    def test_la_confirmacion_explica_la_regla(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertContains(respuesta, 'Solo se puede eliminar si no tiene reservas')

    def test_el_guia_sigue_sin_poder_eliminar(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('experiencia_borrar', args=[self.exp1.pk]))
        self.assertEqual(respuesta.status_code, 403)

    def test_se_puede_eliminar_una_reserva_sin_restricciones(self):
        reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        self.client.post(reverse('inscripcion_borrar', args=[reserva.pk]))
        self.assertFalse(Inscripcion.objects.filter(pk=reserva.pk).exists())


class BorrarUsuarioTest(BaseGuiaTest):
    def test_no_se_elimina_un_guia_con_tours(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('usuario_borrar', args=[self.guia1.pk]), follow=True)
        self.assertRedirects(respuesta, reverse('usuario_lista'))
        self.assertContains(respuesta, 'el usuario tiene reservas o tours asociados')
        self.assertTrue(Usuario.objects.filter(pk=self.guia1.pk).exists())
        self.assertTrue(Experiencia.objects.filter(pk=self.exp1.pk).exists())

    def test_no_se_elimina_un_turista_con_reservas(self):
        Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.admin)
        self.client.post(reverse('usuario_borrar', args=[self.turista1.pk]))
        self.assertTrue(Usuario.objects.filter(pk=self.turista1.pk).exists())
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_se_elimina_un_usuario_sin_registros(self):
        self.ingresar(self.admin)
        self.client.post(reverse('usuario_borrar', args=[self.turista2.pk]))
        self.assertFalse(Usuario.objects.filter(pk=self.turista2.pk).exists())

    def test_la_confirmacion_explica_la_regla(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('usuario_borrar', args=[self.guia1.pk]))
        self.assertContains(respuesta, 'Solo se puede eliminar si no tiene reservas ni tours asociados')

    def test_en_su_lugar_se_puede_desactivar_la_cuenta(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('usuario_actualizar', args=[self.guia1.pk]), {
            'username': 'guia1',
            'first_name': 'Guia',
            'last_name': 'Uno',
            'email': 'guia1@correo.cl',
            'telefono': '',
            'rol': 'guia',
            'password1': '',
            'password2': '',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.guia1.refresh_from_db()
        self.assertFalse(self.guia1.is_active)
        self.assertTrue(Experiencia.objects.filter(pk=self.exp1.pk).exists())
        self.assertFalse(self.client_class().login(username='guia1', password='clave12345'))

    def test_el_administrador_no_se_elimina_a_si_mismo(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('usuario_borrar', args=[self.admin.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())


class ConfirmarPagoTest(BaseGuiaTest):
    def setUp(self):
        super().setUp()
        self.reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.url = reverse('confirmar_pago', args=[self.reserva.pk])

    def test_el_administrador_confirma_un_pago_pendiente(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(self.url, follow=True)
        self.assertRedirects(respuesta, reverse('inscripcion_lista'))
        self.assertContains(respuesta, 'Pago confirmado: turista1 en Ruta uno.')
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_pago, 'confirmado')

    def test_confirmar_dos_veces_no_cambia_nada_y_lo_informa(self):
        self.ingresar(self.admin)
        self.client.post(self.url)
        respuesta = self.client.post(self.url, follow=True)
        self.assertContains(respuesta, 'Esta reserva ya tenia el pago confirmado.')
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_pago, 'confirmado')

    def test_solo_cambia_el_estado_de_pago(self):
        Inscripcion.objects.filter(pk=self.reserva.pk).update(asistio=True)
        antes = Inscripcion.objects.get(pk=self.reserva.pk)
        self.ingresar(self.admin)
        self.client.post(self.url)
        despues = Inscripcion.objects.get(pk=self.reserva.pk)
        self.assertEqual(despues.estado_pago, 'confirmado')
        self.assertEqual(
            (despues.usuario_id, despues.experiencia_id, despues.asistio, despues.fecha_inscripcion),
            (antes.usuario_id, antes.experiencia_id, antes.asistio, antes.fecha_inscripcion),
        )

    def test_no_afecta_a_otras_reservas(self):
        otra = Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp1)
        self.ingresar(self.admin)
        self.client.post(self.url)
        otra.refresh_from_db()
        self.assertEqual(otra.estado_pago, 'pendiente')

    def test_exige_post(self):
        self.ingresar(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_guias_y_turistas_no_pueden_confirmar_pagos(self):
        for usuario in (self.guia1, self.turista1):
            self.client.logout()
            self.ingresar(usuario)
            self.assertEqual(self.client.post(self.url).status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_pago, 'pendiente')

    def test_el_anonimo_es_enviado_al_login(self):
        respuesta = self.client.post(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_una_reserva_inexistente_da_404(self):
        self.ingresar(self.admin)
        self.assertEqual(self.client.post(reverse('confirmar_pago', args=[99999])).status_code, 404)

    def test_la_lista_ofrece_el_boton_solo_en_reservas_pendientes(self):
        confirmada = Inscripcion.objects.create(
            usuario=self.turista2, experiencia=self.exp1, estado_pago='confirmado'
        )
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('inscripcion_lista'))
        self.assertContains(respuesta, self.url)
        self.assertNotContains(respuesta, reverse('confirmar_pago', args=[confirmada.pk]))

    def test_tras_confirmar_el_boton_desaparece(self):
        self.ingresar(self.admin)
        self.client.post(self.url)
        self.assertNotContains(self.client.get(reverse('inscripcion_lista')), self.url)

    def test_el_guia_no_ve_el_boton_en_las_reservas_de_su_grupo(self):
        self.ingresar(self.guia1)
        self.assertNotContains(self.client.get(reverse('inscripcion_lista')), self.url)

    def test_el_turista_ve_el_pago_confirmado_y_ya_no_puede_cancelar(self):
        self.ingresar(self.admin)
        self.client.post(self.url)
        self.client.logout()
        self.ingresar(self.turista1)
        respuesta = self.client.get(reverse('mis_reservas'))
        self.assertContains(respuesta, 'Confirmado')
        self.assertNotContains(respuesta, reverse('cancelar_reserva', args=[self.reserva.pk]))

    def test_el_guia_ve_el_pago_confirmado_en_su_grupo(self):
        self.ingresar(self.admin)
        self.client.post(self.url)
        self.client.logout()
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('grupo_detalle', args=[self.exp1.pk]))
        self.assertEqual(respuesta.context['confirmados'], 1)
