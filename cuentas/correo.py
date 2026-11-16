import sys

from django.core.mail.backends.base import BaseEmailBackend


class ConsolaLegibleBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        codificacion = sys.stdout.encoding or 'utf-8'
        enviados = 0
        for mensaje in email_messages:
            texto = (
                '-' * 60 + '\n'
                f'Asunto: {mensaje.subject}\n'
                f'Para: {", ".join(mensaje.to)}\n\n'
                f'{mensaje.body}\n'
                + '-' * 60 + '\n'
            )
            sys.stdout.write(texto.encode(codificacion, 'replace').decode(codificacion))
            sys.stdout.flush()
            enviados += 1
        return enviados
