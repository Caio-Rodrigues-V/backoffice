import os

def carregar_env():
    """Carrega as variáveis do arquivo .env local para o ambiente do sistema."""
    caminho_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(caminho_env):
        with open(caminho_env, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith("#") and "=" in linha:
                    partes = linha.split("=", 1)
                    chave = partes[0].strip()
                    valor = partes[1].strip()
                    os.environ[chave] = valor

# Carrega as configurações
carregar_env()

# Credenciais reais carregadas do .env
EMAIL_USER = os.getenv("EMAIL_USER", "")
# Remove qualquer espaço em branco na senha de app
EMAIL_PASS = os.getenv("EMAIL_PASS", "").replace(" ", "")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")

# Configurações de Filtros
# Adicionado 'gmail.com' para permitir que você faça testes usando sua própria conta
DOMINIOS_AUTORIZADOS = [
    "multivix.edu.br",
    "grupoddm.com.br",
    "gmail.com"
]

# Palavras-chave exigidas no assunto do e-mail
ASSUNTO_PALAVRAS_CHAVE = [
    "negociação",
    "negociacao",
    "cobrança",
    "cobranca",
    "inaptos"
]

# Configurações do Banco de Dados
DB_NAME = "backoffice_agent.db"

# Integração com GoGenier (Robô de Abordagem)
SIMULAR_GOGENIER = True  # Mude para False para enviar requisições HTTP reais para a GoGenier
GOGENIER_WEBHOOK_URL = os.getenv("GOGENIER_WEBHOOK_URL", "http://localhost:5000/webhook/gogenier_mock")
GOGENIER_API_KEY = os.getenv("GOGENIER_API_KEY", "")

# Diretórios de Simulação (para salvar anexos e logs locais)
SIMULACAO_DIR = os.path.join(os.path.dirname(__file__), "simulador")
EMAILS_ENTRADA_DIR = os.path.join(SIMULACAO_DIR, "caixa_entrada")
EMAILS_SAIDA_DIR = os.path.join(SIMULACAO_DIR, "caixa_saida")
WHATSAPP_SIMULADO_DIR = os.path.join(SIMULACAO_DIR, "whatsapp_logs")

# Garantindo que os diretórios existam
for diretorio in [EMAILS_ENTRADA_DIR, EMAILS_SAIDA_DIR, WHATSAPP_SIMULADO_DIR]:
    os.makedirs(diretorio, exist_ok=True)
