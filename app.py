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
