"""Geração de respostas de e-mail usando a API do Google Gemini."""
import config
from google import genai


SYSTEM_PROMPT = """Você é um assistente de e-mail profissional que escreve respostas
em nome do usuário. Regras:
- Responda em português, tom cordial e profissional (ou mais informal se o e-mail original for informal).
- Seja conciso: responda exatamente o que foi perguntado, sem enrolação.
- Se o e-mail for spam ou não exigir resposta, retorne exatamente: NAO_RESPONDER
- Não invente compromissos, preços ou informações. Se faltar informação para responder,
  escreva que o usuário vai verificar e retornar com mais detalhes.
- Não use placeholders como [seu nome]. Assine como "{assinatura}".
"""


def generate_reply(sender: str, subject: str, body: str, context: str = "") -> str:
    """Gera o texto da resposta para um e-mail."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    user_prompt = f"""Escreva uma resposta para o e-mail abaixo.

De: {sender}
Assunto: {subject}

Mensagem:
{body[:4000]}
"""
    if context.strip():
        user_prompt += f"\nContexto adicional sobre o usuário para personalizar a resposta:\n{context.strip()}"

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT.replace("{assinatura}", _signature()),
            temperature=0.5,
        ),
    )
    return (response.text or "").strip()


def _signature() -> str:
    nome = config.GMAIL_USER.split("@")[0].replace(".", " ").title()
    return nome
