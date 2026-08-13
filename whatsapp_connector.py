import os
import requests
from datetime import datetime
import db_manager
import config
from config import WHATSAPP_SIMULADO_DIR
import crm_connector

def disparar_mensagem_inicial(aluno_id, nome, ra_cpf, telefone):
    """
    Envia (transfere) os dados do aluno para o CRM iniciar a abordagem.
    """
    try:
        # Prepara a mensagem inicial
        mensagem = config.CRM_MENSAGEM_INICIAL.format(nome=nome)
        
        print(f"[CRM Ponte] Integrando e iniciando abordagem para o aluno {nome} no CRM...")
        sucesso = crm_connector.processar_aluno_no_crm(
            nome=nome,
            telefone=telefone,
            ra_cpf=ra_cpf,
            valor=0.0,  # Valor default (pode ser ajustado se extraído futuramente)
            mensagem_inicial=mensagem
        )
        
        if sucesso:
            db_manager.atualizar_status_aluno(aluno_id, "contatando")
            print(f"[CRM Ponte] Aluno {nome} enviado e abordagem iniciada com sucesso.")
            return True
        else:
            db_manager.atualizar_status_aluno(aluno_id, "erro")
            print(f"[CRM Ponte] Falha no fluxo do CRM para o aluno {nome}.")
            return False
            
    except Exception as e:
        print(f"[Erro CRM Ponte] Falha ao enviar dados do aluno {nome} para o CRM: {e}")
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
