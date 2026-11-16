import datetime
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .models import Categoria, Experiencia, Inscripcion
from .services import ReservaError, crear_reserva
from .tests import BaseTest


class BaseGuiaTest(BaseTest):
    def fijar(self, experiencia, **cambios):
        Experiencia.objects.filter(pk=experiencia.pk).update(**cambios)
        experiencia.refresh_from_db()
        return experiencia

    def estado(self, experiencia, nuevo, seguir=False):
        return self.client.post(
            reverse('cambiar_estado', args=[experiencia.pk]), {'estado': nuevo}, follow=seguir
        )

    def poner_en_curso(self, experiencia):
        return self.fijar(
            experiencia, estado='en_curso', fecha_hora=timezone.now() - timedelta(hours=1)
        )


class EstadosTest(BaseGuiaTest):
    def test_el_guia_inicia_la_ruta_cuando_se_acerca_su_hora(self):
        self.fijar(self.exp1, fecha_hora=timezone.now() + timedelta(minutes=30))
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'en_curso')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'en_curso')

    def test_no_se_inicia_con_mas_de_una_hora_de_anticipacion(self):
        self.ingresar(self.guia1)
        respuesta = self.estado(self.exp1, 'en_curso', seguir=True)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'programada')
        self.assertContains(respuesta, 'No se puede cambiar la ruta a ese estado.')

    def test_se_puede_suspender_una_ruta_programada(self):
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'suspendida')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'suspendida')

    def test_una_ruta_suspendida_se_reprograma(self):
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'programada')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'programada')

    def test_una_ruta_en_curso_se_finaliza(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'finalizada')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'finalizada')

    def test_una_ruta_en_curso_se_puede_suspender(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'suspendida')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'suspendida')

    def test_una_ruta_finalizada_ya_no_cambia(self):
        self.fijar(self.exp1, estado='finalizada')
        self.ingresar(self.guia1)
        for nuevo in ['programada', 'en_curso', 'suspendida']:
            self.estado(self.exp1, nuevo)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'finalizada')

    def test_no_se_vuelve_a_programada_desde_en_curso(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'programada')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'en_curso')

    def test_un_estado_inexistente_se_rechaza(self):
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'volando')
        self.estado(self.exp1, '')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'programada')

    def test_una_ruta_pasada_sin_iniciar_puede_finalizarse_directamente(self):
        self.fijar(self.exp1, fecha_hora=timezone.now() - timedelta(days=1))
        self.ingresar(self.guia1)
        self.estado(self.exp1, 'finalizada')
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'finalizada')

    def test_un_guia_no_cambia_el_estado_de_rutas_ajenas(self):
        self.ingresar(self.guia1)
        respuesta = self.estado(self.exp2, 'suspendida')
        self.assertEqual(respuesta.status_code, 404)
        self.exp2.refresh_from_db()
        self.assertEqual(self.exp2.estado, 'programada')

    def test_turistas_y_administradores_no_cambian_estados(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            self.assertEqual(self.estado(self.exp1, 'suspendida').status_code, 403)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'programada')

    def test_el_anonimo_es_enviado_al_login(self):
        respuesta = self.estado(self.exp1, 'suspendida')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_cambiar_el_estado_exige_post(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('cambiar_estado', args=[self.exp1.pk]))
        self.assertEqual(respuesta.status_code, 405)

    def test_las_transiciones_disponibles_segun_el_estado(self):
        self.assertEqual([v for v, _ in self.exp1.estados_siguientes], ['suspendida'])
        self.fijar(self.exp1, fecha_hora=timezone.now() + timedelta(minutes=10))
        self.assertEqual(
            [v for v, _ in self.exp1.estados_siguientes], ['en_curso', 'finalizada', 'suspendida']
        )
        self.fijar(self.exp1, estado='en_curso')
        self.assertEqual([v for v, _ in self.exp1.estados_siguientes], ['finalizada', 'suspendida'])
        self.fijar(self.exp1, estado='suspendida')
        self.assertEqual([v for v, _ in self.exp1.estados_siguientes], ['programada'])
        self.fijar(self.exp1, estado='finalizada')
        self.assertEqual(self.exp1.estados_siguientes, [])

    def test_el_estado_no_se_edita_desde_el_formulario_de_la_experiencia(self):
        self.ingresar(self.guia1)
        datos = self.datos_experiencia(self.exp1)
        datos['estado'] = 'finalizada'
        self.client.post(reverse('experiencia_actualizar', args=[self.exp1.pk]), datos)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.estado, 'programada')


