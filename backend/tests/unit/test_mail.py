"""Tests para ``app.core.mail`` (C-03): MailSender + ConsoleMailSender."""

from __future__ import annotations

import logging


class TestConsoleMailSender:
    """``ConsoleMailSender`` loggea el mail como JSON estructurado."""

    def test_send_does_not_raise(self):
        from app.core.mail import ConsoleMailSender

        sender = ConsoleMailSender()
        sender.send_reset_link("alice@example.com", "https://app/reset?token=abc")

    def test_send_emits_mail_log(self, caplog):
        from app.core.mail import ConsoleMailSender

        sender = ConsoleMailSender()
        caplog.set_level(logging.INFO, logger="mail")
        sender.send_reset_link("alice@example.com", "https://app/reset?token=abc")

        mail_records = [r for r in caplog.records if r.name == "mail"]
        assert len(mail_records) == 1

    def test_send_log_contains_to_subject_link(self, caplog):
        from app.core.mail import ConsoleMailSender

        sender = ConsoleMailSender()
        caplog.set_level(logging.INFO, logger="mail")
        sender.send_reset_link(
            "alice@example.com", "https://app/reset?token=opaque123"
        )

        rec = next(r for r in caplog.records if r.name == "mail")
        assert rec.extra is not None
        assert rec.extra["mail.to"] == "alice@example.com"
        assert rec.extra["mail.subject"] == "Reset your password"
        assert rec.extra["mail.link"] == "https://app/reset?token=opaque123"
        assert rec.extra["mail.template"] == "password_reset"

    def test_send_message_includes_template_marker(self, caplog):
        from app.core.mail import ConsoleMailSender

        sender = ConsoleMailSender()
        caplog.set_level(logging.INFO, logger="mail")
        sender.send_reset_link("a@b.com", "https://x")

        rec = next(r for r in caplog.records if r.name == "mail")
        assert "mail.send" in rec.getMessage()


class TestMailSenderInterface:
    """``MailSender`` es abstracta — no se puede instanciar directamente."""

    def test_mail_sender_is_abstract(self):
        from app.core.mail import MailSender

        with __import__("pytest").raises(TypeError):
            MailSender()  # type: ignore[abstract]

    def test_console_sender_is_mail_sender(self):
        """``ConsoleMailSender`` implementa la interfaz (es un ``MailSender``)."""
        from app.core.mail import ConsoleMailSender, MailSender

        sender = ConsoleMailSender()
        assert isinstance(sender, MailSender)

    def test_subclass_can_be_used_polymorphically(self):
        """Un caller que recibe un ``MailSender`` puede llamar ``send_reset_link``."""
        from app.core.mail import MailSender

        # Función genérica que acepta cualquier MailSender
        def notify(sender: MailSender, email: str, link: str) -> None:
            sender.send_reset_link(email, link)

        from app.core.mail import ConsoleMailSender

        notify(ConsoleMailSender(), "a@b.com", "https://x")  # no debe fallar


class TestConsoleMailSenderTriangulate:
    """Sanity checks cruzados."""

    def test_multiple_sends_emit_multiple_logs(self, caplog):
        from app.core.mail import ConsoleMailSender

        sender = ConsoleMailSender()
        caplog.set_level(logging.INFO, logger="mail")
        sender.send_reset_link("a@b.com", "l1")
        sender.send_reset_link("c@d.com", "l2")
        sender.send_reset_link("e@f.com", "l3")

        mail_records = [r for r in caplog.records if r.name == "mail"]
        assert len(mail_records) == 3
        emails = {r.extra["mail.to"] for r in mail_records}
        assert emails == {"a@b.com", "c@d.com", "e@f.com"}
