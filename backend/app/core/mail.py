"""Mail sender — interfaz + implementación console (C-03).

Decisión D9 (design.md): ``MailSender`` es una interfaz; la implementación
por defecto ``ConsoleMailSender`` escribe un log JSON estructurado con
``mail.to``, ``mail.subject`` y ``mail.link``. En C-12 llega una
implementación ``N8NMailSender`` que llama al webhook de N8N; se enchufa
vía ``MAILER_MODE`` en ``Settings``.

El link de reset filtra a los logs — es la única forma de probar el flujo
en desarrollo. En producción, los logs van a un sink seguro (no accesible
a usuarios). Documentado en ``.env.example`` con warning.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

# Logger dedicado de mail (separado del audit y del root) para poder
# configurarlo independientemente.
_mail_logger = logging.getLogger("mail")


class MailSender(ABC):
    """Interfaz abstracta para envío de mails.

    C-03 implementa solo :class:`ConsoleMailSender`. C-12 agrega
    :class:`N8NMailSender` que llama al webhook de N8N.
    """

    @abstractmethod
    def send_reset_link(self, to_email: str, link: str) -> None:
        """Envía un mail con el link de reset de contraseña.

        Args:
            to_email: Dirección del destinatario.
            link: URL completa del reset (``{base_url}/reset?token=<opaque>``).
        """
        raise NotImplementedError


class ConsoleMailSender(MailSender):
    """Implementación que loggea el mail como JSON (desarrollo / C-03).

    En producción, se reemplaza por :class:`N8NMailSender` cuando
    ``MAILER_MODE=n8n``.
    """

    def send_reset_link(self, to_email: str, link: str) -> None:
        """Loggea el mail con ``mail.to``, ``mail.subject``, ``mail.link``.

        Args:
            to_email: Email del destinatario.
            link: URL del link de reset.
        """
        extra = {
            "mail.to": to_email,
            "mail.subject": "Reset your password",
            "mail.link": link,
            "mail.template": "password_reset",
        }
        _mail_logger.info("mail.send", extra={"extra": extra})