class ReglasPorEstadoTest(BaseGuiaTest):
    def test_no_se_reserva_una_ruta_que_no_esta_programada(self):
        for estado in ['suspendida', 'en_curso', 'finalizada']:
            with self.subTest(estado=estado):
                self.fijar(self.exp1, estado=estado)
                with self.assertRaises(ReservaError):
                    crear_reserva(self.turista1, self.exp1.pk)
        self.assertFalse(Inscripcion.objects.exists())

    def test_el_turista_ve_el_motivo_si_la_ruta_no_admite_reservas(self):
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.turista1)
        respuesta = self.client.post(reverse('reservar', args=[self.exp1.pk]), follow=True)
        self.assertContains(respuesta, 'suspendida y no admite reservas')

    def test_el_catalogo_oculta_las_rutas_no_programadas(self):
        self.fijar(self.exp1, estado='suspendida')
        respuesta = self.client.get(reverse('catalogo'))
        self.assertEqual(list(respuesta.context['experiencias']), [self.exp2])

    def test_el_detalle_de_una_ruta_suspendida_no_ofrece_reservar(self):
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.turista1)
        respuesta = self.client.get(reverse('experiencia_detalle', args=[self.exp1.pk]))
        self.assertContains(respuesta, 'Esta ruta esta suspendida')
        self.assertNotContains(respuesta, reverse('reservar', args=[self.exp1.pk]))

    def test_no_se_cancela_una_reserva_de_una_ruta_en_curso_o_finalizada(self):
        reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.ingresar(self.turista1)
        for estado in ['en_curso', 'finalizada']:
            with self.subTest(estado=estado):
                self.fijar(self.exp1, estado=estado)
                respuesta = self.client.post(reverse('cancelar_reserva', args=[reserva.pk]), follow=True)
                self.assertContains(respuesta, 'No se puede cancelar: la ruta ya comenzo.')
                self.assertTrue(Inscripcion.objects.filter(pk=reserva.pk).exists())

    def test_si_se_cancela_una_reserva_de_una_ruta_suspendida(self):
        reserva = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.turista1)
        self.client.post(reverse('cancelar_reserva', args=[reserva.pk]))
        self.assertFalse(Inscripcion.objects.filter(pk=reserva.pk).exists())

    def test_el_administrador_no_crea_reservas_en_rutas_suspendidas(self):
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('inscripcion_crear'), {
            'usuario': self.turista1.pk,
            'experiencia': self.exp1.pk,
            'estado_pago': 'pendiente',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Inscripcion.objects.exists())


