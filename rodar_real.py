import os
import sys
import db_manager
import orchestrator
import whatsapp_connector
import config

def mostrar_menu():
    print("\n" + "="*50)
    print("      DDM NEGOTIATION AGENT - INTERACTIVE TESTER")
    print("="*50)
    print(f"Conta Configurada: {config.EMAIL_USER}")
    print(f"Modo WhatsApp: {'[WAHA REAL]' if config.USE_WAHA else '[SIMULADOR LOCAL]'}")
    print("-"*50)
    print("1. [LEITURA] Buscar novos e-mails e iniciar contatos")
    print("2. [WHATSAPP] Simular respostas dos alunos (Webhook)")
    print("3. [RETORNO] Verificar lotes prontos e enviar e-mails finais")
    print("4. [BANCO] Visualizar registros atuais no banco de dados")
    print("0. Sair")
    print("="*50)
    
def listar_alunos_ativos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.nome, a.ra_cpf, a.status_whatsapp, l.id, l.subject 
        FROM alunos_negociacao a
        JOIN lotes_email l ON a.lote_id = l.id
        WHERE a.status_whatsapp IN ('pendente', 'contatando')
    """)
    alunos = cursor.fetchall()
    conn.close()
    return alunos

def mostrar_banco_completo():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    print("\n--- LOTES REGISTRADOS ---")
    cursor.execute("SELECT id, sender, subject, status, confirmation_sent FROM lotes_email")
    lotes = cursor.fetchall()
    for lote in lotes:
        print(f"Lote ID: {lote[0]} | Remetente: {lote[1]} | Assunto: {lote[2]} | Status: {lote[3]} | Confirmado: {lote[4]}")
        
    print("\n--- ALUNOS REGISTRADOS ---")
    cursor.execute("SELECT id, lote_id, nome, ra_cpf, status_whatsapp FROM alunos_negociacao")
    alunos = cursor.fetchall()
    for aluno in alunos:
        print(f"Aluno ID: {aluno[0]} | Lote: {aluno[1]} | Nome: {aluno[2]} | RA/CPF: {aluno[3]} | Status: {aluno[4]}")
        
    conn.close()

def main():
    # Inicializa banco de dados
    orchestrator.inicializar_sistema()
    
    while True:
        mostrar_menu()
        opcao = input("Escolha uma opção (0-4): ").strip()
        
        if opcao == "1":
            print("\nBuscando novos e-mails no inbox...")
            try:
                orchestrator.executar_ciclo_leitura()
            except Exception as e:
                print(f"\n[Erro] Falha ao rodar ciclo de leitura: {e}")
                
        elif opcao == "2":
            alunos = listar_alunos_ativos()
            if not alunos:
                print("\n[WhatsApp] Não há alunos com atendimento ativo no momento (status 'pendente' ou 'contatando').")
                continue
                
            print("\n--- SELECIONE O ALUNO PARA SIMULAR RESPOSTA ---")
            for idx, aluno in enumerate(alunos):
                print(f"{idx + 1}. {aluno[1]} ({aluno[2]}) | Lote: {aluno[4]} - '{aluno[5]}'")
                
            try:
                escolha_aluno = int(input(f"Escolha o aluno (1-{len(alunos)}): ")) - 1
                if 0 <= escolha_aluno < len(alunos):
                    aluno_selecionado = alunos[escolha_aluno]
                    aluno_id = aluno_selecionado[0]
                    nome_aluno = aluno_selecionado[1]
                    
                    print(f"\nComo {nome_aluno} respondeu no WhatsApp?")
                    print("1. 'Sim, quero fazer o acordo agora!' (Status: Sucesso)")
                    print("2. 'Não tenho interesse.' (Status: Sem Retorno)")
                    print("3. 'Este número não é dele / Número errado' (Status: Erro)")
                    
                    escolha_resp = input("Escolha a opção (1-3): ").strip()
                    if escolha_resp == "1":
                        whatsapp_connector.processar_resposta_webhook(aluno_id, "Sim, fechar acordo")
                    elif escolha_resp == "2":
                        whatsapp_connector.processar_resposta_webhook(aluno_id, "Não quero")
                    elif escolha_resp == "3":
                        whatsapp_connector.processar_resposta_webhook(aluno_id, "numero errado / erro")
                    else:
                        print("Opção inválida.")
                else:
                    print("Aluno inválido.")
            except ValueError:
                print("Digite um número válido.")
                
        elif opcao == "3":
            print("\nVerificando se algum lote concluiu todas as negociações...")
            try:
                orchestrator.executar_ciclo_retorno()
            except Exception as e:
                print(f"\n[Erro] Falha ao rodar ciclo de retorno: {e}")
                
        elif opcao == "4":
            mostrar_banco_completo()
            
        elif opcao == "0":
            print("\nEncerrando o testador. Até mais!")
            sys.exit(0)
        else:
            print("\nOpção inválida.")
            
        input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    main()
