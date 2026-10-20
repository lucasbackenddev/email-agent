"""Agente de resposta de e-mails — leia, sugira, aprove e envie.

Fluxo:
1. Busca e-mails não lidos no Gmail
2. IA gera uma resposta sugerida para cada um
3. Você revisa: (A)provar e enviar, (E)ditar antes de enviar, (I)gnorar, (S)air
"""
import reader
import generator
import sender
import config


def main() -> None:
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        print("❌ Configure GMAIL_USER e GMAIL_APP_PASSWORD no arquivo .env (veja README.md)")
        return
    if not config.GEMINI_API_KEY:
        print("❌ Configure OPENAI_API_KEY no arquivo .env (veja README.md)")
        return

    print(f"📬 Buscando e-mails não lidos ({config.MAX_EMAILS_PER_RUN} máx.)...\n")
    emails = reader.fetch_unread()

    if not emails:
        print("✅ Nenhum e-mail não lido. Tudo em dia!")
        return

    enviado = ignorado = 0
    for i, mail in enumerate(emails, 1):
        print("=" * 60)
        print(f"[{i}/{len(emails)}]")
        print(f"De:      {mail['from']}")
        print(f"Assunto: {mail['subject']}")
        print("-" * 60)
        corpo = mail["body"].strip()
        print(corpo[:600] + ("..." if len(corpo) > 600 else ""))
        print("-" * 60)

        print("🤖 Gerando sugestão de resposta com IA...\n")
        try:
            sugestao = generator.generate_reply(mail["from"], mail["subject"], mail["body"])
        except Exception as e:
            print(f"❌ Erro ao gerar resposta: {e}\n")
            ignorado += 1
            continue

        if sugestao == "NAO_RESPONDER":
            print("🤔 A IA decidiu que este e-mail não precisa de resposta (spam/sem pergunta).")
            acao = input("Ignorar mesmo assim? (s/n): ").strip().lower()
            if acao == "s":
                ignorado += 1
                continue

        print("\n--- SUGESTÃO DE RESPOSTA ---")
        print(sugestao)
        print("----------------------------\n")

        acao = input("[A]provar e enviar | [E]ditar antes | [I]gnorar | [S]air: ").strip().lower()
        if acao == "a":
            try:
                remetente = mail["from"].split("<")[-1].rstrip(">").strip()
                sender.send(remetente, mail["subject"], sugestao)
                print(f"✅ Enviado para {remetente}\n")
                enviado += 1
            except Exception as e:
                print(f"❌ Falha no envio: {e}\n")
        elif acao == "e":
            print("Digite sua resposta (termine com uma linha contendo apenas 'FIM'):")
            linhas = []
            while True:
                linha = input()
                if linha.strip() == "FIM":
                    break
                linhas.append(linha)
            texto = "\n".join(linhas).strip()
            if texto:
                try:
                    remetente = mail["from"].split("<")[-1].rstrip(">").strip()
                    sender.send(remetente, mail["subject"], texto)
                    print(f"✅ Enviado para {remetente}\n")
                    enviado += 1
                except Exception as e:
                    print(f"❌ Falha no envio: {e}\n")
        elif acao == "s":
            break
        else:
            ignorado += 1

    print("=" * 60)
    print(f"Resumo: {enviado} enviados | {ignorado} ignorados")


if __name__ == "__main__":
    main()