class VisitantesTest(BaseGuiaTest):
    def setUp(self):
        super().setUp()
        self.r1 = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp1)
        self.r2 = Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp1)
        self.url = reverse('registrar_visitantes', args=[self.exp1.pk])

    def test_el_formulario_muestra_a_cada_visitante(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, f'id="visitante{self.r1.pk}"')
        self.assertContains(respuesta, f'id="visitante{self.r2.pk}"')
        self.assertNotContains(respuesta, 'disabled')

    def test_con_la_ruta_programada_el_formulario_esta_bloqueado(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'Inicia la ruta antes de registrar visitantes.')
        self.assertContains(respuesta, 'disabled')

    def test_se_registran_los_presentes_y_el_resto_queda_ausente(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.client.post(self.url, {'asistieron': [self.r1.pk]})
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.assertTrue(self.r1.asistio)
        self.assertFalse(self.r2.asistio)

    def test_se_puede_corregir_la_asistencia(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.client.post(self.url, {'asistieron': [self.r1.pk]})
        self.client.post(self.url, {'asistieron': [self.r2.pk]})
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.assertFalse(self.r1.asistio)
        self.assertTrue(self.r2.asistio)

    def test_sin_marcar_a_nadie_todos_quedan_ausentes(self):
        self.poner_en_curso(self.exp1)
        Inscripcion.objects.filter(pk=self.r1.pk).update(asistio=True)
        self.ingresar(self.guia1)
        self.client.post(self.url, {})
        self.r1.refresh_from_db()
        self.assertFalse(self.r1.asistio)

    def test_tambien_se_registra_en_una_ruta_finalizada(self):
        self.fijar(self.exp1, estado='finalizada')
        self.ingresar(self.guia1)
        self.client.post(self.url, {'asistieron': [self.r1.pk, self.r2.pk]})
        self.assertEqual(Inscripcion.objects.filter(experiencia=self.exp1, asistio=True).count(), 2)

    def test_no_se_registra_con_la_ruta_programada_ni_suspendida(self):
        self.ingresar(self.guia1)
        for estado in ['programada', 'suspendida']:
            with self.subTest(estado=estado):
                self.fijar(self.exp1, estado=estado)
                respuesta = self.client.post(self.url, {'asistieron': [self.r1.pk]}, follow=True)
                self.assertContains(respuesta, 'Inicia la ruta antes de registrar visitantes.')
                self.assertFalse(Inscripcion.objects.filter(asistio=True).exists())

    def test_se_rechaza_una_reserva_de_otra_ruta(self):
        ajena = Inscripcion.objects.create(usuario=self.turista1, experiencia=self.exp2)
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        respuesta = self.client.post(self.url, {'asistieron': [self.r1.pk, ajena.pk]}, follow=True)
        self.assertContains(respuesta, 'Hay visitantes que no pertenecen a esta ruta.')
        self.assertFalse(Inscripcion.objects.filter(asistio=True).exists())

    def test_se_rechazan_valores_que_no_son_numeros(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        respuesta = self.client.post(self.url, {'asistieron': ['abc']}, follow=True)
        self.assertContains(respuesta, 'La lista de visitantes no es valida.')
        self.assertFalse(Inscripcion.objects.filter(asistio=True).exists())

    def test_un_guia_no_registra_visitantes_de_rutas_ajenas(self):
        self.ingresar(self.guia2)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'asistieron': [self.r1.pk]}).status_code, 404)

    def test_turistas_y_administradores_no_acceden(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_la_asistencia_se_ve_en_la_lista_de_reservas(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        self.client.post(self.url, {'asistieron': [self.r1.pk]})
        respuesta = self.client.get(reverse('inscripcion_lista'))
        self.assertContains(respuesta, 'Presente')
        self.assertContains(respuesta, 'Ausente')


class GrupoDetalleTest(BaseGuiaTest):
    def setUp(self):
        super().setUp()
        Usuario.objects.filter(pk=self.turista1.pk).update(
            first_name='Ana', last_name='Soto', email='ana@correo.cl', telefono='+56 9 1111 2222'
        )
        self.r1 = Inscripcion.objects.create(
            usuario=self.turista1, experiencia=self.exp1, estado_pago='confirmado', asistio=True
        )
        self.r2 = Inscripcion.objects.create(usuario=self.turista2, experiencia=self.exp1)
        self.url = reverse('grupo_detalle', args=[self.exp1.pk])

    def test_muestra_los_totales_del_grupo(self):
        self.poner_en_curso(self.exp1)
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context['total_reservas'], 2)
        self.assertEqual(respuesta.context['confirmados'], 1)
        self.assertEqual(respuesta.context['asistentes'], 1)
        self.assertEqual(respuesta.context['cupos_libres'], 0)
        self.assertContains(respuesta, '2 / 2')

    def test_lista_a_los_visitantes_con_sus_datos(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'Ana Soto')
        self.assertContains(respuesta, 'ana@correo.cl')
        self.assertContains(respuesta, '+56 9 1111 2222')
        self.assertContains(respuesta, 'turista2')
        self.assertContains(respuesta, 'Confirmado')
        self.assertContains(respuesta, 'Pendiente')

    def test_ofrece_solo_los_estados_permitidos(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, '<option value="suspendida">Suspendida</option>')
        self.assertNotContains(respuesta, '<option value="en_curso">')
        self.assertContains(respuesta, 'se puede iniciar desde una hora antes')

    def test_el_boton_de_visitantes_depende_del_estado(self):
        self.ingresar(self.guia1)
        self.assertNotContains(self.client.get(self.url), 'id="irRegistrarVisitantes"')
        self.poner_en_curso(self.exp1)
        self.assertContains(self.client.get(self.url), 'id="irRegistrarVisitantes"')

    def test_una_ruta_finalizada_no_ofrece_cambios_de_estado(self):
        self.fijar(self.exp1, estado='finalizada')
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'ya finalizo')
        self.assertNotContains(respuesta, 'id="formEstado"')

    def test_un_guia_no_ve_el_grupo_de_otro(self):
        self.ingresar(self.guia2)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_turistas_y_administradores_no_ven_el_grupo(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_el_listado_de_tours_enlaza_al_grupo_solo_para_el_guia(self):
        self.ingresar(self.guia1)
        self.assertContains(self.client.get(reverse('experiencia_lista')), self.url)
        self.client.logout()
        self.ingresar(self.admin)
        self.assertNotContains(self.client.get(reverse('experiencia_lista')), self.url)

    def test_el_listado_muestra_el_estado_de_la_ruta(self):
        self.fijar(self.exp1, estado='suspendida')
        self.ingresar(self.guia1)
        self.assertContains(self.client.get(reverse('experiencia_lista')), 'Suspendida')


class CalendarioTest(BaseGuiaTest):
    url = None

    def setUp(self):
        super().setUp()
        self.url = reverse('calendario')
        zona = timezone.get_current_timezone()
        self.marzo = datetime.datetime(2027, 3, 15, 10, 0, tzinfo=zona)
        self.fijar(self.exp1, fecha_hora=self.marzo)
        self.fijar(self.exp2, fecha_hora=self.marzo)
        self.abril = Experiencia.objects.create(
            titulo='Ruta de abril', descripcion='d', precio=1, cupo_maximo=3,
            fecha_hora=datetime.datetime(2027, 4, 2, 9, 0, tzinfo=zona),
            categoria=self.categoria, creador=self.guia1,
        )

    def celdas(self, respuesta):
        return [celda for semana in respuesta.context['semanas'] for celda in semana]

    def test_muestra_la_ruta_en_su_dia(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-03'})
        dia = [c for c in self.celdas(respuesta) if c['fecha'] == datetime.date(2027, 3, 15)][0]
        self.assertEqual(dia['rutas'], [self.exp1])
        self.assertEqual(respuesta.context['titulo_mes'], 'Marzo 2027')
        self.assertEqual(respuesta.context['total_del_mes'], 1)

    def test_no_muestra_rutas_ajenas_ni_de_otros_meses(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-03'})
        titulos = [r.titulo for c in self.celdas(respuesta) for r in c['rutas']]
        self.assertEqual(titulos, ['Ruta uno'])
        self.assertNotContains(respuesta, 'Ruta dos')
        self.assertNotContains(respuesta, 'Ruta de abril')

    def test_cada_mes_muestra_sus_rutas(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-04'})
        self.assertContains(respuesta, 'Ruta de abril')
        self.assertNotContains(respuesta, 'Ruta uno')

    def test_la_semana_comienza_el_lunes(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-03'})
        self.assertEqual(respuesta.context['dias_semana'][0], 'Lun')
        self.assertEqual(self.celdas(respuesta)[0]['fecha'], datetime.date(2027, 3, 1))
        self.assertTrue(all(len(semana) == 7 for semana in respuesta.context['semanas']))

    def test_los_dias_de_otros_meses_se_marcan_como_fuera_del_mes(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-04'})
        primera = self.celdas(respuesta)[0]
        self.assertFalse(primera['en_mes'])

    def test_la_navegacion_entre_meses(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-03'})
        self.assertEqual(respuesta.context['mes_anterior'], '2027-02')
        self.assertEqual(respuesta.context['mes_siguiente'], '2027-04')
        self.assertContains(respuesta, '?mes=2027-02')
        self.assertContains(respuesta, '?mes=2027-04')

    def test_la_navegacion_cruza_el_cambio_de_anio(self):
        self.ingresar(self.guia1)
        diciembre = self.client.get(self.url, {'mes': '2027-12'})
        self.assertEqual(diciembre.context['mes_siguiente'], '2028-01')
        enero = self.client.get(self.url, {'mes': '2027-01'})
        self.assertEqual(enero.context['mes_anterior'], '2026-12')

    def test_un_mes_invalido_cae_en_el_mes_actual(self):
        self.ingresar(self.guia1)
        actual = timezone.localdate().strftime('%Y-%m')
        for valor in ['', 'abc', '2027-13', '2027-00', '1900-01', '9999-12', '2027-3-1', '2027']:
            with self.subTest(valor=valor):
                respuesta = self.client.get(self.url, {'mes': valor})
                self.assertEqual(respuesta.status_code, 200)
                siguiente = respuesta.context['mes_siguiente']
                self.assertGreater(siguiente, actual)

    def test_sin_parametro_muestra_el_mes_actual_y_marca_hoy(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url)
        hoy = timezone.localdate()
        self.assertEqual(respuesta.context['titulo_mes'].split()[-1], str(hoy.year))
        self.assertEqual(len([c for c in self.celdas(respuesta) if c['es_hoy']]), 1)

    def test_la_ruta_enlaza_al_detalle_del_grupo(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-03'})
        self.assertContains(respuesta, reverse('grupo_detalle', args=[self.exp1.pk]))

    def test_una_ruta_cerca_de_medianoche_cae_en_su_dia_local(self):
        zona = timezone.get_current_timezone()
        tarde = datetime.datetime(2027, 5, 31, 23, 30, tzinfo=zona)
        ruta = Experiencia.objects.create(
            titulo='Ruta nocturna', descripcion='d', precio=1, cupo_maximo=3,
            fecha_hora=tarde, categoria=self.categoria, creador=self.guia1,
        )
        self.ingresar(self.guia1)
        respuesta = self.client.get(self.url, {'mes': '2027-05'})
        dia = [c for c in self.celdas(respuesta) if c['fecha'] == datetime.date(2027, 5, 31)][0]
        self.assertEqual(dia['rutas'], [ruta])

    def test_solo_el_guia_accede(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)


class PanelGuiaTest(BaseGuiaTest):
    def crear_ruta(self, titulo, creador, **extra):
        datos = dict(
            titulo=titulo, descripcion='d', precio=1, cupo_maximo=3,
            fecha_hora=timezone.now() + timedelta(days=2), categoria=self.categoria, creador=creador,
        )
        datos.update(extra)
        return Experiencia.objects.create(**datos)

    def test_cuenta_las_rutas_en_curso_propias(self):
        self.poner_en_curso(self.exp1)
        self.poner_en_curso(self.exp2)
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('panel'))
        self.assertEqual(respuesta.context['rutas_en_curso'], 1)
        self.assertContains(respuesta, 'id="rutasEnCurso"')

    def test_las_proximas_incluyen_rutas_en_curso_y_programadas_futuras(self):
        en_curso = self.crear_ruta('En curso', self.guia1, estado='en_curso', fecha_hora=timezone.now() - timedelta(hours=2))
        self.crear_ruta('Finalizada', self.guia1, estado='finalizada', fecha_hora=timezone.now() - timedelta(days=3))
        self.crear_ruta('Suspendida', self.guia1, estado='suspendida')
        self.crear_ruta('Ajena', self.guia2)
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('panel'))
        titulos = [r.titulo for r in respuesta.context['proximas']]
        self.assertEqual(titulos, ['En curso', 'Ruta uno'])
        self.assertContains(respuesta, reverse('grupo_detalle', args=[en_curso.pk]))

    def test_las_proximas_se_limitan_a_cinco_en_orden_de_fecha(self):
        for numero in range(7):
            self.crear_ruta(f'Futura {numero}', self.guia1, fecha_hora=timezone.now() + timedelta(days=10 + numero))
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('panel'))
        self.assertEqual(len(respuesta.context['proximas']), 5)
        fechas = [r.fecha_hora for r in respuesta.context['proximas']]
        self.assertEqual(fechas, sorted(fechas))

    def test_sin_rutas_proximas_muestra_un_aviso(self):
        Experiencia.objects.filter(creador=self.guia1).delete()
        self.ingresar(self.guia1)
        self.assertContains(self.client.get(reverse('panel')), 'No tienes rutas proximas.')

    def test_el_menu_del_guia_incluye_calendario_y_mis_tours(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('panel'))
        self.assertContains(respuesta, reverse('calendario'))
        self.assertContains(respuesta, 'Mis Tours')
        self.assertNotContains(respuesta, 'Mis Experiencias')

    def test_el_menu_de_otros_roles_no_incluye_el_calendario(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            self.assertNotContains(self.client.get(reverse('panel')), reverse('calendario'))


class PerfilEditableTest(BaseGuiaTest):
    def datos(self, **cambios):
        base = {
            'first_name': 'Marcela',
            'last_name': 'Rojas Soto',
            'email': 'nueva@correo.cl',
            'telefono': '+56 9 1234 5678',
        }
        base.update(cambios)
        return base

    def test_el_guia_actualiza_sus_datos(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('perfil'), self.datos(), follow=True)
        self.assertContains(respuesta, 'Tus datos fueron actualizados.')
        self.guia1.refresh_from_db()
        self.assertEqual(self.guia1.last_name, 'Rojas Soto')
        self.assertEqual(self.guia1.email, 'nueva@correo.cl')
        self.assertEqual(self.guia1.telefono, '+56 9 1234 5678')

    def test_el_perfil_muestra_los_datos_actuales(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('perfil'))
        self.assertContains(respuesta, 'guia1')
        self.assertContains(respuesta, 'Guia / Operador')
        self.assertContains(respuesta, 'id="formPerfil"')

    def test_el_usuario_y_el_rol_no_se_pueden_cambiar(self):
        self.ingresar(self.guia1)
        self.client.post(reverse('perfil'), self.datos(username='otro', rol='admin', is_superuser='on', is_staff='on'))
        self.guia1.refresh_from_db()
        self.assertEqual(self.guia1.username, 'guia1')
        self.assertEqual(self.guia1.rol, 'guia')
        self.assertFalse(self.guia1.is_superuser)
        self.assertFalse(self.guia1.is_staff)

    def test_el_telefono_es_opcional(self):
        self.ingresar(self.guia1)
        self.client.post(reverse('perfil'), self.datos(telefono=''))
        self.guia1.refresh_from_db()
        self.assertEqual(self.guia1.telefono, '')

    def test_formatos_de_telefono_validos(self):
        self.ingresar(self.guia1)
        for telefono in ['+56912345678', '912345678', '(2) 2345 6789', '+56 9 1234-5678']:
            with self.subTest(telefono=telefono):
                respuesta = self.client.post(reverse('perfil'), self.datos(telefono=telefono))
                self.assertEqual(respuesta.status_code, 302)

    def test_formatos_de_telefono_invalidos(self):
        self.ingresar(self.guia1)
        for telefono in ['abc', '123', '++56912345678', 'tel 12345678']:
            with self.subTest(telefono=telefono):
                respuesta = self.client.post(reverse('perfil'), self.datos(telefono=telefono))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'Ingresa un telefono valido')

    def test_un_telefono_demasiado_largo_se_rechaza(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('perfil'), self.datos(telefono='1' * 30))
        self.assertEqual(respuesta.status_code, 200)
        self.guia1.refresh_from_db()
        self.assertEqual(self.guia1.telefono, '')

    def test_nombre_apellido_y_correo_son_obligatorios(self):
        self.ingresar(self.guia1)
        for campo in ['first_name', 'last_name', 'email']:
            with self.subTest(campo=campo):
                respuesta = self.client.post(reverse('perfil'), self.datos(**{campo: ''}))
                self.assertEqual(respuesta.status_code, 200)

    def test_un_correo_invalido_se_rechaza(self):
        self.ingresar(self.guia1)
        respuesta = self.client.post(reverse('perfil'), self.datos(email='no-es-correo'))
        self.assertEqual(respuesta.status_code, 200)

    def test_cada_usuario_edita_solo_su_propio_perfil(self):
        self.ingresar(self.guia1)
        self.client.post(reverse('perfil'), self.datos(first_name='Cambiado'))
        self.turista1.refresh_from_db()
        self.assertNotEqual(self.turista1.first_name, 'Cambiado')

    def test_el_turista_y_el_administrador_tambien_editan_su_perfil(self):
        for usuario in (self.turista1, self.admin):
            self.client.logout()
            self.ingresar(usuario)
            respuesta = self.client.post(reverse('perfil'), self.datos(first_name=f'Editado {usuario.username}'))
            self.assertEqual(respuesta.status_code, 302)
            usuario.refresh_from_db()
            self.assertEqual(usuario.first_name, f'Editado {usuario.username}')

    def test_el_anonimo_es_enviado_al_login(self):
        respuesta = self.client.post(reverse('perfil'), self.datos())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_la_zona_de_riesgo_sigue_disponible_en_el_perfil(self):
        self.ingresar(self.turista1)
        respuesta = self.client.get(reverse('perfil'))
        self.assertContains(respuesta, 'id="abrirEliminarCuenta"')
        self.assertContains(respuesta, 'id="modalEliminarPaso2"')

    def test_el_guia_con_tours_ve_la_zona_de_riesgo_bloqueada(self):
        self.ingresar(self.guia1)
        respuesta = self.client.get(reverse('perfil'))
        self.assertContains(respuesta, 'Tu cuenta tiene tours creados')
        self.assertNotContains(respuesta, 'id="abrirEliminarCuenta"')
        self.assertNotContains(respuesta, 'id="modalEliminarPaso2"')
