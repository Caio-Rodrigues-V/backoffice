import os
import db_manager
import email_connector
import whatsapp_connector

def inicializar_sistema():
    """Garante que o banco de dados esteja criado e pronto."""
    db_manager.init_db()
    print("[Orquestrador] Sistema inicializado e banco de dados verificado.")

def reprocessar_alunos_com_erro():
    """
    Busca alunos que ficaram com status de 'erro' ou 'pendente' no banco local e tenta reenviar para o CRM.
    """
    print("[Orquestrador] Verificando se ha alunos que falharam anteriormente para reprocessar...")
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nome, ra_cpf, telefone FROM alunos_negociacao WHERE status_whatsapp IN ('erro', 'pendente')"
    )
    alunos_falhos = cursor.fetchall()
    conn.close()
    
    if alunos_falhos:
        print(f"[Orquestrador] Re-processando {len(alunos_falhos)} alunos que falharam anteriormente...")
        for aluno_id, nome, ra_cpf, telefone in alunos_falhos:
            whatsapp_connector.disparar_mensagem_inicial(
                aluno_id=aluno_id,
                nome=nome,
                ra_cpf=ra_cpf,
                telefone=telefone
            )

def executar_ciclo_leitura():
    """
    Varre a caixa de e-mails, filtra, cadastra no banco,
    envia resposta de recebimento e inicia disparos de WhatsApp.
    """
    print("\n--- INICIANDO CICLO DE LEITURA DE NOVOS EMAILS ---")
    
    # 0. Reprocessa alunos com falhas anteriores
    reprocessar_alunos_com_erro()
    
    # 1. Busca novos e-mails na pasta de entrada
    novos_emails = email_connector.buscar_novos_emails()
    
    for email in novos_emails:
        alunos = email["alunos"]
        
        if not alunos:
            print(f"[Orquestrador] E-mail '{email['subject']}' não possui alunos a processar. Removendo...")
            if os.path.exists(email["arquivo_origem"]):
                os.remove(email["arquivo_origem"])
            continue
            
        # 2. Cria o lote de controle no banco de dados
        lote_id = db_manager.criar_lote(email["sender"], email["subject"], email.get("id"))
        print(f"[Orquestrador] Criado Lote ID {lote_id} para o e-mail '{email['subject']}'")
        
        # 3. Cadastra os alunos vinculados a esse lote
        for aluno in alunos:
            db_manager.adicionar_aluno(
                lote_id=lote_id,
                nome=aluno["nome"],
                ra_cpf=aluno["ra_cpf"],
                telefone=aluno["telefone"]
            )
            
        # 4. Envia o e-mail de resposta inicial (Confirmação de recebimento)
        nomes_alunos = [aluno["nome"] for aluno in alunos]
        email_connector.enviar_resposta_recebimento(
            lote_id=lote_id,
            destinatario=email["sender"],
            assunto_original=email["subject"],
            alunos_nomes=nomes_alunos,
            message_id=email.get("id")
        )
        db_manager.marcar_confirmacao_enviada(lote_id)
        
        # 5. Recupera os alunos cadastrados com seus IDs gerados para disparar o WhatsApp
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nome, ra_cpf, telefone FROM alunos_negociacao WHERE lote_id = ?",
            (lote_id,)
        )
        alunos_cadastrados = cursor.fetchall()
        conn.close()
        
        # 6. Dispara a mensagem inicial de WhatsApp para cada um
        for aluno_id, nome, ra_cpf, telefone in alunos_cadastrados:
            whatsapp_connector.disparar_mensagem_inicial(
                aluno_id=aluno_id,
                nome=nome,
                ra_cpf=ra_cpf,
                telefone=telefone
            )
            
        # 7. Remove o e-mail de origem para não ser reprocessado na próxima leitura (apenas no simulador)
        if "arquivo_origem" in email and os.path.exists(email["arquivo_origem"]):
            os.remove(email["arquivo_origem"])
            print(f"[Orquestrador] E-mail origem {os.path.basename(email['arquivo_origem'])} processado e arquivado.")

def sincronizar_status_crm():
    """
    Busca alunos que estão com status_whatsapp = 'contatando' no SQLite local,
    consulta o status deles no CRM (Supabase) e atualiza o SQLite local.
    """
    import crm_connector
    print("[Orquestrador] Sincronizando status dos atendimentos ativos com o CRM...")
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, telefone FROM alunos_negociacao WHERE status_whatsapp = 'contatando'")
    alunos = cursor.fetchall()
    conn.close()
    
    if not alunos:
        print("[Orquestrador] Nenhum atendimento ativo em andamento para atualizar.")
        return
        
    for aluno_id, telefone in alunos:
        novo_status = crm_connector.verificar_status_aluno_no_crm(telefone)
        if novo_status != "contatando":
            db_manager.atualizar_status_aluno(aluno_id, novo_status)
            print(f"[Orquestrador] Aluno ID {aluno_id} atualizado para status '{novo_status}' no banco local.")

def executar_ciclo_retorno():
    """
    Verifica se há lotes onde todos os alunos já concluíram o atendimento no WhatsApp
    e envia o e-mail final de retorno para o cliente que solicitou.
    """
    print("\n--- INICIANDO CICLO DE MONITORAMENTO DE RETORNOS ---")
    
    # 1. Sincroniza os status ativos com o CRM
    sincronizar_status_crm()
    
    # 2. Verifica quais lotes já terminaram e precisam de e-mail de retorno
    lotes_concluidos = db_manager.obter_lotes_pendentes_retorno()
    
    if not lotes_concluidos:
        print("[Orquestrador] Nenhum lote finalizado pendente de retorno.")
        return
        
    for lote in lotes_concluidos:
        lote_id = lote["id"]
        sender = lote["sender"]
        subject = lote["subject"]
        
        print(f"[Orquestrador] Lote ID {lote_id} concluído! Compilando relatório...")
        
        # 2. Obtém o status de todos os alunos do lote
        relatorio = db_manager.obter_relatorio_lote(lote_id)
        
        # 3. Envia o e-mail de retorno final
        email_connector.enviar_resposta_resultado_final(
            lote_id=lote_id,
            destinatario=sender,
            assunto_original=subject,
            relatorio_alunos=relatorio,
            message_id=lote.get("message_id")
        )
        
        # 4. Conclui o lote para não enviar o retorno novamente
        db_manager.concluir_lote(lote_id)
        print(f"[Orquestrador] Lote ID {lote_id} arquivado com sucesso.")
