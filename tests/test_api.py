"""Testes da API — serviços externos (IMAP/IA/SMTP) mockados."""
import pytest

from app.services import reader_service


@pytest.fixture
def fake_emails():
    return [
        {"id": "100", "from": "Alice <alice@x.com>", "subject": "Pergunta", "body": "Como vai?"},
        {"id": "101", "from": "Bob <bob@y.com>", "subject": "Oferta!!!", "body": "Compre já"},
    ]


@pytest.fixture
def mock_reader(monkeypatch, fake_emails):
    """Substitui a leitura do Gmail por dados fixos."""
    monkeypatch.setattr(
        reader_service, "fetch_unread", lambda limit=None: fake_emails[: limit or None]
    )
    return fake_emails


@pytest.fixture
def mock_generator(monkeypatch):
    """Substitui a chamada à IA por resposta fixa."""
    from app.services import generator_service

    calls = []

    def fake_generate(sender, subject, body, context=""):
        calls.append((sender, subject, body))
        return "NAO_RESPONDER" if "Oferta" in subject else f"Resposta para {sender}"

    monkeypatch.setattr(generator_service, "generate_reply", fake_generate)
    return calls


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestListEmails:
    def test_syncs_and_lists(self, client, mock_reader):
        resp = client.get("/api/v1/emails")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {e["id"] for e in data} == {"100", "101"}

    def test_idempotent_second_call(self, client, mock_reader):
        client.get("/api/v1/emails")
        resp = client.get("/api/v1/emails")
        assert resp.status_code == 200
        assert len(resp.json()) == 2  # não duplicou

    def test_reader_failure_returns_502(self, client, monkeypatch):
        from app.services import reader_service

        def boom(limit=None):
            raise ConnectionError("IMAP down")

        monkeypatch.setattr(reader_service, "fetch_unread", boom)
        resp = client.get("/api/v1/emails")
        assert resp.status_code == 502


class TestProcessEmails:
    def test_generates_and_persists(self, client, mock_reader, mock_generator):
        resp = client.post("/api/v1/emails/process")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2
        assert {c[0] for c in mock_generator} == {"alice@x.com", "bob@y.com"}  # e-mails puros passados à IA

        # e-mail com "Oferta" no assunto deve ser pulado
        by_id = {r["email_id"]: r for r in results}
        assert by_id["100"]["suggestion"] is not None
        assert by_id["101"]["suggestion"] is None
        assert "não responder" in by_id["101"]["skip_reason"].lower()

    def test_reprocessing_does_not_duplicate(self, client, mock_reader, mock_generator):
        client.post("/api/v1/emails/process")
        # segunda passada não reprocessa (já marcados como processed)
        resp = client.post("/api/v1/emails/process")
        assert resp.json() == []


class TestSendReply:
    def test_send_records_in_db(self, client, mock_reader, monkeypatch):
        from app.services import sender_service

        sent = []
        monkeypatch.setattr(
            sender_service, "send",
            lambda to, subject, body: sent.append((to, subject, body)),
        )

        resp = client.post("/api/v1/replies/send", json={
            "email_id": "100", "to": "alice@x.com",
            "subject": "Re: Pergunta", "body": "Tudo ótimo!",
        })
        assert resp.status_code == 200
        assert resp.json() == {"status": "sent", "to": "alice@x.com"}
        assert len(sent) == 1

    def test_send_failure_returns_502(self, client, monkeypatch):
        from app.services import sender_service

        def boom(to, subject, body):
            raise ConnectionError("SMTP down")

        monkeypatch.setattr(sender_service, "send", boom)
        resp = client.post("/api/v1/replies/send", json={
            "email_id": "100", "to": "a@x.com", "subject": "s", "body": "b",
        })
        assert resp.status_code == 502

    def test_send_requires_payload(self, client):
        resp = client.post("/api/v1/replies/send", json={})
        assert resp.status_code == 422
