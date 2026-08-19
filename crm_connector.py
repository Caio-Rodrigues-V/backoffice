import os
import requests
import json
import datetime
from supabase import create_client, Client, ClientOptions
import config

_supabase_client = None

def get_supabase_client() -> Client:
    """
    Inicializa e retorna o cliente de conexão do Supabase (CRM).
    """
    global _supabase_client
    if _supabase_client is None:
        url = config.CRM_SUPABASE_URL
        key = config.CRM_SUPABASE_KEY
        if not url or not key:
            print("[CRM Connector] AVISO: CRM_SUPABASE_URL ou CRM_SUPABASE_KEY não configurados no .env")
            return None
        options = ClientOptions(schema="wacrm")
        _supabase_client = create_client(url, key, options=options)
    return _supabase_client

def resolver_account_id(supabase: Client, user_id: str) -> str:
    """
    Busca o account_id vinculado ao perfil do admin no CRM.
    """
    try:
        res = supabase.table("profiles").select("account_id").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]["account_id"]
        raise ValueError(f"Perfil não encontrado para o user_id: {user_id}")
    except Exception as e:
        print(f"[CRM Connector] Erro ao resolver account_id: {e}")
        raise e

def sanitizar_telefone(telefone: str) -> str:
    """
    Deixa apenas números no telefone para o padrão E.164.
    """
    return "".join(c for c in telefone if c.isdigit())

def criar_ou_obter_contato(supabase: Client, user_id: str, account_id: str, nome: str, telefone: str) -> str:
    """
    Verifica se o contato já existe no CRM pelo telefone. Se não, cria um novo.
    """
    telefone_limpo = sanitizar_telefone(telefone)
    
    # Busca contato existente por phone_normalized
    res = supabase.table("contacts").select("id").eq("phone_normalized", telefone_limpo).eq("account_id", account_id).execute()
    if res.data:
        print(f"[CRM Connector] Contato existente encontrado: {nome} ({telefone_limpo})")
        return res.data[0]["id"]
        
    # Cria novo contato
    contato_data = {
        "user_id": user_id,
        "account_id": account_id,
        "phone": telefone_limpo,
        "name": nome,
        "company": "Grupo DDM Backoffice"
    }
    try:
        insert_res = supabase.table("contacts").insert(contato_data).execute()
        if insert_res.data:
            print(f"[CRM Connector] Novo contato criado: {nome} ({telefone_limpo})")
            return insert_res.data[0]["id"]
    except Exception as e:
        err_msg = str(e)
        if "23505" in err_msg or "duplicate key" in err_msg:
            print(f"[CRM Connector] Contato {nome} ({telefone_limpo}) já existe (concorrência). Recuperando ID...")
            res_retry = supabase.table("contacts").select("id").eq("phone_normalized", telefone_limpo).eq("account_id", account_id).execute()
            if res_retry.data:
                return res_retry.data[0]["id"]
        raise e
        
    raise ValueError("Falha ao criar contato no Supabase.")

def criar_ou_obter_conversa(supabase: Client, user_id: str, account_id: str, contact_id: str) -> str:
    """
    Garante que exista uma conversa (chat thread) ativa para o contato no inbox.
    """
    res = supabase.table("conversations").select("id").eq("contact_id", contact_id).eq("account_id", account_id).execute()
    if res.data:
        return res.data[0]["id"]
        
    conv_data = {
        "user_id": user_id,
        "account_id": account_id,
        "contact_id": contact_id,
        "status": "open",
        "unread_count": 0
    }
    insert_res = supabase.table("conversations").insert(conv_data).execute()
    if insert_res.data:
        return insert_res.data[0]["id"]
        
    raise ValueError("Falha ao criar conversa no Supabase.")

