# 📧 Inbox Assistant API

Backend em Python que lê e-mails do Gmail, gera respostas com IA (Gemini)
e só envia **depois da sua aprovação**. Evolução de um script de terminal
para uma API REST em camadas, com persistência, fila de processamento e CI.

## Arquitetura

```
                        ┌──────────────────────────────────────────────┐
                        │              FastAPI (app/main.py)           │
   Gmail ◀──IMAP──▶  app/api/routes.py  ──▶  app/services/             │
   Gmail ◀──SMTP──▶      │                 ├─ reader_service    (IMAP)  │
                        │                 ├─ generator_service (Gemini) │
   Gemini ◀─────────────┘                 ├─ sender_service    (SMTP)  │
                                         └─ repository        (SQLAlchemy)
                        │
                        ├──▶ PostgreSQL (prod) / SQLite (dev)  ← migrations Alembic
                        └──▶ Redis ←→ Celery worker (app/worker.py, processamento em background)
```

**Fluxo:** Gmail (IMAP) → grava no banco (idempotente) → IA gera rascunho →
você revisa e aprova → envio (SMTP) → registrado no banco.

## Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| API | FastAPI | validação automática (Pydantic), docs interativas, async-ready |
| Banco | SQLAlchemy 2.0 + Alembic | ORM tipado (`Mapped[...]`) e migrations versionadas |
| Fila | Celery + Redis | processamento em background com retries; fallback local sem Redis |
| IA | Google Gemini | geração de respostas + classificação (`NAO_RESPONDER` para spam) |
| Qualidade | pytest + ruff + GitHub Actions | 18 testes, lint, CI no push/PR |

## Decisões técnicas

- **Idempotência por `imap_uid`**: o banco tem constraint única — o mesmo
  e-mail nunca é lido nem processado duas vezes, mesmo se o job falhar e repetir.
- **Normalização de remetentes**: tabela `senders` separada (um remetente = uma linha).
- **Camada de repositório**: os serviços de IMAP/SMTP/IA não conhecem o banco;
  toda persistência passa por `app/services/repository.py`.
- **Fallback local**: se o Redis não estiver no ar, as rotas `/queue/*`
  executam as tasks em linha — o modo dev nunca quebra.
- **Retry com backoff exponencial**: decorator `@retry` em `app/core/retry.py`
  para chamadas a serviços externos (IA, SMTP).
- **Aprovação obrigatória**: o agente nunca envia nada sozinho — resposta
  só sai via `POST /replies/send`, registrada no banco (`status: sent`).

## Endpoints

| Método | Rota | Função |
|---|---|---|
| GET | `/api/v1/health` | health check |
| GET | `/api/v1/emails` | sincroniza Gmail → banco e lista os e-mails |
| POST | `/api/v1/emails/process` | gera sugestão de resposta (IA) para os pendentes |
| POST | `/api/v1/replies/send` | envia resposta aprovada e registra no banco |
| POST | `/api/v1/queue/sync` | enfileira sincronização (Celery; fallback local) |
| POST | `/api/v1/queue/process` | enfileira processamento (Celery; fallback local) |
| GET | `/api/v1/queue/status/{id}` | status de uma task |

## Como rodar

### 1. Configuração (só na primeira vez)

```bash
cd email-agent
copy .env.example .env   # Windows
```

Preencha no `.env`:
- `GMAIL_USER` + `GMAIL_APP_PASSWORD` — [senha de app do Gmail](https://myaccount.google.com/apppasswords) (16 caracteres, exige verificação em 2 etapas)
- `GEMINI_API_KEY` — [chave do Google AI Studio](https://aistudio.google.com/apikey)
- `DATABASE_URL` — SQLite por padrão; para PostgreSQL: `postgresql+psycopg2://inbox:inbox_secret@localhost:5432/inbox`

### 2. Banco + Redis (opcional, com Docker)

```bash
docker compose up -d
alembic upgrade head   # cria as tabelas
```

Sem Docker, o projeto funciona com SQLite (padrão) e a fila cai no fallback local.

### 3. API

```bash
uvicorn app.main:app --reload
# docs interativas: http://localhost:8000/docs
```

### 4. Worker da fila (opcional)

```bash
celery -A app.celery_app worker --loglevel=info --pool=solo
```

## Testes e lint

```bash
python -m pytest tests/ -v      # 18 testes (banco em memória, serviços mockados)
python -m ruff check app tests  # lint
```

O CI (`.github/workflows/ci.yml`) roda ruff + pytest a cada push/PR.

## Estrutura

```
email-agent/
├── app/
│   ├── api/routes.py           # endpoints REST
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (.env)
│   │   ├── database.py         # engine + sessão SQLAlchemy
│   │   └── retry.py            # decorator @retry (backoff exponencial)
│   ├── models/entities.py      # ORM: Sender, Email, Reply
│   ├── schemas/models.py       # contratos de entrada/saída
│   ├── services/
│   │   ├── reader_service.py   # IMAP (Gmail)
│   │   ├── generator_service.py# Gemini
│   │   ├── sender_service.py   # SMTP (Gmail)
│   │   └── repository.py       # persistência + idempotência
│   ├── worker.py               # tasks Celery
│   ├── celery_app.py           # app Celery
│   └── main.py                 # fábrica FastAPI
├── alembic/                    # migrations
├── tests/                      # pytest (banco em memória, mocks)
├── .github/workflows/ci.yml    # CI: ruff + pytest
├── docker-compose.yml          # PostgreSQL + Redis
└── main.py                     # CLI original (referência)
```

## Segurança

- Nunca envie a resposta sem aprovação — risco de resposta errada automática é zero.
- Nunca compartilhe ou commite o `.env` (já está no `.gitignore`).
- A senha de app do Gmail é revogável a qualquer momento em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
