"""Serviço de geração de respostas via API do Google Gemini.

Migrado do generator.py original.
"""
import logging

from google import genai
from google.genai import errors as genai_errors

from app.core.config import get_settings
from app.core.retry import retry

logger = logging.getLogger(__name__)

# Erros transitórios da API Gemini que valem retry (5xx e rate limit)
_RETRYABLE = (genai_errors.APIError, ConnectionError, TimeoutError)

SYSTEM_PROMPT = """Você é um assistente de e-mail profissional que escreve respostas
em nome do usuário. Regras:
- Responda em português, tom cordial e profissional (ou mais informal se o e-mail original for informal).
- Seja conciso: responda exatamente o que foi perguntado, sem enrolação.
- Se o e-mail for spam ou não exigir resposta, retorne exatamente: NAO_RESPONDER
- Não invente compromissos, preços ou informações. Se faltar informação para responder,
  escreva que o usuário vai verificar e retornar com mais detalhes.
- Não use placeholders como [seu nome]. Assine como "{assinatura}".
"""


def _signature() -> str:
    settings = get_settings()
    return settings.gmail_user.split("@")[0].replace(".", " ").title()


@retry(times=3, backoff=2.0, initial_delay=1.0, exceptions=_RETRYABLE, log=logger)
def generate_reply(sender: str, subject: str, body: str, context: str = "") -> str:
    """Gera o texto da resposta para um e-mail (com retry para erros transitórios)."""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    user_prompt = f"""Escreva uma resposta para o e-mail abaixo.

De: {sender}
Assunto: {subject}

Mensagem:
{body[:4000]}
"""
    if context.strip():
        user_prompt += f"\nContexto adicional sobre o usuário para personalizar a resposta:\n{context.strip()}"

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT.replace("{assinatura}", _signature()),
            temperature=0.5,
        ),
    )
    return (response.text or "").strip()
