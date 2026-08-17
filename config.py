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
                    valor = partes[1].strip().strip("'\"")
                    os.environ[chave] = valor

# Carrega as configurações
carregar_env()

# Credenciais reais carregadas do .env
EMAIL_USER = os.getenv("EMAIL_USER", "")
# Remove qualquer espaço em branco na senha de app
EMAIL_PASS = os.getenv("EMAIL_PASS", "").replace(" ", "").strip("'\"")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")

# Credenciais específicas de leitura (IMAP) com fallback
EMAIL_IMAP_USER = os.getenv("EMAIL_IMAP_USER", EMAIL_USER)
EMAIL_IMAP_PASS = os.getenv("EMAIL_IMAP_PASS", EMAIL_PASS).replace(" ", "").strip("'\"")

# Credenciais específicas de envio (SMTP) com fallback
EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER", EMAIL_USER)
EMAIL_SMTP_PASS = os.getenv("EMAIL_SMTP_PASS", EMAIL_PASS).replace(" ", "").strip("'\"")

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

# Configurações do Banco de Dados (Caminho Absoluto)
DB_NAME = os.path.join(os.path.dirname(__file__), "backoffice_agent.db")

# Integração com GoGenier (Robô de Abordagem)
SIMULAR_GOGENIER = True  # Mude para False para enviar requisições HTTP reais para a GoGenier
SIMULAR_WHATSAPP = os.getenv("SIMULAR_WHATSAPP", "True").lower() in ("true", "1", "yes")
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

# Configurações de Integração com o CRM
CRM_SUPABASE_URL = os.getenv("CRM_SUPABASE_URL", "")
CRM_SUPABASE_KEY = os.getenv("CRM_SUPABASE_KEY", "")
CRM_ADMIN_USER_ID = os.getenv("CRM_ADMIN_USER_ID", "")
CRM_PIPELINE_ID = os.getenv("CRM_PIPELINE_ID", "")
CRM_STAGE_ID = os.getenv("CRM_STAGE_ID", "")
CRM_MENSAGEM_INICIAL = os.getenv(
    "CRM_MENSAGEM_INICIAL",
    "Olá, {nome}! Somos da equipe de negociação do Grupo DDM. Identificamos uma pendência e gostaríamos de lhe ajudar a regularizar. Podemos conversar?"
)