def criar_negocio_no_funil(supabase: Client, user_id: str, account_id: str, contact_id: str, conversation_id: str, nome_aluno: str, valor: float, ra_cpf: str):
    """
    Cria ou atualiza um card de negócio (Deal) no Funil de Vendas do CRM.
    Evita duplicados gerados pela trigger de auto-criação do Supabase.
    """
    deal_data = {
        "user_id": user_id,
        "account_id": account_id,
        "pipeline_id": config.CRM_PIPELINE_ID,
        "stage_id": config.CRM_STAGE_ID,
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "title": f"Cobrança - {nome_aluno}",
        "value": float(valor) if valor else 0.0,
        "notes": f"Aluno cadastrado via Backoffice (Leitor de E-mails)\nRA/CPF: {ra_cpf}",
        "status": "open"
    }
    
    try:
        # Verifica se o Supabase já auto-criou um deal aberto para este contato
        res = supabase.table("deals").select("id").eq("contact_id", contact_id).eq("status", "open").execute()
        if res.data:
            deal_id = res.data[0]["id"]
            supabase.table("deals").update(deal_data).eq("id", deal_id).execute()
            print(f"[CRM Connector] Card de negócio existente ID {deal_id} atualizado para '{nome_aluno}' no valor de R$ {valor}")
        else:
            supabase.table("deals").insert(deal_data).execute()
            print(f"[CRM Connector] Card de negócio criado para '{nome_aluno}' no valor de R$ {valor}")
    except Exception as e:
        print(f"[CRM Connector] Erro ao criar/atualizar card de negócio: {e}")
        # Tenta inserção direta caso a busca falhe
        try:
            supabase.table("deals").insert(deal_data).execute()
        except Exception:
            pass

