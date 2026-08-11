import re
import pandas as pd
from bs4 import BeautifulSoup

def clean_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def normalizar_colunas(cols):
    """
    Mapeia os nomes das colunas de uma tabela/planilha para nossas chaves padronizadas:
    'nome', 'ra_cpf', 'telefone'
    """
    mapa = {}
    for col in cols:
        col_lower = str(col).lower().strip()
        
        # Mapeamento para Nome do Aluno
        if col_lower in ["aluno", "nome", "nome do aluno", "estudante"]:
            mapa["nome"] = col
        # Mapeamento para Identificador (RA ou CPF)
        elif col_lower in ["ra", "cpf", "matricula", "matrícula", "ra/cpf"]:
            mapa["ra_cpf"] = col
        # Mapeamento para Contato/Telefone
        elif col_lower in ["telefone", "telefone 1", "telefone1", "celular", "contato", "fone", "tel"]:
            mapa["telefone"] = col
            
    return mapa

def parse_excel(file_path):
    """
    Lê uma planilha Excel (.xlsx ou .xls), identifica as colunas relevantes
    e retorna uma lista de dicionários contendo os dados dos alunos.
    """
    try:
        df = pd.read_excel(file_path)
        mapa_colunas = normalizar_colunas(df.columns)
        
        # Se não encontrarmos colunas mapeadas automaticamente, tentamos heurísticas
        if "nome" not in mapa_colunas:
            # Assume que a primeira coluna do tipo string com nomes longos pode ser o nome
            for col in df.columns:
                if df[col].dtype == object and df[col].astype(str).str.len().mean() > 5:
                    mapa_colunas["nome"] = col
                    break
        
        # Garante que temos pelo menos o nome do aluno para prosseguir
        if "nome" not in mapa_colunas:
            raise ValueError("Não foi possível identificar a coluna de 'Nome' ou 'Aluno' na planilha.")
            
        alunos = []
        for _, row in df.iterrows():
            nome = clean_text(row.get(mapa_colunas.get("nome")))
            if not nome:
                continue # ignora linhas sem nome
                
            ra_cpf = clean_text(row.get(mapa_colunas.get("ra_cpf"))) if "ra_cpf" in mapa_colunas else ""
            telefone = clean_text(row.get(mapa_colunas.get("telefone"))) if "telefone" in mapa_colunas else ""
            
            # Limpa formatações de telefone se vier em float/int no Excel
            if telefone.endswith(".0"):
                telefone = telefone[:-2]
                
            alunos.append({
                "nome": nome,
                "ra_cpf": ra_cpf,
                "telefone": telefone
            })
            
        return alunos
    except Exception as e:
        print(f"[Erro Parser Excel] Falha ao processar planilha: {e}")
        return []

