import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.utils import parseaddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import config
from config import EMAILS_SAIDA_DIR, DOMINIOS_AUTORIZADOS, ASSUNTO_PALAVRAS_CHAVE
import parser_agent

def decodificar_header(text):
    """Decodifica cabeçalhos de e-mail encodados (como assunto ou remetente)."""
    if not text:
        return ""
    decoded = decode_header(text)
    parts = []
    for val, encoding in decoded:
        if isinstance(val, bytes):
            try:
                parts.append(val.decode(encoding or "utf-8", errors="ignore"))
            except Exception:
                parts.append(val.decode("latin1", errors="ignore"))
        else:
            parts.append(val)
    return "".join(parts)

def obter_dados_corpo_e_anexo(msg):
    """
    Percorre as partes do e-mail para extrair o texto plano,
    o corpo HTML e baixar eventuais anexos em Excel (.xlsx).
    """
    body_text = ""
    body_html = ""
    attachment_path = None
    
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))
        
        # Verifica se é anexo
        if "attachment" in content_disposition:
            filename = part.get_filename()
            if filename:
                filename = decodificar_header(filename)
                if filename.endswith(".xlsx") or filename.endswith(".xls"):
                    # Salva temporariamente o Excel na pasta de simulação/downloads
                    local_path = os.path.join(config.SIMULACAO_DIR, filename)
                    try:
                        with open(local_path, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        attachment_path = local_path
                        print(f"[Email Parser] Anexo de Excel baixado com sucesso: {filename}")
                    except Exception as e:
                        print(f"[Email Parser] Erro ao salvar anexo {filename}: {e}")
        else:
            # É corpo do e-mail
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body_text = part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    pass
            elif content_type == "text/html":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body_html = part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    pass
                    
    return body_text, body_html, attachment_path

def verificar_remetente_autorizado(sender):
    """Verifica se o remetente pertence a um domínio autorizado."""
    sender_lower = sender.lower().strip()
    for dominio in DOMINIOS_AUTORIZADOS:
        if sender_lower.endswith(dominio):
            return True
    return False

def verificar_assunto_relevante(subject):
    """Verifica se o assunto contém palavras-chave de negociação."""
    subject_lower = subject.lower().strip()
    for palavra in ASSUNTO_PALAVRAS_CHAVE:
        if palavra in subject_lower:
            return True
    return False

def buscar_novos_emails():
    """
    Conecta via IMAP SSL ao servidor de e-mail real, busca e-mails UNSEEN (não lidos),
    filtra remetente/assunto e extrai a lista de alunos.
    """
    emails_encontrados = []
    
    if not config.EMAIL_IMAP_USER or not config.EMAIL_IMAP_PASS:
        print("[Email Monitor] Erro: EMAIL_IMAP_USER ou EMAIL_IMAP_PASS não configurados no arquivo .env!")
        return emails_encontrados

    try:
        print(f"[Email Monitor] Conectando ao servidor IMAP: {config.EMAIL_IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_SERVER, 993)
        mail.login(config.EMAIL_IMAP_USER, config.EMAIL_IMAP_PASS)
        mail.select("inbox")
        
        # Busca todas as mensagens não lidas
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print("[Email Monitor] Nenhuma nova mensagem não lida encontrada.")
            mail.close()
            mail.logout()
            return emails_encontrados
            
        # Pega a lista completa de IDs (ordem crescente: mais antigos primeiro)
        todas_mensagens = messages[0].split()
        
        # Filtramos para ler apenas os cabeçalhos das 10 mensagens não lidas mais recentes (fim da lista)
        msg_ids = todas_mensagens[-10:]
        print(f"[Email Monitor] Analisando cabeçalhos das {len(msg_ids)} mensagens não lidas mais recentes...")
        
        for num in msg_ids:
            # 1. Obtém apenas o cabeçalho sem marcar o e-mail como lido (PEEK)
            status, data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])")
            if status != "OK" or not data or not data[0]:
                continue
                
            raw_header = data[0][1]
            msg_header = email.message_from_bytes(raw_header)
            
            # Extrai e decodifica assunto, remetente e Message-ID
            subject = decodificar_header(msg_header["Subject"])
            sender_full = decodificar_header(msg_header["From"])
            _, sender_email = parseaddr(sender_full)
            message_id = msg_header["Message-ID"] or f"sem-id-{datetime.now().timestamp()}"
            
            # --- Aplicação rápida das regras de filtragem ---
            if not verificar_remetente_autorizado(sender_email):
                # Silenciosamente ignora remetentes não autorizados para manter o log limpo
                continue
                
            if not verificar_assunto_relevante(subject):
                # Silenciosamente ignora assuntos não relevantes
                continue
                
            # Se passou nos filtros, agora marcamos o e-mail como lido e baixamos o corpo completo
            print(f"[Email Monitor] Encontrado e-mail relevante! Processando: '{subject}' de <{sender_email}>")
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                continue
                
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extrai corpo e anexos
            body_text, body_html, anexo_excel = obter_dados_corpo_e_anexo(msg)
            
            alunos = []
            
            # 1. Tenta extrair do Excel anexado
            if anexo_excel and os.path.exists(anexo_excel):
                alunos = parser_agent.parse_excel(anexo_excel)
                # Remove o arquivo temporário de anexo após a extração
                try:
                    os.remove(anexo_excel)
                except Exception:
                    pass
                    
            # 2. Tenta extrair da tabela HTML do corpo
            if not alunos and body_html:
                alunos = parser_agent.parse_html_table(body_html)
                
            # 3. Tenta extrair do texto simples
            if not alunos and body_text:
                alunos = parser_agent.parse_plain_text(body_text)
                
            print(f"[Email Parser] Sucesso! Extraídos {len(alunos)} alunos do e-mail.")
            
            # Adiciona na lista para processamento
            emails_encontrados.append({
                "id": message_id,
                "sender": sender_email,
                "subject": subject,
                "alunos": alunos,
                "original_uid": num
            })
            
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"[Erro Email Monitor] Falha ao conectar ou buscar e-mails via IMAP: {e}")
        
    return emails_encontrados

