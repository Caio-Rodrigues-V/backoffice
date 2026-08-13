import config
import imaplib

def testar():
    print("=== TESTANDO CONEXAO IMAP DO GMAIL ===")
    print(f"EMAIL_USER: {config.EMAIL_USER}")
    print(f"IMAP SERVER: {config.EMAIL_IMAP_SERVER}")
    
    if not config.EMAIL_USER or not config.EMAIL_PASS:
        print("Erro: EMAIL_USER ou EMAIL_PASS nao estao configurados no .env")
        return
        
    try:
        print("Conectando via SSL...")
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_SERVER, 993)
        print("Tentando realizar login...")
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        print("[OK] Login efetuado com sucesso!")
        
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        if status == "OK" and messages[0]:
            num_msgs = len(messages[0].split())
            print(f"[OK] Conexao IMAP operacional! Encontradas {num_msgs} mensagens nao lidas na Inbox.")
        else:
            print("[OK] Conexao IMAP operacional! Nenhuma mensagem nao lida na Inbox.")
            
        mail.close()
        mail.logout()
        print("=== TESTE CONCLUIDO ===")
    except Exception as e:
        print(f"[ERRO] ERRO NA CONEXAO IMAP: {e}")

if __name__ == "__main__":
    testar()
