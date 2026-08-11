import sys
import os
import orchestrator

def main():
    print("=== INICIANDO EXECUÇÃO AUTOMÁTICA DO AGENTE DDM ===")
    
    # 1. Inicializa o banco de dados
    orchestrator.inicializar_sistema()
    
    # 2. Executa a triagem de novos e-mails e inicia disparos de WhatsApp
    try:
        orchestrator.executar_ciclo_leitura()
    except Exception as e:
        print(f"[Erro Automação] Falha no ciclo de leitura de e-mails: {e}", file=sys.stderr)
        
    # 3. Verifica atendimentos de WhatsApp finalizados e envia relatórios de fechamento por e-mail
    try:
        orchestrator.executar_ciclo_retorno()
    except Exception as e:
        print(f"[Erro Automação] Falha no ciclo de monitoramento de retornos: {e}", file=sys.stderr)
        
    print("=== EXECUÇÃO AUTOMÁTICA CONCLUÍDA ===")

if __name__ == "__main__":
    main()
