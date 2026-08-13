import config
from supabase import create_client, ClientOptions

def verificar():
    if not config.CRM_SUPABASE_URL or not config.CRM_SUPABASE_KEY:
        print("Erro: Configure URL e KEY no .env")
        return
        
    try:
        options = ClientOptions(schema="wacrm")
        supabase = create_client(config.CRM_SUPABASE_URL, config.CRM_SUPABASE_KEY, options=options)
        
        res = supabase.table("whatsapp_config").select("id, account_id, provider, status").execute()
        print("=== CONFIGURAÇÕES DE WHATSAPP ATIVAS ===")
        if res.data:
            for w in res.data:
                # Busca qual perfil/usuário é dono dessa conta
                prof_res = supabase.table("profiles").select("full_name, user_id").eq("account_id", w["account_id"]).execute()
                nomes = [p["full_name"] for p in prof_res.data] if prof_res.data else ["Nenhum"]
                print(f"Canal ID: {w['id']} | Provider: {w['provider']} | Status: {w['status']} | Donos do Perfil: {', '.join(nomes)} | Account ID: {w['account_id']}")
        else:
            print("Nenhuma configuração de WhatsApp encontrada.")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    verificar()
