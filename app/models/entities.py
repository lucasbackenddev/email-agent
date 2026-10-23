"""Modelos ORM — persistência de e-mails, remetentes e respostas."""
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Sender(Base):
    """Remetente — evita duplicação de dados (normalização)."""

    __tablename__ = "senders"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    emails: Mapped[list["Email"]] = relationship(back_populates="sender")


class Email(Base):
    """E-mail lido da caixa de entrada.

    `imap_uid` garante idempotência: o mesmo e-mail não é processado duas vezes.
    """

    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    imap_uid: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(default=utcnow)
    processed: Mapped[bool] = mapped_column(default=False, index=True)

    sender_id: Mapped[int] = mapped_column(ForeignKey("senders.id"), index=True)
    sender: Mapped["Sender"] = relationship(back_populates="emails")

    replies: Mapped[list["Reply"]] = relationship(back_populates="email")

    __table_args__ = (UniqueConstraint("imap_uid", name="uq_emails_imap_uid"),)


class Reply(Base):
    """Resposta gerada pela IA e/ou enviada pelo usuário."""

    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion: Mapped[str] = mapped_column(Text, default="")
    sent_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|sent|skipped
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)

    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), index=True)
    email: Mapped["Email"] = relationship(back_populates="replies")