def enviar_mensagem_whatsapp(supabase: Client, user_id: str, account_id: str, conversation_id: str, telefone: str, mensagem: str) -> bool:
    """
    Lê a configuração ativa de WhatsApp do CRM e faz o disparo real (WAHA ou Meta).
    """
    try:
        telefone_limpo = sanitizar_telefone(telefone)
        success = False
        message_id = f"msg_{int(datetime.datetime.now().timestamp())}"
        
        if config.SIMULAR_WHATSAPP:
            print(f"[CRM Connector] [SIMULADO] WhatsApp simulado para {telefone_limpo}: {mensagem}")
            success = True
            message_id = f"sim_{int(datetime.datetime.now().timestamp())}"
        else:
            # Busca a configuração de WhatsApp atrelada à conta
            res = supabase.table("whatsapp_config").select("*").eq("account_id", account_id).execute()
            if not res.data:
                print("[CRM Connector] Erro: Nenhuma configuração de WhatsApp ativa encontrada no CRM.")
                return False
                
            config_whats = res.data[0]
            provider = config_whats.get("provider", "meta")
            
            # 1. DISPARO VIA WAHA (WhatsApp Web API)
            if provider == "waha":
                waha_url = config_whats.get("waha_url")
                waha_session = config_whats.get("waha_session")
                waha_key = config_whats.get("waha_api_key")
                
                if not waha_url or not waha_session:
                    print("[CRM Connector] Erro: Dados do WAHA incompletos no banco do CRM.")
                    return False
                    
                headers = {"Content-Type": "application/json"}
                if waha_key:
                    headers["X-Api-Key"] = waha_key
                    headers["Authorization"] = f"Bearer {waha_key}"
                    
                chat_id = f"{telefone_limpo}@c.us"
                payload = {
                    "chatId": chat_id,
                    "text": mensagem,
                    "session": waha_session
                }
                
                url_envio = f"{waha_url.rstrip('/')}/api/sendText"
                print(f"[CRM Connector] Disparando via WAHA para {chat_id} com payload: {payload}")
                response = requests.post(url_envio, json=payload, headers=headers, timeout=15)
                if response.status_code != 200 and response.status_code != 201:
                    print(f"[CRM Connector] WAHA Error Response ({response.status_code}): {response.text}")
                response.raise_for_status()
                
                waha_res = response.json()
                message_id = waha_res.get("id", message_id)
                success = True
                print(f"[CRM Connector] Mensagem entregue com sucesso via WAHA.")
                
            # 2. DISPARO VIA META (WhatsApp Cloud API Oficial)
            elif provider == "meta":
                phone_number_id = config_whats.get("phone_number_id")
                token = config_whats.get("access_token")
                
                if not phone_number_id or not token:
                    print("[CRM Connector] Erro: Dados do Meta Cloud API incompletos no banco do CRM.")
                    return False
                    
                url_envio = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": f"+{telefone_limpo}",
                    "type": "text",
                    "text": {"body": mensagem}
                }
                
                print(f"[CRM Connector] Disparando via Meta API para {telefone_limpo}...")
                response = requests.post(url_envio, json=payload, headers=headers, timeout=15)
                response.raise_for_status()
                
                meta_res = response.json()
                if "messages" in meta_res:
                    message_id = meta_res["messages"][0].get("id", message_id)
                    success = True
                print(f"[CRM Connector] Mensagem entregue com sucesso via Meta API.")
                
        # 3. GRAVA NO INBOX DO CRM (Tabela messages)
        if success:
            msg_data = {
                "conversation_id": conversation_id,
                "sender_type": "bot",
                "content_type": "text",
                "content_text": mensagem,
                "message_id": message_id,
                "status": "sent"
            }
            supabase.table("messages").insert(msg_data).execute()
            
            # Atualiza o status da conversa
            conv_update = {
                "last_message_text": mensagem,
                "last_message_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            supabase.table("conversations").update(conv_update).eq("id", conversation_id).execute()
            print("[CRM Connector] Conversa e histórico de mensagens atualizados no CRM.")
            return True
            
        return False
    except Exception as e:
        print(f"[CRM Connector] Falha ao disparar ou registrar mensagem: {e}")
        return False

def verificar_status_aluno_no_crm(telefone: str) -> str:
    """
    Busca o status do negócio (deal) do aluno no CRM pelo telefone dele.
    Retorna:
    - 'acordo_fechado' se o status for 'won' ou se o deal estiver na etapa de fechamento.
    - 'sem_retorno' se o status for 'lost'.
    - 'contatando' se continuar ativo/em andamento.
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return "contatando"
            
        telefone_limpo = sanitizar_telefone(telefone)
        
        # 1. Busca o ID do contato pelo telefone usando phone_normalized
        res_contato = supabase.table("contacts").select("id").eq("phone_normalized", telefone_limpo).execute()
        if not res_contato.data:
            print(f"[CRM Connector] Contato com telefone {telefone_limpo} não encontrado.")
            return "contatando"
            
        contact_id = res_contato.data[0]["id"]
        
        # 2. Busca os negócios (deals) vinculados ao contato
        res_deal = supabase.table("deals").select("status, stage_id").eq("contact_id", contact_id).execute()
        
        if res_deal.data:
            # Pega o negócio mais recente (último inserido)
            deal = res_deal.data[-1]
            status = deal.get("status", "active")
            stage_id = deal.get("stage_id")
            
            # Se o status do negócio for 'won' ou estiver na etapa "Fechado" (oj) / "Ganho" (MultiVix)
            if status == "won" or stage_id in ["16f36065-2831-4aab-9380-6141d2bc88e9", "9fbb6384-f47a-4fb2-bdcd-5b1072c71ea1"]:
                return "acordo_fechado"
            elif status == "lost":
                return "sem_retorno"
                
        return "contatando"
    except Exception as e:
        print(f"[CRM Connector] Erro ao verificar status no CRM para {telefone}: {e}")
        return "contatando"

def processar_aluno_no_crm(nome: str, telefone: str, ra_cpf: str, valor: float, mensagem_inicial: str) -> bool:
    """
    Função principal que gerencia o fluxo completo de cadastro e disparo do aluno no CRM.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("[CRM Connector] Abortando: Supabase do CRM não conectado.")
        return False
        
    try:
        user_id = config.CRM_ADMIN_USER_ID
        account_id = resolver_account_id(supabase, user_id)
        
        # 1. Cria ou recupera o Contato
        contact_id = criar_ou_obter_contato(supabase, user_id, account_id, nome, telefone)
        
        # 2. Cria ou recupera a Conversa
        conversation_id = criar_ou_obter_conversa(supabase, user_id, account_id, contact_id)
        
        # 3. Cria o Card no Funil de Vendas (Deal)
        criar_negocio_no_funil(supabase, user_id, account_id, contact_id, conversation_id, nome, valor, ra_cpf)
        
        # 4. Dispara a mensagem via WhatsApp e adiciona ao Inbox
        disparo_ok = enviar_mensagem_whatsapp(supabase, user_id, account_id, conversation_id, telefone, mensagem_inicial)
        
        return disparo_ok
    except Exception as e:
        print(f"[CRM Connector] Falha ao processar aluno no CRM: {e}")
        return False
