"""Schemas Pydantic (contratos de entrada/saída da API)."""
from pydantic import BaseModel, ConfigDict, Field


class EmailOut(BaseModel):
    """E-mail lido da caixa de entrada."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(serialization_alias="from")
    subject: str
    body: str


class ReplySend(BaseModel):
    """Corpo de `POST /replies/send` — resposta aprovada pelo usuário."""

    email_id: str  # imap_uid do e-mail original (para registrar o envio)
    to: str
    subject: str
    body: str


class ProcessResult(BaseModel):
    """Resultado do processamento de um e-mail (sugestão da IA)."""

    model_config = ConfigDict(populate_by_name=True)

    email_id: str
    from_: str = Field(serialization_alias="from")
    subject: str
    suggestion: str | None = None
    skip_reason: str | None = None
