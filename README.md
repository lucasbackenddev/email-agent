# 📧 Agente de Resposta de E-mails

Agente em Python que lê e-mails não lidos do Gmail, gera respostas com a OpenAI
e só envia **depois da sua aprovação**.

## Fluxo
```
Gmail (IMAP) → IA gera rascunho → Você revisa → [A]provar / [E]ditar / [I]gnorar → Envio (SMTP)
```

## Configuração (só na primeira vez)

### 1. Gmail — criar "Senha de App"
1. Ative a verificação em 2 etapas: https://myaccount.google.com/security
2. Crie uma senha de app em: https://myaccount.google.com/apppasswords
   - Escolha "E-mail" / "Outro" e dê um nome (ex.: "agente-py")
3. Copie a senha de **16 caracteres** gerada — é ela que você vai usar no `.env` (não a senha normal do Gmail)

### 2. OpenAI — chave da API
1. Acesse: https://platform.openai.com/api-keys
2. Crie uma chave e copie (começa com `sk-`)

### 3. Arquivo .env
```bash
copy .env.example .env
```
Edite o `.env` com seu e-mail, a senha de app e a chave da OpenAI.

## Uso
```bash
python -X utf8 main.py
```
(No Windows o `-X utf8` é necessário para exibir acentos e emojis corretamente.)
Para cada e-mail não lido, o agente mostra o e-mail + uma resposta sugerida.
Você escolhe: **A** aprovar e enviar, **E** editar antes, **I** ignorar, **S** sair.

## Arquivos
| Arquivo | Função |
|---|---|
| `main.py` | Fluxo principal com menu de aprovação |
| `reader.py` | Busca e-mails via IMAP (Gmail) |
| `generator.py` | Gera respostas com a OpenAI |
| `sender.py` | Envia respostas via SMTP (Gmail) |
| `config.py` | Configurações (lê o `.env`) |

## Dicas de segurança
- O agente **nunca envia sem você aprovar** — assim não tem risco de resposta errada automática.
- Nunca compartilhe ou commite o arquivo `.env`.