def parse_html_table(html_content):
    """
    Lê tabelas em formato HTML (corpo do e-mail) e extrai a lista de alunos.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            return []
            
        # Extrai os cabeçalhos
        headers = []
        thead = table.find("thead")
        if thead:
            headers = [clean_text(th.text) for th in thead.find_all("th")]
        else:
            # Se não houver thead, tenta pegar a primeira tr
            first_tr = table.find("tr")
            if first_tr:
                headers = [clean_text(td.text) for td in first_tr.find_all(["td", "th"])]
                
        mapa_colunas = normalizar_colunas(headers)
        
        # Localiza todas as linhas de dados (ignorando a primeira se ela continha os headers)
        rows = table.find_all("tr")
        start_idx = 1 if not thead and len(headers) > 0 else 0
        
        alunos = []
        for tr in rows[start_idx:]:
            tds = tr.find_all("td")
            if not tds or len(tds) < len(headers):
                continue
                
            # Cria um dicionário temporário da linha mapeando o cabeçalho ao valor
            row_data = {}
            for i, header in enumerate(headers):
                if i < len(tds):
                    row_data[header] = clean_text(tds[i].text)
                    
            nome = row_data.get(mapa_colunas.get("nome", ""))
            if not nome:
                continue
                
            ra_cpf = row_data.get(mapa_colunas.get("ra_cpf", ""))
            telefone = row_data.get(mapa_colunas.get("telefone", ""))
            
            alunos.append({
                "nome": nome,
                "ra_cpf": ra_cpf,
                "telefone": telefone
            })
            
        return alunos
    except Exception as e:
        print(f"[Erro Parser HTML] Falha ao processar tabela: {e}")
        return []

def parse_plain_text(text_content):
    """
    Processa e-mails em texto corrido.
    Suporta dois formatos:
    1. Formato Bloco Multilinhas (Multivix):
       RA: 2528022
       Aluno: Nilson Pereira da Silva
       Telefone 1: 27 997418799
    2. Formato Linha Única (Unidoctum):
       EMÍLIA OLIVEIRA WIGHTMAN CPF: 04700012676
    """
    alunos = []
    linhas = [l.strip() for l in text_content.split("\n") if l.strip()]
    
    # Heurística para detectar se o texto tem blocos estruturados de multilinhas
    tem_estrutura_multilinha = False
    for linha in linhas:
        linha_lower = linha.lower()
        if any(key in linha_lower for key in ["aluno:", "nome:", "ra:", "telefone 1:", "telefone:", "tel:"]):
            tem_estrutura_multilinha = True
            break
            
    if tem_estrutura_multilinha:
        print("[Plain Text Parser] Detectado formato multilinhas estruturado.")
        current_aluno = {}
        
        for linha in linhas:
            nome_match = re.search(r"(?:aluno|nome)\s*:\s*(.+)", linha, re.IGNORECASE)
            ra_match = re.search(r"(?:ra|cpf|matricula)\s*:\s*([\w\.-]+)", linha, re.IGNORECASE)
            tel_match = re.search(r"(?:telefone|celular|fone|contato)\s*(?:\d+)?\s*:\s*([\d\s+-]+)", linha, re.IGNORECASE)
            
            if nome_match or ra_match or tel_match:
                if not current_aluno:
                    current_aluno = {"nome": "", "ra_cpf": "", "telefone": ""}
                
                if nome_match:
                    # Se já temos um nome preenchido, salvamos o anterior antes de começar um novo
                    if current_aluno["nome"]:
                        if len(current_aluno["nome"]) > 3 and (current_aluno["ra_cpf"] or current_aluno["telefone"]):
                            alunos.append(current_aluno)
                        current_aluno = {"nome": "", "ra_cpf": "", "telefone": ""}
                    current_aluno["nome"] = nome_match.group(1).strip()
                    
                elif ra_match:
                    if current_aluno["ra_cpf"]:
                        if len(current_aluno["nome"]) > 3 and (current_aluno["ra_cpf"] or current_aluno["telefone"]):
                            alunos.append(current_aluno)
                        current_aluno = {"nome": "", "ra_cpf": "", "telefone": ""}
                    current_aluno["ra_cpf"] = ra_match.group(1).strip()
                    
                elif tel_match:
                    if current_aluno["telefone"]:
                        if len(current_aluno["nome"]) > 3 and (current_aluno["ra_cpf"] or current_aluno["telefone"]):
                            alunos.append(current_aluno)
                        current_aluno = {"nome": "", "ra_cpf": "", "telefone": ""}
                    current_aluno["telefone"] = tel_match.group(1).strip()
                    
        # Salva o último aluno pendente do loop
        if current_aluno and len(current_aluno.get("nome", "")) > 3:
            if current_aluno.get("ra_cpf") or current_aluno.get("telefone"):
                alunos.append(current_aluno)
                
        if alunos:
            return alunos

    # --- FALLBACK: Parser de Linha Única (ex: Unidoctum) ---
    print("[Plain Text Parser] Processando no formato linha única (fallback)...")
    regex_cpf = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
    regex_ra = re.compile(r"\b\d{6,10}\b")
    regex_telefone = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-.\s]?\d{4}\b")
    
    for linha in linhas:
        linha_limpa = linha.strip()
        
        identificador = ""
        cpf_match = regex_cpf.search(linha_limpa)
        if cpf_match:
            identificador = cpf_match.group(0)
        else:
            ra_match = regex_ra.search(linha_limpa)
            if ra_match:
                identificador = ra_match.group(0)
                
        telefone = ""
        tel_match = regex_telefone.search(linha_limpa)
        if tel_match:
            telefone = tel_match.group(0)
            
        divisor = None
        for term in ["cpf:", "cpf", "ra:", "ra", "ra/cpf"]:
            if term in linha_limpa.lower():
                divisor = term
                break
                
        nome = ""
        if divisor:
            partes = re.split(divisor, linha_limpa, flags=re.IGNORECASE)
            nome = partes[0].strip(" -:;,")
        elif identificador:
            partes = linha_limpa.split(identificador)
            nome = partes[0].strip(" -:;,")
            
        nome = re.sub(r"[^\w\sÀ-ÿ]", "", nome).strip()
        
        if len(nome) > 3 and (identificador or telefone):
            alunos.append({
                "nome": nome,
                "ra_cpf": identificador,
                "telefone": telefone
            })
            
    return alunos
