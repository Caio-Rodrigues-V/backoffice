import config
from supabase import create_client, ClientOptions

def listar_ids():
    print("=== BUSCANDO PIPELINES E STAGES NO SUPABASE ===")
    if not config.CRM_SUPABASE_URL or not config.CRM_SUPABASE_KEY:
        print("❌ ERRO: Configure CRM_SUPABASE_URL e CRM_SUPABASE_KEY no seu .env primeiro!")
        return
        
    try:
        options = ClientOptions(schema="wacrm")
        supabase = create_client(config.CRM_SUPABASE_URL, config.CRM_SUPABASE_KEY, options=options)
        
        # 1. Lista Perfis/Usuários para achar o admin
        print("\n--- Usuários Cadastrados (Profiles) ---")
        profiles = supabase.table("profiles").select("user_id, full_name, account_id").execute()
        if profiles.data:
            for p in profiles.data:
                print(f"Nome: {p.get('full_name')} | CRM_ADMIN_USER_ID: {p.get('user_id')} | Account ID: {p.get('account_id')}")
        else:
            print("Nenhum perfil encontrado.")
            
        # 2. Lista Pipelines
        print("\n--- Funis Disponíveis (Pipelines) ---")
        pipelines = supabase.table("pipelines").select("id, name, account_id").execute()
        if pipelines.data:
            for pl in pipelines.data:
                print(f"Funil: {pl['name']} | CRM_PIPELINE_ID: {pl['id']} | Account ID: {pl.get('account_id')}")
                
                # Lista Estágios deste pipeline
                stages = supabase.table("pipeline_stages").select("id, name").eq("pipeline_id", pl['id']).order("position").execute()
                if stages.data:
                    for st in stages.data:
                        print(f"    - Etapa: {st['name']} | CRM_STAGE_ID: {st['id']}")
                else:
                    print("    - Sem etapas cadastradas.")
        else:
            print("Nenhum funil (pipeline) encontrado.")
            
    except Exception as e:
        print(f"Erro ao conectar ao Supabase: {e}")

if __name__ == "__main__":
    listar_ids()
