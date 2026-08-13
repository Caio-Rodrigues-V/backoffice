import config
import crm_connector

def rodar_teste():
    print("=== INICIANDO TESTE DE INTEGRAÇÃO DO CRM ===")
    
    # Validação das configurações básicas
    if not config.CRM_SUPABASE_URL or not config.CRM_SUPABASE_KEY:
        print("❌ ERRO: CRM_SUPABASE_URL ou CRM_SUPABASE_KEY não configurados no arquivo .env!")
        return
    if not config.CRM_ADMIN_USER_ID:
        print("❌ ERRO: CRM_ADMIN_USER_ID não configurado no arquivo .env!")
        return
        
    print(f"Supabase URL: {config.CRM_SUPABASE_URL}")
    print(f"Admin User ID: {config.CRM_ADMIN_USER_ID}")
    
    # DADOS DE TESTE
    # Dica: Substitua pelo seu nome e telefone real com DDD para testar o envio de WhatsApp
    nome_teste = "Aluno Teste Ponte"
    telefone_teste = "5521984354821"  
    ra_teste = "RA999999"
    valor_teste = 199.90
    
    mensagem = config.CRM_MENSAGEM_INICIAL.format(nome=nome_teste)
    
    print("\n[Teste] Iniciando inserção de dados e envio de mensagem...")
    sucesso = crm_connector.processar_aluno_no_crm(
        nome=nome_teste,
        telefone=telefone_teste,
        ra_cpf=ra_teste,
        valor=valor_teste,
        mensagem_inicial=mensagem
    )
    
    if sucesso:
        print("\n[OK] TESTE CONCLUIDO COM SUCESSO!")
        print("Verifique no seu CRM:")
        print("1. O contato 'Aluno Teste Ponte' foi criado na aba 'Contatos'.")
        print("2. Um card de R$ 199.90 entrou na etapa configurada do seu Funil (Pipelines).")
        print("3. A mensagem de WhatsApp foi enviada e o chat aparece ativo no Inbox.")
    else:
        print("\n[ERRO] FALHA NO TESTE. Verifique os logs acima para identificar o erro.")

if __name__ == "__main__":
    rodar_teste()
