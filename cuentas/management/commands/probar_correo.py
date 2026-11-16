from smtplib import SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Envia un correo de prueba con la configuracion de correo actual'

    def add_arguments(self, parser):
        parser.add_argument('destinatario')

    def handle(self, *args, **options):
        destinatario = options['destinatario']
        backend = settings.EMAIL_BACKEND.lower()
        if 'consola' in backend or 'console' in backend:
            self.stdout.write(self.style.WARNING(
                'El envio real no esta configurado: el correo solo se imprime en esta terminal. '
                'Completa EMAIL_USUARIO y EMAIL_CLAVE en el archivo .env.'
            ))
        try:
            send_mail(
                'Prueba de correo - Aventuras del Sur',
                'Si lees este mensaje, el envio de correos de Aventuras del Sur funciona correctamente.',
                settings.DEFAULT_FROM_EMAIL,
                [destinatario],
            )
        except SMTPAuthenticationError:
            raise CommandError(
                'El servidor rechazo el usuario o la clave. En Gmail se debe usar una clave de '
                'aplicacion de 16 caracteres (sin espacios), no la clave normal de la cuenta.'
            )
        except (SMTPException, OSError) as error:
            raise CommandError(f'No se pudo enviar el correo: {error}')
        self.stdout.write(self.style.SUCCESS(
            f'Correo enviado a {destinatario} desde {settings.DEFAULT_FROM_EMAIL}.'
        ))
