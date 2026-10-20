"""Configuração central do agente de e-mails."""
import os
from dotenv import load_dotenv

load_dotenv()  # carrega variáveis do arquivo .env

# --- Gmail ---
GMAIL_USER = os.getenv("GMAIL_USER", "")          # seuemail@gmail.com
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")  # senha de app de 16 caracteres

# --- Gemini (Google AI Studio) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Comportamento ---
CHECK_FOLDER = "INBOX"
UNREAD_ONLY = True          # processar apenas e-mails não lidos
MAX_EMAILS_PER_RUN = 5      # limite de e-mails por execução
