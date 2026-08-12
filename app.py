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

@app.route('/api/debug/find-all-node', methods=['GET'])
def find_all_node():
    """Varre os diretórios de sistema da VPS para localizar todas as versões do Node instaladas."""
    try:
        import os
        results = []
        # Busca executáveis 'node' em locais de sistema do cPanel
        search_paths = ["/opt", "/usr/local"]
        for path in search_paths:
            if os.path.exists(path):
                try:
                    for root, dirs, files in os.walk(path):
                        # Limita a profundidade para não dar timeout
                        depth = root.replace(path, '').count(os.sep)
                        if depth > 4:
                            dirs.clear()
                            continue
                        if 'node' in files:
                            node_path = os.path.join(root, 'node')
                            if os.access(node_path, os.X_OK):
                                results.append(node_path)
                except Exception as walk_err:
                    results.append(f"Erro em {path}: {str(walk_err)}")
        return jsonify({
            "node_binaries_found": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/read-other-htaccess', methods=['GET'])
def read_other_htaccess():
    """Lê os arquivos .htaccess de outros apps na pasta apps/ para verificar a configuração funcional do Passenger."""
    try:
        import os
        results = {}
        base_apps = "/home/grpia/apps"
        if os.path.exists(base_apps):
            for item in os.listdir(base_apps):
                item_path = os.path.join(base_apps, item)
                if os.path.isdir(item_path):
                    htaccess_path = os.path.join(item_path, ".htaccess")
                    if os.path.exists(htaccess_path):
                        try:
                            with open(htaccess_path, 'r') as f:
                                results[item] = f.read()
                        except Exception as e:
                            results[item] = f"Erro ao ler: {str(e)}"
                    else:
                        results[item] = "Não possui .htaccess"
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/find-htaccess', methods=['GET'])
def find_htaccess():
    """Varre a conta do usuário /home/grpia/ para localizar todos os arquivos .htaccess."""
    try:
        import os
        results = []
        root_home = "/home/grpia"
        # Varre até profundidade 3 para evitar varrer pastas gigantescas como node_modules
        for root, dirs, files in os.walk(root_home):
            # Ignora pastas de controle e node_modules/trash para ir rápido
            if any(p in root for p in ["node_modules", ".git", ".trash", "repositories"]):
                dirs.clear()
                continue
            depth = root.replace(root_home, '').count(os.sep)
            if depth > 3:
                dirs.clear()
                continue
            if '.htaccess' in files:
                results.append(os.path.join(root, '.htaccess'))
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        # Vamos fazer uma busca ampla caso o caminho padrão não exista
        node_executable = None
        activate_path = None
        
        # 1. Tenta os caminhos padrão do usuário
        probable_paths = [
            "/home/grpia/nodevenv/apps/omnichannel/20/bin/activate",
            "/home/grpia/nodevenv/apps/omnichannel/18/bin/activate",
            "/home/grpia/nodevenv/apps/omnichannel/22/bin/activate",
        ]
        
        for path in probable_paths:
            if os.path.exists(path):
                activate_path = path
                break
                
        # 2. Se não achou, procura por versões do Node 20/22/18 instaladas no sistema
        if not activate_path:
            system_node_paths = [
                "/opt/cpanel/ea-nodejs22/bin",
                "/opt/alt/alt-nodejs20/root/usr/bin",
                "/opt/alt/alt-nodejs22/root/usr/bin",
                "/opt/alt/alt-nodejs18/root/usr/bin",
                "/usr/bin",
                "/usr/local/bin"
            ]
            for path in system_node_paths:
                potential_node = os.path.join(path, "node")
                if os.path.exists(potential_node):
                    node_executable = potential_node
                    break
                    
        # 3. Se ainda não achou, lista a raiz /home/grpia para diagnóstico
        scan_results = []
        if not activate_path and not node_executable:
            try:
                scan_results = os.listdir("/home/grpia")
            except Exception as e:
                scan_results.append(f"Erro ao listar raiz: {str(e)}")
                
        if not activate_path and not node_executable:
            return jsonify({
                "success": False, 
                "message": "Não foi possível encontrar o Node ou NVM no servidor.",
                "conteudo_raiz_home": scan_results
            }), 400
            
        # 4. Monta o comando de execução para depurar as dependências do React
        if activate_path:
            print("[Debug Build] Rodando 'npm run build' com NODE_ENV=production usando virtualenv...")
            cmd = f"export NODE_ENV=production && source {activate_path} && cd /home/grpia/apps/omnichannel && npm run build"
        elif node_executable:
            print(f"[Debug Build] Rodando 'npm run build' com NODE_ENV=production usando o Node: {node_executable}...")
            node_dir = os.path.dirname(node_executable)
            cmd = f"export NODE_ENV=production && export PATH={node_dir}:$PATH && cd /home/grpia/apps/omnichannel && npm run build"
        else:
            print("[Debug Build] Rodando 'npm run build' com NVM...")
            cmd = (
                "export NODE_ENV=production && "
                "export NVM_DIR=/home/grpia/.nvm && "
                "source $NVM_DIR/nvm.sh && "
                "nvm use 20.19.0 && "
                "cd /home/grpia/apps/omnichannel && "
                "npm run build"
            )
        
        result = subprocess.run(
            cmd,
            shell=True,
            executable='/bin/bash',
            capture_output=True,
            text=True,
            timeout=300  # Aumenta para 5 minutos para o build completo
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
