import sqlite3
import os
from datetime import datetime
from config import DB_NAME

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Inicializa as tabelas do banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Lotes de E-mail recebidos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lotes_email (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        subject TEXT NOT NULL,
        received_at TEXT NOT NULL,
        confirmation_sent INTEGER DEFAULT 0,
        status TEXT DEFAULT 'processando' -- 'processando', 'concluido'
    )
    ''')
    
    # Verifica se a coluna message_id existe, se não, adiciona
    cursor.execute("PRAGMA table_info(lotes_email)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "message_id" not in colunas:
        cursor.execute("ALTER TABLE lotes_email ADD COLUMN message_id TEXT")
    
    # Tabela de Alunos vinculados a cada lote
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alunos_negociacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        ra_cpf TEXT,
        telefone TEXT,
        status_whatsapp TEXT DEFAULT 'pendente', -- 'pendente', 'contatando', 'acordo_fechado', 'sem_retorno', 'erro'
        last_update TEXT NOT NULL,
        FOREIGN KEY(lote_id) REFERENCES lotes_email(id)
    )
    ''')
    
    conn.commit()
    conn.close()

def lote_existe(message_id):
    """Verifica se já existe um lote cadastrado com o message_id fornecido."""
    if not message_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM lotes_email WHERE message_id = ?", (message_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def criar_lote(sender, subject, message_id=None):
    """Cria um novo registro de lote e retorna o ID gerado."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO lotes_email (sender, subject, received_at, message_id) VALUES (?, ?, ?, ?)",
        (sender, subject, now, message_id)
    )
    lote_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return lote_id

def adicionar_aluno(lote_id, nome, ra_cpf, telefone):
    """Adiciona um aluno ao lote de negociação."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO alunos_negociacao (lote_id, nome, ra_cpf, telefone, last_update) VALUES (?, ?, ?, ?, ?)",
        (lote_id, nome, ra_cpf, telefone, now)
    )
    
    conn.commit()
    conn.close()

def marcar_confirmacao_enviada(lote_id):
    """Marca o e-mail de recebimento inicial como enviado para o lote."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE lotes_email SET confirmation_sent = 1 WHERE id = ?",
        (lote_id,)
    )
    
    conn.commit()
    conn.close()

def atualizar_status_aluno(aluno_id, novo_status):
    """Atualiza o status de atendimento de um aluno específico pelo ID."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute(
        "UPDATE alunos_negociacao SET status_whatsapp = ?, last_update = ? WHERE id = ?",
        (novo_status, now, aluno_id)
    )
    
    conn.commit()
    conn.close()

def verificar_lote_concluido(lote_id):
    """
    Verifica se todos os alunos de um determinado lote já foram processados
    (status final: acordo_fechado, sem_retorno ou erro).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Seleciona alunos que ainda estão 'pendente' ou 'contatando'
    cursor.execute(
        "SELECT COUNT(*) FROM alunos_negociacao WHERE lote_id = ? AND status_whatsapp IN ('pendente', 'contatando')",
        (lote_id,)
    )
    restantes = cursor.fetchone()[0]
    
    conn.close()
    return restantes == 0

def obter_lotes_pendentes_retorno():
    """
    Retorna todos os lotes que estão como 'processando', mas que todos os seus
    alunos já atingiram o status final. Esses lotes precisam do e-mail de retorno final.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Seleciona lotes ativos
    cursor.execute("SELECT id, sender, subject, message_id FROM lotes_email WHERE status = 'processando'")
    lotes_ativos = cursor.fetchall()
    
    lotes_para_concluir = []
    for lote_id, sender, subject, message_id in lotes_ativos:
        if verificar_lote_concluido(lote_id):
            lotes_para_concluir.append({
                "id": lote_id,
                "sender": sender,
                "subject": subject,
                "message_id": message_id
            })
            
    conn.close()
    return lotes_para_concluir

def concluir_lote(lote_id):
    """Marca o lote de e-mail como concluído."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE lotes_email SET status = 'concluido' WHERE id = ?",
        (lote_id,)
    )
    
    conn.commit()
    conn.close()

def obter_relatorio_lote(lote_id):
    """Retorna uma lista com os alunos e seus respectivos status finais para o relatório."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT nome, ra_cpf, telefone, status_whatsapp FROM alunos_negociacao WHERE lote_id = ?",
        (lote_id,)
    )
    alunos = cursor.fetchall()
    
    relatorio = []
    for nome, ra_cpf, telefone, status in alunos:
        relatorio.append({
            "nome": nome,
            "ra_cpf": ra_cpf,
            "telefone": telefone,
            "status": status
        })
        
    conn.close()
    return relatorio
