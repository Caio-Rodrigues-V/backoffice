from flask import Flask, render_template, jsonify, request
import os
import db_manager
import orchestrator
import whatsapp_connector
import config
import sys

app = Flask(__name__, template_folder='templates', static_folder='static')

# Garantindo que as tabelas estejam inicializadas
db_manager.init_db()

@app.route('/api/debug/python-path', methods=['GET'])
def debug_python_path():
    """Retorna o caminho exato do executável do Python rodando no servidor."""
    return jsonify({
        "python_executable": sys.executable,
        "cwd": os.getcwd()
    })

@app.route('/api/debug/test-smtp', methods=['GET'])
def debug_test_smtp():
    """Testa a conexão e credenciais do SMTP e retorna o resultado ou erro detalhado."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        import traceback
        
        if not config.EMAIL_USER or not config.EMAIL_PASS:
            return jsonify({"success": False, "message": "EMAIL_USER ou EMAIL_PASS não estão configurados no .env."}), 400
            
        msg = MIMEText("E-mail de diagnóstico de envio SMTP.")
        msg["From"] = config.EMAIL_USER
        msg["To"] = config.EMAIL_USER  # Envia para si mesmo
        msg["Subject"] = "Diagnóstico SMTP - Agente DDM"
        
        print("[Debug SMTP] Iniciando conexão com o SMTP...")
        server = smtplib.SMTP_SSL(config.EMAIL_SMTP_SERVER, 465, timeout=10)
        print("[Debug SMTP] Fazendo login...")
        server.login(config.EMAIL_USER, config.EMAIL_PASS)
        print("[Debug SMTP] Enviando e-mail...")
        server.sendmail(config.EMAIL_USER, [config.EMAIL_USER], msg.as_string())
        server.quit()
        
        return jsonify({"success": True, "message": "SMTP conectado e e-mail de teste enviado com sucesso!"})
    except Exception as e:
        return jsonify({
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/debug/run-build', methods=['GET'])
def debug_run_build():
    """Executa o build do Next.js do CRM ativando o ambiente virtual do Node do cPanel."""
    try:
        import subprocess
        import os
        import traceback
        
        # Localiza dinamicamente a pasta da versão do Node na pasta do nodevenv do omnichannel
        base_nodevenv = "/home/grpia/nodevenv/apps/omnichannel"
        if not os.path.exists(base_nodevenv):
            return jsonify({
                "success": False, 
                "message": f"Diretório do ambiente virtual do Node não encontrado: {base_nodevenv}. Certifique-se de que o aplicativo OMNI-CRM está criado no cPanel."
            }), 400
            
        versions = [d for d in os.listdir(base_nodevenv) if os.path.isdir(os.path.join(base_nodevenv, d)) and d.isdigit()]
        if not versions:
            return jsonify({
                "success": False,
                "message": f"Nenhuma versão do Node encontrada em {base_nodevenv}."
            }), 400
            
        node_version = versions[0]
        activate_path = f"{base_nodevenv}/{node_version}/bin/activate"
        
        print(f"[Debug Build] Iniciando build com Node v{node_version} em apps/omnichannel...")
        
        # Comando para ativar o virtualenv do Node e executar o npm run build
        cmd = f"source {activate_path} && cd /home/grpia/apps/omnichannel && npm run build"
        
        result = subprocess.run(
            cmd,
            shell=True,
            executable='/bin/bash',  # Necessário bash para suportar o comando 'source'
            capture_output=True,
            text=True,
            timeout=300  # Limite de 5 minutos para o build
        )
        
        return jsonify({
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/')
def index():
    """Serva a página principal do Dashboard."""
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas consolidadas para o topo do Dashboard."""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Total de lotes
        cursor.execute("SELECT COUNT(*) FROM lotes_email")
        total_lotes = cursor.fetchone()[0]
        
        # Total de alunos
        cursor.execute("SELECT COUNT(*) FROM alunos_negociacao")
        total_alunos = cursor.fetchone()[0]
        
        # Alunos por status
        cursor.execute("SELECT COUNT(*) FROM alunos_negociacao WHERE status_whatsapp = 'acordo_fechado'")
        total_acordos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alunos_negociacao WHERE status_whatsapp = 'sem_retorno'")
        total_sem_retorno = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alunos_negociacao WHERE status_whatsapp = 'erro'")
        total_erros = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alunos_negociacao WHERE status_whatsapp IN ('pendente', 'contatando')")
        total_ativos = cursor.fetchone()[0]
        
        # Taxa de conversão (acordos fechados / finalizados)
        total_finalizados = total_acordos + total_sem_retorno + total_erros
        taxa_conversao = round((total_acordos / total_finalizados) * 100, 1) if total_finalizados > 0 else 0.0
        
        conn.close()
        
        return jsonify({
            "total_lotes": total_lotes,
            "total_alunos": total_alunos,
            "total_acordos": total_acordos,
            "total_sem_retorno": total_sem_retorno,
            "total_erros": total_erros,
            "total_ativos": total_ativos,
            "taxa_conversao": taxa_conversao
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/lotes', methods=['GET'])
def get_lotes():
    """Retorna todos os lotes com seus respectivos alunos cadastrados."""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Busca os lotes por data decrescente (mais recentes primeiro)
        cursor.execute("SELECT id, sender, subject, received_at, confirmation_sent, status FROM lotes_email ORDER BY id DESC")
        lotes_raw = cursor.fetchall()
        
        lotes = []
        for id_lote, sender, subject, received_at, confirmation_sent, status in lotes_raw:
            # Busca os alunos vinculados a esse lote
            cursor.execute(
                "SELECT id, nome, ra_cpf, telefone, status_whatsapp, last_update FROM alunos_negociacao WHERE lote_id = ?",
                (id_lote,)
            )
            alunos_raw = cursor.fetchall()
            
            alunos = []
            for id_aluno, nome, ra_cpf, telefone, status_whats, last_update in alunos_raw:
                alunos.append({
                    "id": id_aluno,
                    "nome": nome,
                    "ra_cpf": ra_cpf,
                    "telefone": telefone,
                    "status_whatsapp": status_whats,
                    "last_update": last_update
                })
                
            lotes.append({
                "id": id_lote,
                "sender": sender,
                "subject": subject,
                "received_at": received_at,
                "confirmation_sent": bool(confirmation_sent),
                "status": status,
                "alunos": alunos
            })
            
        conn.close()
        return jsonify(lotes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/retorno', methods=['POST'])
def webhook_retorno():
    """
    Webhook que a GoGenier chama para nos notificar o resultado do contato com o aluno.
    Exemplo de payload esperado:
    {
        "aluno_id": 5,
        "status": "acordo_fechado",
        "detalhes": "Mensagem lida, parcelou em 3x via Pix"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Nenhum dado JSON recebido"}), 400
        
    aluno_id = data.get("aluno_id")
    status = data.get("status")
    detalhes = data.get("detalhes", "")
    
    if not aluno_id or not status:
        return jsonify({"success": False, "message": "Campos 'aluno_id' e 'status' são obrigatórios"}), 400
        
    try:
        # Processa a resposta e atualiza o banco
        novo_status = whatsapp_connector.processar_resposta_webhook(
            aluno_id=aluno_id,
            status_retorno=status,
            detalhes_conversa=detalhes
        )
        return jsonify({
            "success": True, 
            "message": "Status atualizado com sucesso", 
            "aluno_id": aluno_id, 
            "novo_status_banco": novo_status
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao processar: {str(e)}"}), 500

@app.route('/webhook/gogenier_mock', methods=['POST'])
def gogenier_mock():
    """
    Simulador da API da GoGenier. Apenas recebe os dados do aluno e loga no console.
    Permite validar a rota de saída.
    """
    data = request.get_json()
    print(f"\n[GoGenier MOCK Server] Recebeu solicitação para abordagem:")
    print(f"Payload: {data}")
    return jsonify({"success": True, "message": "Abordagem agendada com sucesso na GoGenier"}), 200

# --- ROTAS DE AÇÕES AUXILIARES PARA O TESTADOR WEB ---

@app.route('/api/acao/buscar-emails', methods=['POST'])
def acao_buscar_emails():
    """Força o orquestrador a buscar e-mails não lidos no Gmail."""
    try:
        print("\n[Dashboard Web] Acionando busca manual de e-mails...")
        orchestrator.executar_ciclo_leitura()
        return jsonify({"success": True, "message": "Ciclo de leitura executado com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/acao/enviar-retornos', methods=['POST'])
def acao_enviar_retornos():
    """Força o orquestrador a verificar lotes finalizados e enviar retornos."""
    try:
        print("\n[Dashboard Web] Acionando envio manual de retornos...")
        orchestrator.executar_ciclo_retorno()
        return jsonify({"success": True, "message": "Ciclo de envio de retornos executado com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/acao/simular-resposta', methods=['POST'])
def acao_simular_resposta():
    """Simula o retorno de um aluno via GoGenier (facilita testar pelo Dashboard)."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Payload inválido"}), 400
        
    aluno_id = data.get("aluno_id")
    resposta = data.get("resposta") # 'acordo_fechado', 'sem_retorno', 'erro'
    
    if not aluno_id or not resposta:
        return jsonify({"success": False, "message": "Campos obrigatórios ausentes"}), 400
        
    try:
        whatsapp_connector.processar_resposta_webhook(
            aluno_id=aluno_id,
            status_retorno=resposta,
            detalhes_conversa="Simulação via Painel Web"
        )
        return jsonify({"success": True, "message": "Simulação gravada"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    # Roda localmente na porta 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
