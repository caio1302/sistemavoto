import sqlite3
import os
import sys
from tkinter import messagebox
import hashlib
import logging

import config
from functions import data_helpers

SCHEMA_VERSION = 18

def get_db_version(cursor):
    try:
        cursor.execute("SELECT version FROM schema_info WHERE id = 1")
        row = cursor.fetchone()
        return row['version'] if row else 0
    except sqlite3.OperationalError:
        return 0

def set_db_version(cursor, version):
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_info (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)")
    cursor.execute("INSERT OR REPLACE INTO schema_info (id, version) VALUES (1, ?)", (version,))

def migrate_schema(cursor, from_version, to_version):
    logging.info(f"Iniciando migração do schema do DB da versão {from_version} para {to_version}...")
    
    def add_column_if_not_exists(cursor, table_name, column_definition):
        column_name = column_definition.split()[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row['name'] for row in cursor.fetchall()]
        if column_name not in existing_columns:
            logging.info(f"Adicionando coluna '{column_name}' à tabela '{table_name}'...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
            if column_name == 'data_criacao':
                logging.info(f"Preenchendo 'data_criacao' para registros existentes em '{table_name}'...")
                cursor.execute(f"UPDATE {table_name} SET data_criacao = STRFTIME('%Y-%m-%d %H:%M:%S', 'now') WHERE data_criacao IS NULL")
        else:
            logging.info(f"Coluna '{column_name}' já existe na tabela '{table_name}'. Pulando.")

    if from_version < 17:
        logging.info("Migrando para a versão 17: Garantindo valores padrão e colunas de visibilidade...")
        add_column_if_not_exists(cursor, "pessoas", "geo_visivel INTEGER DEFAULT 0")
        add_column_if_not_exists(cursor, "organizacoes", "geo_visivel INTEGER DEFAULT 0")
        cursor.execute("UPDATE pessoas SET geo_visivel = 0 WHERE geo_visivel IS NULL;")
        cursor.execute("UPDATE organizacoes SET geo_visivel = 0 WHERE geo_visivel IS NULL;")
        logging.info("Garantido que geo_visivel existe e o padrão é 0 para novos registros. Contatos existentes foram definidos como não visíveis.")
    
    if from_version < 18:
        logging.info("Migrando para a versão 18: Padronizando nomes de cidades com apóstrofos...")
        
        # --- LÓGICA DE MIGRAÇÃO CORRIGIDA USANDO DIRETAMENTE SEU SQL ---
        tabelas_para_corrigir = ["candidaturas", "votos_por_municipio", "municipios", "pessoas", "organizacoes"]
        
        for tabela in tabelas_para_corrigir:
            try:
                # Primeiro, aplica a normalização de substituir ' por espaço
                update_query_apostrofo = f"UPDATE {tabela} SET cidade = REPLACE(cidade, '''', ' ') WHERE cidade LIKE '%''%'"
                cursor.execute(update_query_apostrofo)
                logging.info(f"Corrigido apóstrofos em '{tabela}': {cursor.rowcount} linhas afetadas.")

                # Em seguida, normaliza o resultado para o padrão da cidade_key
                cursor.execute(f"SELECT id, cidade FROM {tabela} WHERE cidade IS NOT NULL")
                registros = cursor.fetchall()
                
                updates_necessarios = []
                id_col_name = f"id_{tabela.rstrip('s')}" if not tabela.startswith("votos") else "id_voto_municipio"
                
                # Para tabelas principais, o ID é mais simples
                if tabela == "pessoas": id_col_name = "id_pessoa"
                if tabela == "organizacoes": id_col_name = "id_organizacao"
                if tabela == "candidaturas": id_col_name = "id_candidatura"
                if tabela == "municipios": id_col_name = "id"

                # Renormaliza para garantir consistência com a nova função
                for row in registros:
                    cidade_atual = row['cidade']
                    cidade_normalizada = data_helpers.normalize_city_key(cidade_atual)
                    if cidade_atual != cidade_normalizada:
                        updates_necessarios.append((cidade_normalizada, row[id_col_name]))
                
                if updates_necessarios:
                    update_query_normalize = f"UPDATE {tabela} SET cidade = ? WHERE {id_col_name} = ?"
                    cursor.executemany(update_query_normalize, updates_necessarios)
                    logging.info(f"Renormalizado cidades em '{tabela}': {len(updates_necessarios)} linhas afetadas.")

            except sqlite3.OperationalError as e:
                logging.warning(f"Não foi possível processar a tabela '{tabela}' (pode não ter a coluna 'cidade' ou 'id'): {e}")

        # Finalmente, garante que as chaves em 'municipios' estejam 100% corretas
        cursor.execute("SELECT id, cidade FROM municipios")
        municipios_para_atualizar_key = []
        for row in cursor.fetchall():
            cidade_key_correta = data_helpers.normalize_city_key(row['cidade'])
            municipios_para_atualizar_key.append((cidade_key_correta, row['id']))
        
        if municipios_para_atualizar_key:
            cursor.executemany("UPDATE municipios SET cidade_key = ? WHERE id = ?", municipios_para_atualizar_key)
            logging.info(f"Atualizado 'cidade_key' na tabela 'municipios' para {len(municipios_para_atualizar_key)} registros.")

        logging.info("Correção e padronização de nomes de cidades concluída.")


def setup_database():
    db_exists = os.path.exists(config.DB_PATH_CONFIG)
    conn = None
    try:
        conn = sqlite3.connect(config.DB_PATH_CONFIG)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        current_version = get_db_version(cursor)

        if not db_exists:
            logging.warning(f"Banco de dados inexistente. Criando do zero para a versão {SCHEMA_VERSION}...")
            _create_all_tables(cursor)
            _populate_lookup_data(cursor)
            set_db_version(cursor, SCHEMA_VERSION)
            conn.commit()
            logging.info(f"Banco de dados criado com sucesso na versão {SCHEMA_VERSION}.")
        
        elif current_version < SCHEMA_VERSION:
            logging.warning(f"Banco de dados desatualizado (versão {current_version}). Iniciando migração para a versão {SCHEMA_VERSION}...")
            migrate_schema(cursor, current_version, to_version=SCHEMA_VERSION)
            set_db_version(cursor, SCHEMA_VERSION)
            conn.commit()
            logging.info(f"Migração do banco de dados concluída com sucesso para a versão {SCHEMA_VERSION}.")
        else:
            logging.info(f"Schema do DB está atualizado (Versão {current_version}). Nenhuma ação necessária.")

    except Exception as e:
        if conn: conn.rollback()
        logging.critical(f"Erro crítico durante o setup/migração do banco de dados: {e}", exc_info=True)
        messagebox.showerror("Erro Crítico de DB", f"Falha ao configurar/migrar o banco de dados: {e}\n\nO programa será encerrado. Verifique o arquivo 'app.log'.")
        sys.exit(1)
    finally:
        if conn: conn.close()

def _create_all_tables(cursor):
    logging.info(f"Criando schema completo das tabelas (v{SCHEMA_VERSION})...")
    cursor.execute('''CREATE TABLE pessoas (id_pessoa INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, apelido TEXT, cpf TEXT UNIQUE, data_nascimento TEXT, genero TEXT, email TEXT, celular TEXT, telefone_residencial TEXT, caminho_foto TEXT, notas_pessoais TEXT, voto TEXT, id_tratamento INTEGER, id_profissao INTEGER, id_escolaridade INTEGER, id_organizacao_trabalho INTEGER, rg TEXT, titulo_eleitor TEXT UNIQUE, sg_uf_nascimento TEXT, cd_genero TEXT, cd_grau_instrucao TEXT, cd_ocupacao TEXT, cd_estado_civil TEXT, ds_estado_civil TEXT, cd_cor_raca TEXT, ds_cor_raca TEXT, endereco TEXT, numero TEXT, complemento TEXT, bairro TEXT, cep TEXT, cidade TEXT, uf TEXT, latitude REAL, longitude REAL, geo_visivel INTEGER DEFAULT 0, data_criacao TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')))''') 
    cursor.execute('''CREATE TABLE organizacoes (id_organizacao INTEGER PRIMARY KEY AUTOINCREMENT, nome_fantasia TEXT NOT NULL, razao_social TEXT, cnpj TEXT UNIQUE, email TEXT, telefone TEXT, website TEXT, id_unidade_vinculada INTEGER, data_inicio_atividade TEXT, notas TEXT, cep TEXT, endereco TEXT, numero TEXT, complemento TEXT, bairro TEXT, cidade TEXT, uf TEXT, id_municipio INTEGER, tipo_organizacao TEXT, latitude REAL, longitude REAL, geo_visivel INTEGER DEFAULT 0, data_criacao TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')), FOREIGN KEY (id_municipio) REFERENCES municipios(id) ON DELETE SET NULL)''')
    cursor.execute('''CREATE TABLE candidaturas (id_candidatura INTEGER PRIMARY KEY AUTOINCREMENT, id_pessoa INTEGER NOT NULL, ano_eleicao INTEGER NOT NULL, sq_candidato TEXT, nome_urna TEXT, numero_urna TEXT, partido TEXT, cargo TEXT, cidade TEXT, uf TEXT, votos INTEGER DEFAULT 0, situacao TEXT, cd_eleicao TEXT, ds_eleicao TEXT, dt_eleicao TEXT, tp_abrangencia TEXT, sg_ue TEXT, cd_cargo TEXT, nm_social_candidato TEXT, nr_partido TEXT, cd_sit_tot_turno TEXT, FOREIGN KEY (id_pessoa) REFERENCES pessoas(id_pessoa) ON DELETE CASCADE, UNIQUE (sq_candidato, ano_eleicao, cidade))''')
    cursor.execute('''CREATE TABLE votos_por_municipio (id_voto_municipio INTEGER PRIMARY KEY AUTOINCREMENT, sq_candidato TEXT NOT NULL, ano_eleicao INTEGER NOT NULL, cidade TEXT NOT NULL, votos INTEGER DEFAULT 0, FOREIGN KEY (sq_candidato) REFERENCES candidaturas(sq_candidato) ON DELETE CASCADE, UNIQUE (sq_candidato, ano_eleicao, cidade))''')
    cursor.execute('''CREATE TABLE municipios (id INTEGER PRIMARY KEY AUTOINCREMENT, cidade_key TEXT UNIQUE, cidade TEXT, uf TEXT, sg_ue TEXT, cod_ibge TEXT, populacao INTEGER, dens_demo REAL, gentilico TEXT, area REAL, idhm_geral REAL, idhm_long REAL, idhm_renda REAL, idhm_educ REAL, aniversario TEXT)''')
    cursor.execute('''CREATE TABLE eleitorado (id_eleitorado INTEGER PRIMARY KEY AUTOINCREMENT, id_municipio INTEGER NOT NULL, ano INTEGER NOT NULL, total INTEGER, masculino INTEGER, feminino INTEGER, nao_informado INTEGER, FOREIGN KEY (id_municipio) REFERENCES municipios(id), UNIQUE(id_municipio, ano))''')
    cursor.execute("CREATE TABLE tratamentos (id INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE profissoes (id INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE escolaridades (id INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE tags (id_tag INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL)")
    cursor.execute('''CREATE TABLE pessoa_tags_assoc (id_pessoa INTEGER NOT NULL, id_tag INTEGER NOT NULL, FOREIGN KEY (id_pessoa) REFERENCES pessoas(id_pessoa) ON DELETE CASCADE, FOREIGN KEY (id_tag) REFERENCES tags(id_tag) ON DELETE CASCADE, PRIMARY KEY (id_pessoa, id_tag))''')
    cursor.execute("CREATE TABLE listas (id_lista INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL, tipo TEXT)")
    cursor.execute('''CREATE TABLE pessoa_listas_assoc (id_pessoa INTEGER NOT NULL, id_lista INTEGER NOT NULL, FOREIGN KEY (id_pessoa) REFERENCES pessoas(id_pessoa) ON DELETE CASCADE, FOREIGN KEY (id_lista) REFERENCES listas(id_lista) ON DELETE CASCADE, PRIMARY KEY (id_pessoa, id_lista))''')
    cursor.execute('''CREATE TABLE relacionamentos (id_relacionamento INTEGER PRIMARY KEY AUTOINCREMENT, id_pessoa_origem INTEGER NOT NULL, id_pessoa_destino INTEGER NOT NULL, tipo_relacao TEXT NOT NULL, FOREIGN KEY (id_pessoa_origem) REFERENCES pessoas(id_pessoa) ON DELETE CASCADE, FOREIGN KEY (id_pessoa_destino) REFERENCES pessoas(id_pessoa) ON DELETE CASCADE, UNIQUE (id_pessoa_origem, id_pessoa_destino, tipo_relacao))''')
    cursor.execute('''CREATE TABLE usuarios (id_usuario INTEGER PRIMARY KEY AUTOINCREMENT, nome_usuario TEXT UNIQUE NOT NULL, hash_senha TEXT NOT NULL, nome_completo TEXT, nivel_acesso TEXT NOT NULL DEFAULT 'assessor', data_nascimento TEXT, telefone TEXT, email TEXT, caminho_foto TEXT, login_token TEXT, token_validade TEXT)''')
    cursor.execute('''CREATE TABLE atendimentos (id_atendimento INTEGER PRIMARY KEY AUTOINCREMENT, id_pessoa INTEGER, id_organizacao INTEGER, titulo TEXT NOT NULL, descricao_demanda TEXT, data_abertura TEXT NOT NULL, responsavel_atendimento TEXT, status TEXT DEFAULT 'Aberto', prioridade TEXT DEFAULT 'Normal', data_criacao TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')), FOREIGN KEY (id_pessoa) REFERENCES pessoas(id_pessoa) ON DELETE SET NULL, FOREIGN KEY (id_organizacao) REFERENCES organizacoes(id_organizacao) ON DELETE SET NULL)''') 
    cursor.execute('''CREATE TABLE atendimento_updates (id_update INTEGER PRIMARY KEY AUTOINCREMENT, id_atendimento INTEGER NOT NULL, data_update TEXT NOT NULL, autor_update TEXT, descricao_update TEXT NOT NULL, FOREIGN KEY (id_atendimento) REFERENCES atendimentos(id_atendimento) ON DELETE CASCADE)''')
    cursor.execute("CREATE TABLE temas (id_tema INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL)")
    cursor.execute('''CREATE TABLE proposicoes (id_proposicao INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, tipo TEXT, autor TEXT, data_proposicao TEXT, status TEXT DEFAULT 'Protocolado', descricao TEXT, link_documento TEXT, data_criacao TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')))''') 
    cursor.execute('''CREATE TABLE proposicao_temas_assoc (id_proposicao INTEGER NOT NULL, id_tema INTEGER NOT NULL, FOREIGN KEY (id_proposicao) REFERENCES proposicoes(id_proposicao) ON DELETE CASCADE, FOREIGN KEY (id_tema) REFERENCES temas(id_tema) ON DELETE CASCADE, PRIMARY KEY (id_proposicao, id_tema))''')
    cursor.execute('''CREATE TABLE eventos (id_evento INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, data_evento TEXT NOT NULL, hora_inicio TEXT, hora_fim TEXT, local TEXT, descricao TEXT, data_criacao TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')))''') 
    cursor.execute('''CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE schema_info (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)''')

def _populate_lookup_data(cursor):
    lookup_data = {
        "tratamentos": [("Sr.",), ("Sra.",), ("Dr.",), ("Dra.",), ("Deputado",), ("Vereador",), ("Prefeito",), ("Ex-Prefeito",)],
        "profissoes": [("Advogado(a)",), ("Médico(a)",), ("Engenheiro(a)",), ("Professor(a)",), ("Empresário(a)",), ("Funcionário Público",)],
        "escolaridades": [("Ensino Fundamental",), ("Ensino Médio",), ("Ensino Superior Incompleto",), ("Ensino Superior Completo",), ("Pós-graduação",), ("Mestrado",), ("Doutorado",)],
        "tags": [("Apoiador-Chave",), ("Liderança Comunitária",), ("Influenciador",), ("Empresariado",), ("Imprensa",), ("Potencial Doador",)],
        "listas": [("Todas as Pessoas", "Pessoas"), ("Todas as Organizações", "Organizacoes")],
        "temas": [("Saúde",), ("Educação",), ("Segurança",), ("Infraestrutura",), ("Meio Ambiente",), ("Cultura e Lazer",), ("Desenvolvimento Econômico",)]
    }
    for table, data in lookup_data.items():
        if table == "listas": cursor.executemany(f"INSERT OR IGNORE INTO {table} (nome, tipo) VALUES (?, ?)", data)
        else: cursor.executemany(f"INSERT OR IGNORE INTO {table} (nome) VALUES (?)", data)
    
    admin_user = 'admin'; admin_pass = 'admin'; hashed_pass = hashlib.sha256(admin_pass.encode('utf-8')).hexdigest()
    cursor.execute("INSERT OR IGNORE INTO usuarios (nome_usuario, hash_senha, nome_completo, nivel_acesso) VALUES (?, ?, ?, ?)", (admin_user, hashed_pass, 'Administrador do Sistema', 'admin'))
    logging.info("Dados de lookup e usuário admin criados.")