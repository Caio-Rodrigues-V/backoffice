import os
import json
import sqlite3
import pandas as pd
import config
import db_manager
import orchestrator
import whatsapp_connector

def limpar_simulacao():
    """Limpa arquivos de simulações anteriores para começar do zero."""
    if os.path.exists(config.DB_NAME):
        os.remove(config.DB_NAME)
        
    for pasta in [config.EMAILS_ENTRADA_DIR, config.EMAILS_SAIDA_DIR, config.WHATSAPP_SIMULADO_DIR]:
        if os.path.exists(pasta):
            for f in os.listdir(pasta):
                os.remove(os.path.join(pasta, f))
    print("[Simulador] Histórico de simulação limpo.")

def criar_emails_ficticios():
    """Cria e-mails simulando os três casos reais recebidos."""
    # --- CASO 1: Multivix (Tabela HTML no Corpo) ---
    email_1 = {
        "id": "email_multivix_tabela",
        "sender": "taina.lellis@multivix.edu.br",
        "subject": "NEGOCIAÇÃO",
        "body_html": """
        <html>
            <body>
                <p>Boa tarde!</p>
                <p>Solicito, por gentileza, entrar em contato com o aluno informado abaixo para negociação.</p>
                <table border="1" cellpadding="5" cellspacing="0">
                    <thead>
                        <tr bgcolor="#CCCCCC">
                            <th>RA</th>
                            <th>Aluno</th>
                            <th>Telefone 1</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>2528022</td>
                            <td>Nilson Pereira da Silva</td>
                            <td>27 997418799</td>
                        </tr>
                    </tbody>
                </table>
                <p>Atenciosamente,</p>
            </body>
        </html>
        """
    }
    
    # --- CASO 2: E-mail de remetente NÃO autorizado (Deve ser ignorado) ---
    email_2 = {
        "id": "email_spam_ignorado",
        "sender": "propaganda_vendas@gmail.com",
        "subject": "NEGOCIAÇÃO DE PRODUTOS",
        "body_text": "Olá! Gostaria de oferecer nossos serviços de cobrança..."
    }
    
    # --- CASO 3: Multivix (Planilha Excel em Anexo) ---
    # Cria a planilha excel fictícia na pasta simulador
    excel_path = os.path.join(config.SIMULACAO_DIR, "Inaptos DDM - 28.07.2026.xlsx")
    df_excel = pd.DataFrame({
        "RA": [2528033, 2528034],
        "Aluno": ["Maria de Souza Martins", "José dos Santos Oliveira"],
        "Telefone 1": ["27 998887777", "27 996665555"]
    })
    df_excel.to_excel(excel_path, index=False)
    
    email_3 = {
        "id": "email_multivix_excel",
        "sender": "dimitry.moreno@multivix.edu.br",
        "subject": "INAPTOS À REMATRICULAS 2026/2 - DDM - MULTIVIX CACHOEIRO",
        "body_text": "Prezados, boa tarde!\nSegue em anexo a base de alunos de Cachoeiro que estão inaptos à rematrícula.",
        "attachment_excel": excel_path
    }
    
    # Salva os arquivos JSON na pasta de caixa de entrada simulada
    for email in [email_1, email_2, email_3]:
        caminho = os.path.join(config.EMAILS_ENTRADA_DIR, f"{email['id']}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(email, f, indent=4, ensure_ascii=False)
            
    print("[Simulador] E-mails de teste criados na pasta 'simulador/caixa_entrada'.")

def mostrar_banco():
    """Exibe o estado atual das tabelas do banco de dados para verificação."""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    print("\n--- ESTADO ATUAL DO BANCO DE DADOS (TABELA: ALUNOS) ---")
    cursor.execute("SELECT id, lote_id, nome, ra_cpf, status_whatsapp FROM alunos_negociacao")
    alunos = cursor.fetchall()
    
    if not alunos:
        print("(Nenhum aluno cadastrado no banco)")
    else:
        for aluno in alunos:
            print(f"ID: {aluno[0]} | Lote: {aluno[1]} | Nome: {aluno[2]} | ID (RA/CPF): {aluno[3]} | Status: {aluno[4]}")
            
    conn.close()

def main():
    print("==================================================")
    print("       SIMULAÇÃO COMPLETA DO AGENTE DDM")
    print("==================================================")
    
    # Passo 1: Limpar e inicializar
    limpar_simulacao()
    orchestrator.inicializar_sistema()
    criar_emails_ficticios()
    
    # Passo 2: Executar o ciclo de leitura dos novos e-mails
    orchestrator.executar_ciclo_leitura()
    
    # Mostrar banco após leitura
    mostrar_banco()
    
    # Passo 3: Simular respostas dos alunos pelo WhatsApp
    print("\n--- SIMULANDO INTERAÇÕES DE WHATSAPP ---")
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM alunos_negociacao")
    alunos = cursor.fetchall()
    conn.close()
    
    # Mapeando respostas para cada aluno
    respostas_simuladas = {
        "Nilson Pereira da Silva": "Sim, tenho interesse em fazer o acordo agora!",
        "Maria de Souza Martins": "Não posso pagar isso agora, infelizmente.",
        "José dos Santos Oliveira": "número inválido (sistema detectou erro)"
    }
    
    for aluno_id, nome in alunos:
        resposta = respostas_simuladas.get(nome, "Não respondeu (timeout)")
        whatsapp_connector.processar_resposta_webhook(aluno_id, resposta)
        
    # Mostrar banco após interações
    mostrar_banco()
    
    # Passo 4: Executar o ciclo de retorno para enviar os e-mails finais
    orchestrator.executar_ciclo_retorno()
    
    # Passo 5: Exibir os e-mails de retorno enviados na pasta de saída
    print("\n--- E-MAILS DE RETORNO GERADOS PELO AGENTE ---")
    retornos = os.listdir(config.EMAILS_SAIDA_DIR)
    for retorno in retornos:
        caminho = os.path.join(config.EMAILS_SAIDA_DIR, retorno)
        print(f"\n[Arquivo: {retorno}]")
        with open(caminho, "r", encoding="utf-8") as f:
            print(f.read())
            
    print("==================================================")
    print("       FIM DA SIMULAÇÃO COM SUCESSO!")
    print("==================================================")

if __name__ == "__main__":
    main()