def conectar_smtp():
    """Tenta conectar ao SMTP usando SSL (465) e, se falhar, tenta TLS (587)."""
    try:
        # Tenta primeira opção: SSL na porta 465
        print(f"[SMTP] Tentando conexao via SSL (Porta 465) no servidor {config.EMAIL_SMTP_SERVER}...")
        server = smtplib.SMTP_SSL(config.EMAIL_SMTP_SERVER, 465, timeout=10)
        return server
    except Exception as e_ssl:
        print(f"[SMTP] Falha na porta 465: {e_ssl}. Tentando TLS (Porta 587)...")
        try:
            # Tenta segunda opção: TLS na porta 587
            server = smtplib.SMTP(config.EMAIL_SMTP_SERVER, 587, timeout=10)
            server.starttls()
            return server
        except Exception as e_tls:
            print(f"[SMTP] Falha na porta 587: {e_tls}")
            raise ConnectionError(f"Nao foi possivel conectar ao servidor SMTP nas portas 465 e 587: {e_ssl} / {e_tls}")

def enviar_resposta_recebimento(lote_id, destinatario, assunto_original, alunos_nomes, message_id=None):
    """
    Envia o e-mail de resposta inicial (Confirmação de recebimento) respondendo na mesma conversa (Thread).
    """
    if not config.EMAIL_SMTP_USER or not config.EMAIL_SMTP_PASS:
        print("[Email Resposta] Erro: EMAIL_SMTP_USER ou EMAIL_SMTP_PASS não configurados no arquivo .env!")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_SMTP_USER
        msg["To"] = destinatario
        msg["Subject"] = f"Re: {assunto_original}"
        
        # Threading: Configura cabeçalhos para manter na mesma conversa de e-mail
        if message_id:
            msg["In-Reply-To"] = message_id
            msg["References"] = message_id
            
        lista_nomes = ", ".join(alunos_nomes)
        corpo = (
            f"Olá,\n\n"
            f"Confirmamos o recebimento da solicitação de negociação para o(s) seguinte(s) aluno(s):\n"
            f"-> {lista_nomes}\n\n"
            f"Os acionamentos via WhatsApp já foram iniciados. Assim que concluídos, "
            f"retornaremos nesta mesma conversa com o resultado das negociações.\n\n"
            f"Atenciosamente,\n"
            f"Equipe Backoffice Grupo DDM\n"
        )
        
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        
        # Conecta no SMTP
        server = conectar_smtp()
        server.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASS)
        server.sendmail(config.EMAIL_SMTP_USER, [destinatario], msg.as_string())
        server.quit()
        
        print(f"[Email Resposta] E-mail de confirmação enviado com sucesso para {destinatario} (Lote: {lote_id})")
        
    except Exception as e:
        print(f"[Erro Email Resposta] Falha ao enviar resposta de recebimento: {e}")

def enviar_resposta_resultado_final(lote_id, destinatario, assunto_original, relatorio_alunos, message_id=None):
    """
    Envia o e-mail final com o relatório de quem formalizou e quem não formalizou (Threaded).
    """
    if not config.EMAIL_SMTP_USER or not config.EMAIL_SMTP_PASS:
        print("[Email Resposta Final] Erro: EMAIL_SMTP_USER ou EMAIL_SMTP_PASS não configurados no arquivo .env!")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_SMTP_USER
        msg["To"] = destinatario
        msg["Subject"] = f"Re: {assunto_original} - RETORNO FINAL"
        
        if message_id:
            msg["In-Reply-To"] = message_id
            msg["References"] = message_id
            
        linhas_alunos = []
        total = len(relatorio_alunos)
        sucessos = 0
        
        for aluno in relatorio_alunos:
            status_traduzido = "Pendente"
            if aluno['status'] == 'acordo_fechado':
                status_traduzido = "[SUCESSO] Acordo Formalizado"
                sucessos += 1
            elif aluno['status'] == 'sem_retorno':
                status_traduzido = "[SEM RETORNO] Mensagem lida e ignorada"
            elif aluno['status'] == 'erro':
                status_traduzido = "[ERRO] Telefone invalido ou inexistente"
                
            ra_cpf_str = f" ({aluno['ra_cpf']})" if aluno['ra_cpf'] else ""
            linhas_alunos.append(f"- {aluno['nome']}{ra_cpf_str}: {status_traduzido}")
            
        lista_detalhada = "\n".join(linhas_alunos)
        
        corpo = (
            f"Olá,\n\n"
            f"Concluímos os contatos referentes ao lote solicitado de negociações (Lote ID: {lote_id}).\n"
            f"Abaixo segue o relatório final detalhado dos retornos:\n\n"
            f"{lista_detalhada}\n\n"
            f"Resumo: {sucessos} de {total} alunos formalizaram acordo.\n\n"
            f"Qualquer dúvida, estamos à disposição.\n\n"
            f"Atenciosamente,\n"
            f"Equipe Backoffice Grupo DDM\n"
        )
        
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        
        # Conecta no SMTP
        server = conectar_smtp()
        server.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASS)
        server.sendmail(config.EMAIL_SMTP_USER, [destinatario], msg.as_string())
        server.quit()
        
        print(f"[Email Resposta Final] E-mail de relatório final enviado para {destinatario} (Lote: {lote_id})")
        
    except Exception as e:
        print(f"[Erro Email Resposta Final] Falha ao enviar resposta de relatório final: {e}")
