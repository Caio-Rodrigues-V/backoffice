import os
import requests
from datetime import datetime
import db_manager
import config
from config import WHATSAPP_SIMULADO_DIR

def disparar_mensagem_inicial(aluno_id, nome, ra_cpf, telefone):
    """
    Envia (transfere) os dados do aluno para o robô da GoGenier iniciar a abordagem.
    Pode rodar em modo real (HTTP POST) ou em modo simulado.
    """
    try:
        # Prepara a carga de dados (payload) esperada pelo robô da GoGenier
        payload = {
            "aluno_id": aluno_id,
            "nome": nome,
            "ra_cpf": ra_cpf,
            "telefone": telefone,
            "origem": "Grupo DDM Backoffice"
        }
        
        # --- INTEGRAÇÃO REAL COM GOGENIER ---
        if not config.SIMULAR_GOGENIER:
            url = config.GOGENIER_WEBHOOK_URL
            headers = {
                "Content-Type": "application/json"
            }
            # Adiciona token de autenticação se estiver configurado
            if config.GOGENIER_API_KEY:
                headers["Authorization"] = f"Bearer {config.GOGENIER_API_KEY}"
                
            print(f"[GoGenier Ponte] Enviando dados do aluno {nome} para {url}...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"[GoGenier Ponte] Aluno {nome} enviado com sucesso para a GoGenier.")
            
        else:
            # --- COMPORTAMENTO SIMULADO (LOCAL) ---
            log_file = os.path.join(WHATSAPP_SIMULADO_DIR, f"aluno_{aluno_id}_whats.log")
            now = datetime.now().isoformat()
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"--- ENVIADO PARA GOGENIER EM {now} ---\n")
                f.write(f"Payload: {payload}\n")
                f.write("-----------------------------------------\n\n")
                
            print(f"[GoGenier Simulado] Aluno {nome} (ID: {aluno_id}) enviado para fila simulada.")
        
        # Atualiza o status do aluno no banco de dados para 'contatando' (indicando que foi enviado para a GoGenier)
        db_manager.atualizar_status_aluno(aluno_id, "contatando")
        return True
    except Exception as e:
        print(f"[Erro GoGenier Ponte] Falha ao enviar dados do aluno {nome}: {e}")
        db_manager.atualizar_status_aluno(aluno_id, "erro")
        return False

def processar_resposta_webhook(aluno_id, status_retorno, detalhes_conversa=""):
    """
    Atualiza o banco de dados quando a GoGenier nos retorna o resultado da abordagem.
    Chamado pelo nosso servidor web (app.py) ao receber a requisição de retorno da GoGenier.
    """
    # Valida o status recebido e mapeia para o banco
    status_retorno = status_retorno.lower().strip()
    
    if status_retorno in ["acordo_fechado", "sucesso", "fechado"]:
        novo_status = "acordo_fechado"
    elif status_retorno in ["sem_retorno", "recusado", "ignorou"]:
        novo_status = "sem_retorno"
    elif status_retorno in ["erro", "invalido", "numero_invalido"]:
        novo_status = "erro"
    else:
        novo_status = "sem_retorno" # Default
        
    print(f"[GoGenier Webhook Retorno] Aluno ID {aluno_id} finalizou com status: {status_retorno} -> Banco: {novo_status}")
    
    # Atualiza no Banco de Dados
    db_manager.atualizar_status_aluno(aluno_id, novo_status)
    
    # Salva no log da conversa para auditoria
    log_file = os.path.join(WHATSAPP_SIMULADO_DIR, f"aluno_{aluno_id}_whats.log")
    now = datetime.now().isoformat()
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"--- RETORNO GOGENIER EM {now} ---\n")
        f.write(f"Status Retornado: {status_retorno}\n")
        f.write(f"Detalhes: {detalhes_conversa}\n")
        f.write(f"Status Final Banco: {novo_status}\n")
        f.write("-------------------------------------\n\n")
        
    return novo_status
