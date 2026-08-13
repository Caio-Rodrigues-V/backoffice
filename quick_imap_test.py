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
        if status != "OK" or not messages[0]:
            print("[OK] Nenhuma mensagem nao lida na Inbox.")
            mail.close()
            mail.logout()
            return
            
        todas = messages[0].split()
        print(f"Total de nao lidas: {len(todas)}")
        # Pega as 50 mais recentes
        msg_ids = todas[-50:]
        
        from email.utils import parseaddr
        import email
        
        encontrados = 0
        for num in msg_ids:
            # Pega apenas os cabecalhos sem marcar como lido
            status, data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])")
            if status != "OK" or not data or not data[0]:
                continue
                
            raw_header = data[0][1]
            msg = email.message_from_bytes(raw_header)
            
            # Decodifica assunto
            from email.header import decode_header
            def decodificar(h):
                if not h: return ""
                parts = decode_header(h)
                res = []
                for val, charset in parts:
                    if isinstance(val, bytes):
                        res.append(val.decode(charset or "utf-8", errors="ignore"))
                    else:
                        res.append(str(val))
                return "".join(res)
                
            subject = decodificar(msg["Subject"])
            print(f"Mensagem ID {num.decode()}: Assunto='{subject}'")
            
            # Verifica se tem 'negociacao' ou 'cobranca' ou 'inaptos'
            subj_lower = subject.lower()
            if any(k in subj_lower for k in ["negociacao", "negociação", "cobranca", "cobrança", "inaptos"]):
                print(f"--> [MATCH] Encontrada mensagem relevante! ID: {num.decode()} | Assunto: {subject}")
                encontrados += 1
                
        print(f"Total de matches relevantes nas 50 mais recentes: {encontrados}")
        mail.close()
        mail.logout()
        print("=== TESTE CONCLUIDO ===")
    except Exception as e:
        print(f"[ERRO] ERRO NA CONEXAO IMAP: {e}")

if __name__ == "__main__":
    testar()
