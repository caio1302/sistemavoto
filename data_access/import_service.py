import sqlite3
import logging
import csv
from collections import defaultdict
import re
import os

from functions import data_helpers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person_repository import PersonRepository
    from .misc_repository import MiscRepository

class ImportService:
    def __init__(self, conn: sqlite3.Connection, person_repo: 'PersonRepository', misc_repo: 'MiscRepository'):
        self.conn = conn
        self.person_repo = person_repo
        self.misc_repo = misc_repo

    def _get_or_create_lookup_id(self, cursor, table_name, value_name, cache: dict):
        if not value_name: return None
        if value_name in cache:
            return cache[value_name]
        
        cursor.execute(f"INSERT OR IGNORE INTO {table_name} (nome) VALUES (?)", (value_name,))
        if cursor.rowcount > 0:
            new_id = cursor.lastrowid
            cache[value_name] = new_id
            return new_id
        else:
            cursor.execute(f"SELECT id FROM {table_name} WHERE nome = ?", (value_name,))
            res = cursor.fetchone()
            if res:
                cache[value_name] = res['id']
                return res['id']
        return None

    def importar_csv_eleicao(self, filepath: str, progress_win):
        try:
            class InterruptedError(Exception): pass

            progress_win.after(0, lambda: progress_win.update_progress("Fase 1/3: Lendo e agregando votos do arquivo CSV...", 0.0))
            
            with open(filepath, 'r', encoding='latin-1', buffering=1024*1024) as f:
                total_rows = sum(1 for _ in f) - 1

            if progress_win.stop_event.is_set(): raise InterruptedError

            votos_agregados = defaultdict(lambda: defaultdict(int))
            candidato_info_cache_csv = {}
            ano_eleicao_arquivo = None

            with open(filepath, 'r', encoding='latin-1', buffering=1024*1024) as f:
                reader = csv.DictReader(f, delimiter=';')
                header = [h.strip().upper().replace('"', '') for h in reader.fieldnames]
                reader.fieldnames = header
                col_keys = [k.replace('"', '') for k in header]

                for i, row in enumerate(reader):
                    if i > 0 and i % 50000 == 0:
                        if progress_win.stop_event.is_set(): raise InterruptedError
                        progress = (i / total_rows) * 0.4 if total_rows > 0 else 0
                        progress_win.after(0, lambda r=i, t=total_rows, p=progress: progress_win.update_progress(f"Lendo linha {r:,} de {t:,}", p))

                    values = [v.strip().replace('"', '') if v else '' for v in row.values()]
                    norm_row = dict(zip(col_keys, values))

                    sq_cand = norm_row.get('SQ_CANDIDATO')
                    cidade_original = norm_row.get('NM_MUNICIPIO')
                    cidade_key = data_helpers.normalize_city_key(cidade_original) if cidade_original else ''
                    if not ano_eleicao_arquivo: ano_eleicao_arquivo = data_helpers.safe_int(norm_row.get('ANO_ELEICAO'))
                    if not sq_cand or not cidade_key: continue

                    if sq_cand not in candidato_info_cache_csv:
                        candidato_info_cache_csv[sq_cand] = {'cargo': norm_row.get('DS_CARGO'),'ano': ano_eleicao_arquivo}
                    votos_agregados[sq_cand][cidade_key] += data_helpers.safe_int(norm_row.get('QT_VOTOS_NOMINAIS'))

            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("PRAGMA foreign_keys = OFF")
                
                progress_win.after(0, lambda: progress_win.update_progress("Fase 2/3: Processando e salvando dados no banco...", 0.4))
                
                cursor.execute("SELECT sq_candidato, cargo FROM candidaturas WHERE ano_eleicao = ?", (ano_eleicao_arquivo,))
                cargos_cache = {row['sq_candidato']: row['cargo'] for row in cursor.fetchall()}
                total_candidatos = len(votos_agregados)

                insert_votos_municipio_buffer = []
                update_votos_candidatura_municipal_buffer = []
                # --- NOVO: Guarda os candidatos que precisam da atualização final ---
                federal_state_sq_cands = set()

                for idx, (sq_cand, cidades_votos_map) in enumerate(votos_agregados.items()):
                    if idx > 0 and idx % 1000 == 0:
                        if progress_win.stop_event.is_set(): raise InterruptedError
                        progress = 0.4 + (idx / total_candidatos) * 0.4
                        progress_win.after(0, lambda i=idx, t=total_candidatos, p=progress: progress_win.update_progress(f"Processando candidato {i}/{t}", p))

                    cargo = cargos_cache.get(sq_cand) or (candidato_info_cache_csv.get(sq_cand, {}).get('cargo'))
                    if not cargo: continue

                    is_federal_or_state = cargo.upper() in ['PRESIDENTE', 'VICE-PRESIDENTE', 'SENADOR', 'DEPUTADO FEDERAL', 'DEPUTADO ESTADUAL', 'DEPUTADO DISTRITAL']
                    
                    if is_federal_or_state:
                        ano = candidato_info_cache_csv[sq_cand]['ano']
                        insert_votos_municipio_buffer.extend([(sq_cand, ano, cidade, votos) for cidade, votos in cidades_votos_map.items()])
                        federal_state_sq_cands.add(sq_cand) # Adiciona à lista de alvos
                    else:
                        # Para candidatos municipais, o total de votos é a soma na única cidade
                        total_votos_municipal = sum(cidades_votos_map.values())
                        # Assume-se que um candidato municipal só concorre em uma cidade
                        cidade_candidatura = next(iter(cidades_votos_map.keys()))
                        update_votos_candidatura_municipal_buffer.append((total_votos_municipal, sq_cand, cidade_candidatura))

                if insert_votos_municipio_buffer:
                    cursor.executemany("INSERT OR REPLACE INTO votos_por_municipio (sq_candidato, ano_eleicao, cidade, votos) VALUES (?, ?, ?, ?)", insert_votos_municipio_buffer)
                
                if update_votos_candidatura_municipal_buffer:
                    cursor.executemany("UPDATE candidaturas SET votos = ? WHERE sq_candidato = ? AND cidade = ?", update_votos_candidatura_municipal_buffer)

                # --- FASE FINAL: Atualização focada e correta ---
                progress_win.after(0, lambda: progress_win.update_progress("Fase 3/3: Consolidando totais de votos...", 0.85))
                if progress_win.stop_event.is_set(): raise InterruptedError

                if federal_state_sq_cands:
                    params = list(federal_state_sq_cands)
                    update_totals_buffer = []
                    for sq_cand in params:
                        cursor.execute("SELECT SUM(votos) FROM votos_por_municipio WHERE sq_candidato = ?", (sq_cand,))
                        total_votos = cursor.fetchone()[0] or 0
                        update_totals_buffer.append((total_votos, sq_cand, ano_eleicao_arquivo))

                    if update_totals_buffer:
                        cursor.executemany(
                            "UPDATE candidaturas SET votos = ? WHERE sq_candidato = ? AND ano_eleicao = ?",
                            update_totals_buffer
                        )
                
                cursor.execute("PRAGMA foreign_keys = ON")

            progress_win.after(0, lambda: progress_win.operation_finished("Importação de votos concluída com sucesso!"))
        
        except InterruptedError:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada pelo usuário."))
        except Exception as e:
            try: cursor.execute("PRAGMA foreign_keys = ON")
            except: pass
            logging.error(f"Erro durante a importação do CSV de votação: {e}", exc_info=True)
            progress_win.after(0, lambda err=e: progress_win.operation_finished("", f"Erro inesperado: {err}"))


    # def importar_csv_eleicao(self, filepath: str, progress_win):
    #     try:
    #         class InterruptedError(Exception): pass

    #         progress_win.after(0, lambda: progress_win.update_progress("Fase 1/2: Contando linhas do arquivo CSV...", 0.0))
            
    #         with open(filepath, 'r', encoding='latin-1') as f:
    #             total_rows = sum(1 for line in f) - 1
            
    #         if progress_win.stop_event.is_set(): raise InterruptedError
            
    #         progress_win.after(0, lambda: progress_win.update_progress("Fase 1/2: Lendo e agregando votos...", 0.05))

    #         votos_agregados = defaultdict(lambda: defaultdict(int))
    #         candidato_info_cache_csv = {}
    #         ano_eleicao_arquivo = None

    #         with open(filepath, 'r', encoding='latin-1') as f:
    #             reader = csv.DictReader(f, delimiter=';')
    #             header = [h.strip().upper().replace('"', '') for h in reader.fieldnames]
    #             reader.fieldnames = header

    #             for i, row in enumerate(reader):
    #                 if i > 0 and i % 5000 == 0:
    #                     if progress_win.stop_event.is_set(): raise InterruptedError
    #                     progress = (i / total_rows) * 0.5 if total_rows > 0 else 0
    #                     progress_win.after(0, lambda r=i, t=total_rows, p=progress: progress_win.update_progress(f"Lendo linha {r:,} de {t:,}", p))

    #                 norm_row = {k.replace('"', ''): v.strip().replace('"', '') if v else '' for k, v in row.items()}
    #                 sq_cand = norm_row.get('SQ_CANDIDATO')
    #                 cidade_original = norm_row.get('NM_MUNICIPIO')
    #                 cidade_key = data_helpers.normalize_city_key(cidade_original)
    #                 if not ano_eleicao_arquivo: ano_eleicao_arquivo = data_helpers.safe_int(norm_row.get('ANO_ELEICAO'))
    #                 if not sq_cand or not cidade_key: continue
    #                 if sq_cand not in candidato_info_cache_csv: candidato_info_cache_csv[sq_cand] = {'cargo': norm_row.get('DS_CARGO'),'ano': ano_eleicao_arquivo}
    #                 votos_agregados[sq_cand][cidade_key] += data_helpers.safe_int(norm_row.get('QT_VOTOS_NOMINAIS'))

    #         with self.conn:
    #             cursor = self.conn.cursor()
                
    #             # --- CORREÇÃO AQUI: Desabilita a verificação de chave estrangeira temporariamente ---
    #             cursor.execute("PRAGMA foreign_keys = OFF")
                
    #             progress_win.after(0, lambda: progress_win.update_progress("Fase 2/2: Salvando votos no banco de dados...", 0.5))
                
    #             cursor.execute("SELECT sq_candidato, cargo FROM candidaturas WHERE ano_eleicao = ?", (ano_eleicao_arquivo,))
    #             cargos_cache = {row['sq_candidato']: row['cargo'] for row in cursor.fetchall()}
    #             total_candidatos = len(votos_agregados)
                
    #             for idx, (sq_cand, cidades_votos_map) in enumerate(votos_agregados.items()):
    #                 if idx > 0 and idx % 200 == 0:
    #                     if progress_win.stop_event.is_set(): raise InterruptedError
    #                     progress = 0.5 + (idx / total_candidatos) * 0.5 if total_candidatos > 0 else 0.5
    #                     progress_win.after(0, lambda i=idx, t=total_candidatos, p=progress: progress_win.update_progress("Salvando no banco...", p, f"Candidato {i}/{t}"))
                    
    #                 cargo = cargos_cache.get(sq_cand) or (candidato_info_cache_csv.get(sq_cand, {}).get('cargo'))
    #                 if not cargo:
    #                     logging.warning(f"Candidato com SQ {sq_cand} do CSV de votação não encontrado na base de candidaturas. Pulando votos.")
    #                     continue
                    
    #                 is_federal_or_state = cargo.upper() in ['PRESIDENTE', 'VICE-PRESIDENTE', 'SENADOR', 'DEPUTADO FEDERAL', 'DEPUTADO ESTADUAL', 'DEPUTADO DISTRITAL']
    #                 if is_federal_or_state:
    #                     ano = candidato_info_cache_csv[sq_cand]['ano']
    #                     data_to_insert = [(sq_cand, ano, cidade, votos) for cidade, votos in cidades_votos_map.items()]
    #                     cursor.executemany("INSERT OR REPLACE INTO votos_por_municipio (sq_candidato, ano_eleicao, cidade, votos) VALUES (?, ?, ?, ?)", data_to_insert)
    #                     cursor.execute("SELECT SUM(votos) FROM votos_por_municipio WHERE sq_candidato = ?", (sq_cand,))
    #                     total_geral_votos = cursor.fetchone()[0] or 0
    #                     cursor.execute("UPDATE candidaturas SET votos = ? WHERE sq_candidato = ?", (total_geral_votos, sq_cand))
    #                 else:
    #                     for cidade_key, total_votos in cidades_votos_map.items():
    #                         cursor.execute("UPDATE candidaturas SET votos = ? WHERE sq_candidato = ? AND cidade = ?", (total_votos, sq_cand, cidade_key))

    #             # --- CORREÇÃO AQUI: Reabilita a verificação de chave estrangeira ---
    #             cursor.execute("PRAGMA foreign_keys = ON")

    #         progress_win.after(0, lambda: progress_win.operation_finished("Importação de votos concluída com sucesso!"))
        
    #     except InterruptedError:
    #         progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada pelo usuário."))
    #     except Exception as e:
    #         # Garante que as chaves estrangeiras sejam reativadas mesmo em caso de erro
    #         try:
    #             cursor = self.conn.cursor()
    #             cursor.execute("PRAGMA foreign_keys = ON")
    #         except: pass
    #         logging.error(f"Erro durante a importação do CSV de votação: {e}", exc_info=True)
    #         progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro inesperado durante a importação: {e}"))

    def importar_dados_cadastrais(self, filepath: str, progress_win):
        try:
            class InterruptedError(Exception): pass
            
            with self.conn:
                cursor = self.conn.cursor()

                progress_win.after(0, lambda: progress_win.update_progress("Fase 1/4: Carregando dados existentes...", 0.05))
                # Otimização: Carrega todos os dados de uma vez para consulta em memória
                cursor.execute("SELECT * FROM pessoas")
                all_people_data = {row['id_pessoa']: dict(row) for row in cursor.fetchall()}
                
                # Cria mapas de lookup a partir dos dados em memória
                titulo_map = {p['titulo_eleitor']: p['id_pessoa'] for p in all_people_data.values() if p.get('titulo_eleitor')}
                cpf_map = {p['cpf']: p['id_pessoa'] for p in all_people_data.values() if p.get('cpf')}
                nome_nasc_map = {f"{p['nome']}_{p['data_nascimento']}": p['id_pessoa'] for p in all_people_data.values() if p.get('nome') and p.get('data_nascimento')}

                prof_cache = {row['nome']: row['id'] for row in self.misc_repo.get_lookup_table_data("profissoes")}
                escol_cache = {row['nome']: row['id'] for row in self.misc_repo.get_lookup_table_data("escolaridades")}
                
                if progress_win.stop_event.is_set(): raise InterruptedError

                progress_win.after(0, lambda: progress_win.update_progress("Fase 2/4: Lendo arquivo CSV...", 0.2))
                with open(filepath, 'r', encoding='latin-1') as f:
                    csv_data = list(csv.DictReader(f, delimiter=';'))
                
                pessoas_para_inserir = []
                # --- NOVO: Lista para guardar as atualizações ---
                pessoas_para_atualizar = []
                candidaturas_para_inserir = []
                
                inserts_count = 0
                updates_count = 0

                total_rows = len(csv_data)
                progress_win.after(0, lambda: progress_win.update_progress("Fase 3/4: Processando contatos...", 0.4))
                
                for i, row in enumerate(csv_data):
                    if i > 0 and i % 500 == 0:
                        if progress_win.stop_event.is_set(): raise InterruptedError
                        progress = 0.4 + (i / total_rows) * 0.4
                        progress_win.after(0, lambda p=progress, i=i, t=total_rows: progress_win.update_progress(f"Processando linha {i}/{t}", p))

                    norm_row = data_helpers.normalize_csv_row(row)
                    titulo_csv = norm_row.get('NR_TITULO_ELEITORAL_CANDIDATO') or None
                    cpf_csv = norm_row.get('NR_CPF_CANDIDATO') or None
                    nome_csv = norm_row.get('NM_CANDIDATO')
                    nasc_csv = norm_row.get('DT_NASCIMENTO')
                    
                    if not nome_csv: continue
                    
                    id_pessoa = None
                    if titulo_csv: id_pessoa = titulo_map.get(titulo_csv)
                    if not id_pessoa and cpf_csv: id_pessoa = cpf_map.get(cpf_csv)
                    if not id_pessoa and nome_csv and nasc_csv:
                        composite_key = f"{nome_csv}_{nasc_csv}"
                        id_pessoa = nome_nasc_map.get(composite_key)

                    id_pessoa_ref = id_pessoa
                    
                    if not id_pessoa:
                        # Lógica para CRIAR uma nova pessoa (inalterada)
                        dados_pessoa = {
                            'nome': nome_csv, 'apelido': norm_row.get('NM_URNA_CANDIDATO'),'cpf': cpf_csv, 'titulo_eleitor': titulo_csv, 
                            'data_nascimento': nasc_csv,'genero': norm_row.get('DS_GENERO'), 'email': norm_row.get('DS_EMAIL'),
                            'id_profissao': self._get_or_create_lookup_id(cursor, 'profissoes', norm_row.get('DS_OCUPACAO'), prof_cache),
                            'id_escolaridade': self._get_or_create_lookup_id(cursor, 'escolaridades', norm_row.get('DS_GRAU_INSTRUCAO'), escol_cache),
                        }
                        pessoas_para_inserir.append(dados_pessoa)
                        id_pessoa_ref = dados_pessoa 
                        inserts_count += 1
                        # Atualiza os mapas em memória para evitar duplicatas dentro do mesmo arquivo
                        if titulo_csv: titulo_map[titulo_csv] = id_pessoa_ref
                        if cpf_csv: cpf_map[cpf_csv] = id_pessoa_ref
                        if nome_csv and nasc_csv: nome_nasc_map[f"{nome_csv}_{nasc_csv}"] = id_pessoa_ref
                    else:
                        # --- NOVO: Bloco para ATUALIZAR uma pessoa existente ---
                        existing_person_data = all_people_data.get(id_pessoa, {})
                        dados_para_atualizar = {}

                        # Verifica se o CPF pode ser adicionado/atualizado
                        if cpf_csv and not existing_person_data.get('cpf'):
                            dados_para_atualizar['cpf'] = cpf_csv
                        
                        # Verifica se o Título de Eleitor pode ser adicionado/atualizado
                        if titulo_csv and not existing_person_data.get('titulo_eleitor'):
                            dados_para_atualizar['titulo_eleitor'] = titulo_csv
                        
                        # Adiciona outros campos que podem ser enriquecidos
                        if norm_row.get('DS_EMAIL') and not existing_person_data.get('email'):
                             dados_para_atualizar['email'] = norm_row.get('DS_EMAIL')

                        if dados_para_atualizar:
                            pessoas_para_atualizar.append({'id_pessoa': id_pessoa, 'data': dados_para_atualizar})
                            updates_count += 1
                            # Atualiza os dados em memória para consistência
                            all_people_data[id_pessoa].update(dados_para_atualizar)

                    cidade_key = data_helpers.normalize_city_key(norm_row.get('NM_UE'))
                    dados_candidatura = {
                        'id_pessoa_ref': id_pessoa_ref,
                        'ano_eleicao': data_helpers.safe_int(norm_row.get('ANO_ELEICAO')),'sq_candidato': norm_row.get('SQ_CANDIDATO'),
                        'nome_urna': norm_row.get('NM_URNA_CANDIDATO'),'numero_urna': norm_row.get('NR_CANDIDATO'),
                        'partido': norm_row.get('SG_PARTIDO'),'cargo': norm_row.get('DS_CARGO'),'cidade': cidade_key,
                        'uf': norm_row.get('SG_UF'),'situacao': norm_row.get('DS_SIT_TOT_TURNO')
                    }
                    candidaturas_para_inserir.append(dados_candidatura)
                
                if progress_win.stop_event.is_set(): raise InterruptedError
                
                progress_win.after(0, lambda: progress_win.update_progress("Fase 4/4: Salvando dados no banco...", 0.85))

                # --- Executa as inserções ---
                if pessoas_para_inserir:
                    for p_data in pessoas_para_inserir:
                        cols = ', '.join(p_data.keys()); placeholders = ', '.join([f":{k}" for k in p_data.keys()])
                        cursor.execute(f"INSERT INTO pessoas ({cols}) VALUES ({placeholders})", p_data)
                        p_data['id_pessoa'] = cursor.lastrowid

                # --- NOVO: Executa as atualizações ---
                if pessoas_para_atualizar:
                    for update_info in pessoas_para_atualizar:
                        set_clauses = ', '.join([f"{k} = ?" for k in update_info['data'].keys()])
                        params = list(update_info['data'].values()) + [update_info['id_pessoa']]
                        cursor.execute(f"UPDATE pessoas SET {set_clauses} WHERE id_pessoa = ?", tuple(params))

                # --- Vincula candidaturas ---
                final_candidaturas = []
                for c_data in candidaturas_para_inserir:
                    id_ref = c_data.pop('id_pessoa_ref')
                    c_data['id_pessoa'] = id_ref['id_pessoa'] if isinstance(id_ref, dict) else id_ref
                    final_candidaturas.append(c_data)

                if final_candidaturas:
                    cols = ', '.join(final_candidaturas[0].keys()); placeholders = ', '.join([f":{k}" for k in final_candidaturas[0].keys()])
                    cursor.executemany(f"INSERT OR IGNORE INTO candidaturas ({cols}) VALUES ({placeholders})", final_candidaturas)

            success_msg = (
                f"Importação cadastral concluída!\n"
                f"- {inserts_count} novos contatos criados.\n"
                f"- {updates_count} contatos existentes atualizados.\n"
                f"- {len(candidaturas_para_inserir)} candidaturas processadas."
            )
            progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
        except InterruptedError:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada pelo usuário."))
        except sqlite3.IntegrityError as ie:
            logging.error(f"Erro de integridade durante a importação cadastral: {ie}", exc_info=True)
            progress_win.after(0, lambda e=ie: progress_win.operation_finished("", f"Erro de Duplicata: {e}"))
        except Exception as e:
            logging.error(f"Erro durante a importação cadastral: {e}", exc_info=True)
            progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro: {e}"))

    # def importar_dados_cadastrais(self, filepath: str, progress_win):
    #     try:
    #         class InterruptedError(Exception): pass
            
    #         with self.conn:
    #             cursor = self.conn.cursor()

    #             progress_win.after(0, lambda: progress_win.update_progress("Fase 1/3: Carregando dados existentes...", 0.1))
    #             cursor.execute("SELECT titulo_eleitor, id_pessoa FROM pessoas WHERE titulo_eleitor IS NOT NULL AND titulo_eleitor != ''"); titulo_map = {r['titulo_eleitor']: r['id_pessoa'] for r in cursor.fetchall()}
    #             cursor.execute("SELECT cpf, id_pessoa FROM pessoas WHERE cpf IS NOT NULL AND cpf != ''"); cpf_map = {r['cpf']: r['id_pessoa'] for r in cursor.fetchall()}
    #             cursor.execute("SELECT nome, data_nascimento, id_pessoa FROM pessoas WHERE nome IS NOT NULL AND data_nascimento IS NOT NULL AND data_nascimento != ''"); nome_nasc_map = {f"{r['nome']}_{r['data_nascimento']}": r['id_pessoa'] for r in cursor.fetchall()}
                
    #             prof_cache = {row['nome']: row['id'] for row in self.misc_repo.get_lookup_table_data("profissoes")}
    #             escol_cache = {row['nome']: row['id'] for row in self.misc_repo.get_lookup_table_data("escolaridades")}
                
    #             if progress_win.stop_event.is_set(): raise InterruptedError

    #             progress_win.after(0, lambda: progress_win.update_progress("Fase 2/3: Lendo arquivo CSV...", 0.3))
    #             with open(filepath, 'r', encoding='latin-1') as f:
    #                 csv_data = list(csv.DictReader(f, delimiter=';'))
                
    #             pessoas_para_inserir = []
    #             candidaturas_para_inserir = []
    #             inserts_count = 0

    #             progress_win.after(0, lambda: progress_win.update_progress("Fase 3/3: Processando contatos em memória...", 0.5))
    #             for i, row in enumerate(csv_data):
    #                 if i > 0 and i % 1000 == 0:
    #                     if progress_win.stop_event.is_set(): raise InterruptedError
                        
    #                 norm_row = data_helpers.normalize_csv_row(row)
    #                 titulo = norm_row.get('NR_TITULO_ELEITORAL_CANDIDATO') or None
    #                 cpf = norm_row.get('NR_CPF_CANDIDATO') or None
    #                 nome = norm_row.get('NM_CANDIDATO')
    #                 nasc = norm_row.get('DT_NASCIMENTO')
                    
    #                 if not nome: continue
                    
    #                 id_pessoa = None
    #                 if titulo: id_pessoa = titulo_map.get(titulo)
    #                 if not id_pessoa and cpf: id_pessoa = cpf_map.get(cpf)
    #                 if not id_pessoa and nome and nasc:
    #                     composite_key = f"{nome}_{nasc}"
    #                     id_pessoa = nome_nasc_map.get(composite_key)

    #                 id_pessoa_ref = id_pessoa
                    
    #                 if not id_pessoa:
    #                     dados_pessoa = {
    #                         'nome': nome, 'apelido': norm_row.get('NM_URNA_CANDIDATO'),'cpf': cpf, 'titulo_eleitor': titulo, 
    #                         'data_nascimento': nasc,'genero': norm_row.get('DS_GENERO'), 'email': norm_row.get('DS_EMAIL'),
    #                         'id_profissao': self._get_or_create_lookup_id(cursor, 'profissoes', norm_row.get('DS_OCUPACAO'), prof_cache),
    #                         'id_escolaridade': self._get_or_create_lookup_id(cursor, 'escolaridades', norm_row.get('DS_GRAU_INSTRUCAO'), escol_cache),
    #                     }
    #                     pessoas_para_inserir.append(dados_pessoa)
                        
    #                     id_pessoa_ref = dados_pessoa 
    #                     inserts_count += 1
                        
    #                     if titulo: titulo_map[titulo] = id_pessoa_ref
    #                     if cpf: cpf_map[cpf] = id_pessoa_ref
    #                     if nome and nasc: nome_nasc_map[f"{nome}_{nasc}"] = id_pessoa_ref

    #                 cidade_key = data_helpers.normalize_city_key(norm_row.get('NM_UE'))
    #                 dados_candidatura = {
    #                     'id_pessoa_ref': id_pessoa_ref,
    #                     'ano_eleicao': data_helpers.safe_int(norm_row.get('ANO_ELEICAO')),'sq_candidato': norm_row.get('SQ_CANDIDATO'),
    #                     'nome_urna': norm_row.get('NM_URNA_CANDIDATO'),'numero_urna': norm_row.get('NR_CANDIDATO'),
    #                     'partido': norm_row.get('SG_PARTIDO'),'cargo': norm_row.get('DS_CARGO'),'cidade': cidade_key,
    #                     'uf': norm_row.get('SG_UF'),'situacao': norm_row.get('DS_SIT_TOT_TURNO')
    #                 }
    #                 candidaturas_para_inserir.append(dados_candidatura)
                
    #             if progress_win.stop_event.is_set(): raise InterruptedError
                
    #             progress_win.after(0, lambda: progress_win.update_progress("Salvando novas pessoas no banco...", 0.8))
    #             if pessoas_para_inserir:
    #                 for p_data in pessoas_para_inserir:
    #                     cols = ', '.join(p_data.keys()); placeholders = ', '.join([f":{k}" for k in p_data.keys()])
    #                     cursor.execute(f"INSERT INTO pessoas ({cols}) VALUES ({placeholders})", p_data)
    #                     p_data['id_pessoa'] = cursor.lastrowid

    #             progress_win.after(0, lambda: progress_win.update_progress("Vinculando candidaturas...", 0.9))
    #             final_candidaturas = []
    #             for c_data in candidaturas_para_inserir:
    #                 id_ref = c_data.pop('id_pessoa_ref')
    #                 c_data['id_pessoa'] = id_ref['id_pessoa'] if isinstance(id_ref, dict) else id_ref
    #                 final_candidaturas.append(c_data)

    #             if final_candidaturas:
    #                 cols = ', '.join(final_candidaturas[0].keys()); placeholders = ', '.join([f":{k}" for k in final_candidaturas[0].keys()])
    #                 cursor.executemany(f"INSERT OR IGNORE INTO candidaturas ({cols}) VALUES ({placeholders})", final_candidaturas)

    #         success_msg = f"Importação cadastral concluída!\n- {inserts_count} novos contatos criados.\n- {len(candidaturas_para_inserir)} candidaturas processadas."
    #         progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
    #     except InterruptedError:
    #         progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada pelo usuário."))
    #     except sqlite3.IntegrityError as ie:
    #         logging.error(f"Erro de integridade durante a importação cadastral: {ie}", exc_info=True)
    #         progress_win.after(0, lambda e=ie: progress_win.operation_finished("", f"Erro de Duplicata: {e}"))
    #     except Exception as e:
    #         logging.error(f"Erro durante a importação cadastral: {e}", exc_info=True)
    #         progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro: {e}"))            

    # def sincronizar_cidades_contatos(self, progress_win):
    #     try:
    #         class InterruptedError(Exception): pass

    #         with self.conn:
    #             cursor = self.conn.cursor()
                
    #             # FASE 1: Buscar todos os dados necessários em uma única consulta otimizada.
    #             # Esta consulta é o coração da nova lógica.
    #             progress_win.after(0, lambda: progress_win.update_progress("Fase 1/2: Buscando dados de localização mais recentes...", 0.1))
    #             if progress_win.stop_event.is_set(): raise InterruptedError
                
    #             query = """
    #                 SELECT 
    #                     p.id_pessoa,
    #                     m.cidade AS cidade_formatada,
    #                     m.uf AS uf_formatada
    #                 FROM 
    #                     pessoas p
    #                 JOIN (
    #                     -- Subquery para encontrar a candidatura mais recente de cada pessoa
    #                     SELECT 
    #                         id_pessoa, 
    #                         cidade,
    #                         uf,
    #                         ROW_NUMBER() OVER(PARTITION BY id_pessoa ORDER BY ano_eleicao DESC) as rn
    #                     FROM 
    #                         candidaturas
    #                     WHERE 
    #                         cidade IS NOT NULL AND cidade != ''
    #                 ) AS ultima_candidatura ON p.id_pessoa = ultima_candidatura.id_pessoa
    #                 JOIN 
    #                     municipios m ON ultima_candidatura.cidade = m.cidade_key
    #                 WHERE 
    #                     ultima_candidatura.rn = 1 
    #                     AND (p.cidade IS NULL OR p.cidade = '' OR p.uf IS NULL OR p.uf = '');
    #             """
    #             cursor.execute(query)
    #             data_to_update = [
    #                 (row['cidade_formatada'], row['uf_formatada'], row['id_pessoa']) 
    #                 for row in cursor.fetchall()
    #             ]

    #             if not data_to_update:
    #                 progress_win.after(0, lambda: progress_win.operation_finished("Nenhum contato elegível para sincronização foi encontrado."))
    #                 return

    #             # FASE 2: Atualizar todos os registros em lote.
    #             total_to_update = len(data_to_update)
    #             progress_win.after(0, lambda: progress_win.update_progress(f"Fase 2/2: Salvando {total_to_update} atualizações no banco...", 0.6))
    #             if progress_win.stop_event.is_set(): raise InterruptedError

    #             update_query = "UPDATE pessoas SET cidade = ?, uf = ? WHERE id_pessoa = ?"
                
    #             # Para fornecer feedback, podemos dividir em lotes
    #             batch_size = 500
    #             updated_count = 0
    #             for i in range(0, total_to_update, batch_size):
    #                 if progress_win.stop_event.is_set(): raise InterruptedError
                    
    #                 batch = data_to_update[i:i + batch_size]
    #                 cursor.executemany(update_query, batch)
                    
    #                 updated_count += len(batch)
    #                 progress = 0.6 + (updated_count / total_to_update) * 0.4
    #                 progress_win.after(0, lambda p=progress, i=updated_count, t=total_to_update: progress_win.update_progress(f"Salvando {i}/{t}...", p))

    #             rows_affected = cursor.rowcount if total_to_update < batch_size else updated_count
                
    #         success_msg = f"Sincronização concluída! {rows_affected} contatos foram atualizados com sua cidade e UF mais recentes."
    #         progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
    #     except InterruptedError:
    #         progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada pelo usuário."))
    #     except Exception as e:
    #         logging.error(f"Erro ao sincronizar cidades: {e}", exc_info=True)
    #         progress_win.after(0, lambda err=e: progress_win.operation_finished("", f"Erro inesperado: {err}"))
            
    def sincronizar_cidades_contatos(self, progress_win):
        try:
            class InterruptedError(Exception): pass

            with self.conn:
                cursor = self.conn.cursor()
                
                # --- FASE 1: Mapear a última candidatura de cada pessoa (rápido) ---
                progress_win.after(0, lambda: progress_win.update_progress("Fase 1/4: Mapeando candidaturas...", 0.05))
                if progress_win.stop_event.is_set(): raise InterruptedError
                
                # Usamos ROW_NUMBER() para eficientemente pegar a última candidatura de cada pessoa
                query_candidaturas = """
                    SELECT id_pessoa, cidade
                    FROM (
                        SELECT id_pessoa, cidade, ROW_NUMBER() OVER (PARTITION BY id_pessoa ORDER BY ano_eleicao DESC) as rn
                        FROM candidaturas
                        WHERE cidade IS NOT NULL AND cidade != ''
                    )
                    WHERE rn = 1;
                """
                cursor.execute(query_candidaturas)
                person_id_to_city_key_map = {row['id_pessoa']: row['cidade'] for row in cursor.fetchall()}

                # --- FASE 2: Criar um cache de cidades (muito rápido) ---
                progress_win.after(0, lambda: progress_win.update_progress("Fase 2/4: Mapeando municípios (cache)...", 0.15))
                if progress_win.stop_event.is_set(): raise InterruptedError

                cursor.execute("SELECT cidade_key, cidade FROM municipios")
                city_key_to_name_map = {row['cidade_key']: row['cidade'] for row in cursor.fetchall()}

                # --- FASE 3: Identificar quem precisa de atualização (rápido) ---
                progress_win.after(0, lambda: progress_win.update_progress("Fase 3/4: Identificando contatos para atualizar...", 0.25))
                if progress_win.stop_event.is_set(): raise InterruptedError
                
                cursor.execute("SELECT id_pessoa FROM pessoas WHERE (cidade IS NULL OR cidade = '')")
                ids_to_update = {row['id_pessoa'] for row in cursor.fetchall()}
                
                if not ids_to_update:
                    progress_win.after(0, lambda: progress_win.operation_finished("Nenhum contato com cidade vazia para sincronizar."))
                    return

                # --- FASE 4: Processar em memória e preparar para salvar (aqui damos o feedback) ---
                progress_win.after(0, lambda: progress_win.update_progress("Fase 4/4: Preparando atualizações...", 0.40))
                
                data_for_update = []
                total_to_process = len(ids_to_update)
                processed_count = 0
                
                for person_id in ids_to_update:
                    if progress_win.stop_event.is_set(): raise InterruptedError

                    city_key = person_id_to_city_key_map.get(person_id)
                    if city_key:
                        # Busca no cache de cidades o nome formatado
                        city_name = city_key_to_name_map.get(city_key)
                        if city_name:
                            data_for_update.append((city_name, person_id))
                    
                    processed_count += 1
                    if processed_count % 100 == 0: # Atualiza a UI a cada 100 contatos
                        progress = 0.40 + (processed_count / total_to_process) * 0.50
                        progress_win.after(0, lambda p=progress, i=processed_count, t=total_to_process: progress_win.update_progress(f"Processando {i}/{t}...", p))

                if not data_for_update:
                    progress_win.after(0, lambda: progress_win.operation_finished("Nenhum contato elegível para sincronização foi encontrado."))
                    return

                # --- SALVAMENTO: Executa todos os updates de uma vez (muito rápido) ---
                progress_win.after(0, lambda: progress_win.update_progress("Salvando alterações no banco de dados...", 0.95))
                if progress_win.stop_event.is_set(): raise InterruptedError

                update_query = "UPDATE pessoas SET cidade = ? WHERE id_pessoa = ?"
                cursor.executemany(update_query, data_for_update)
                rows_affected = cursor.rowcount

            success_msg = f"Sincronização concluída! {rows_affected} contatos foram atualizados."
            progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
        except InterruptedError:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada pelo usuário."))
        except Exception as e:
            logging.error(f"Erro ao sincronizar cidades: {e}", exc_info=True)
            progress_win.after(0, lambda err=e: progress_win.operation_finished("", f"Erro inesperado: {err}"))

    def corrigir_duplicatas_de_pessoas(self, progress_win):
        try:
            class InterruptedError(Exception): pass
            
            cursor = self.conn.cursor()
            try:
                with self.conn:
                    cursor.execute("PRAGMA foreign_keys = OFF")

                    progress_win.after(0, lambda: progress_win.update_progress("Fase 1/3: Buscando e agrupando contatos...", 0.1))
                    cursor.execute("SELECT * FROM pessoas"); todas_as_pessoas = [dict(row) for row in cursor.fetchall()]
                    
                    grupos = defaultdict(set)
                    for pessoa in todas_as_pessoas:
                        cpf = pessoa.get('cpf')
                        titulo = pessoa.get('titulo_eleitor')
                        nome = pessoa.get('nome')
                        nasc = pessoa.get('data_nascimento')
                        if cpf: grupos[f"cpf_{cpf}"].add(pessoa['id_pessoa'])
                        if titulo: grupos[f"titulo_{titulo}"].add(pessoa['id_pessoa'])
                        if nome and nasc:
                            nome_normalizado = data_helpers.normalize_city_key(nome)
                            grupos[f"nome_nasc_{nome_normalizado}_{nasc}"].add(pessoa['id_pessoa'])
                    
                    if progress_win.stop_event.is_set(): raise InterruptedError
                    
                    progress_win.after(0, lambda: progress_win.update_progress("Fase 2/3: Consolidando grupos de duplicatas...", 0.4))
                    id_para_grupo_final = {}
                    grupo_id_counter = 0
                    for ids_grupo in grupos.values():
                        if len(ids_grupo) < 2: continue
                        conjunto_de_grupos_associados = {id_para_grupo_final.get(id_pessoa) for id_pessoa in ids_grupo if id_pessoa in id_para_grupo_final}
                        
                        if not conjunto_de_grupos_associados:
                            id_novo_grupo = grupo_id_counter; grupo_id_counter += 1
                        else:
                            id_novo_grupo = min(conjunto_de_grupos_associados)

                        for id_pessoa in ids_grupo:
                            grupo_existente = id_para_grupo_final.get(id_pessoa)
                            if grupo_existente is not None and grupo_existente != id_novo_grupo:
                                grupo_a_ser_mesclado = grupo_existente
                                for id_p, id_g in id_para_grupo_final.items():
                                    if id_g == grupo_a_ser_mesclado: id_para_grupo_final[id_p] = id_novo_grupo
                            id_para_grupo_final[id_pessoa] = id_novo_grupo
                    
                    grupos_consolidados = defaultdict(list)
                    for id_pessoa, id_grupo in id_para_grupo_final.items():
                        grupos_consolidados[id_grupo].append(id_pessoa)
                    grupos_para_fusao = [sorted(g) for g in grupos_consolidados.values() if len(g) > 1]
                    
                    if progress_win.stop_event.is_set(): raise InterruptedError

                    total_grupos, registros_fundidos = len(grupos_para_fusao), 0
                    progress_win.after(0, lambda: progress_win.update_progress(f"Fase 3/3: Fundindo {total_grupos} grupos...", 0.6))

                    for i, ids_grupo in enumerate(grupos_para_fusao):
                        if progress_win.stop_event.is_set(): break
                        progress = 0.6 + (i / total_grupos) * 0.4 if total_grupos > 0 else 0.6
                        progress_win.after(0, lambda i=i,t=total_grupos,p=progress: progress_win.update_progress(f"Corrigindo grupo {i+1}/{t}...", p))

                        pessoas_no_grupo = [p for p in todas_as_pessoas if p['id_pessoa'] in ids_grupo]
                        
                        master_pessoa_ref = next((p for p in pessoas_no_grupo if p.get('cpf')), None)
                        if not master_pessoa_ref: master_pessoa_ref = next((p for p in pessoas_no_grupo if p.get('titulo_eleitor')), None)
                        if not master_pessoa_ref: master_pessoa_ref = pessoas_no_grupo[0]
                        
                        mestre_dados = dict(master_pessoa_ref)
                        id_mestre = mestre_dados['id_pessoa']
                        ids_para_deletar = [p['id_pessoa'] for p in pessoas_no_grupo if p['id_pessoa'] != id_mestre]
                        
                        unique_cols = {'cpf', 'titulo_eleitor'}
                        
                        for id_duplicado in ids_para_deletar:
                            duplicado_dados = next((p for p in todas_as_pessoas if p['id_pessoa'] == id_duplicado), {})
                            for col, val in duplicado_dados.items():
                                if col != 'id_pessoa' and not mestre_dados.get(col) and val:
                                    can_merge = True
                                    if col in unique_cols:
                                        placeholders_check = ', '.join(['?'] * len(ids_grupo))
                                        check_query = f"SELECT 1 FROM pessoas WHERE {col} = ? AND id_pessoa NOT IN ({placeholders_check}) LIMIT 1"
                                        params_check = (val, *ids_grupo)
                                        cursor.execute(check_query, params_check)
                                        if cursor.fetchone():
                                            can_merge = False
                                            logging.warning(f"Não foi possível fundir o valor '{val}' para a coluna '{col}' no registro mestre {id_mestre} pois ele já existe em outro registro não relacionado.")
                                    if can_merge:
                                        mestre_dados[col] = val

                        mestre_dados.pop('id_pessoa', None)
                        set_clauses = ', '.join([f"{k} = ?" for k in mestre_dados.keys()]); sql_upd = f"UPDATE pessoas SET {set_clauses} WHERE id_pessoa = ?"; cursor.execute(sql_upd, (*mestre_dados.values(), id_mestre))
                        
                        # --- CORREÇÃO AQUI: Estrutura de dados e loop corrigidos ---
                        tabelas_para_atualizar = {
                            'candidaturas': 'id_pessoa',
                            'atendimentos': 'id_pessoa',
                            'pessoa_listas_assoc': 'id_pessoa',
                            'pessoa_tags_assoc': 'id_pessoa',
                            'relacionamentos': ['id_pessoa_origem', 'id_pessoa_destino']
                        }
                        placeholders = ', '.join(['?'] * len(ids_para_deletar))
                        
                        for tab_name, col_data in tabelas_para_atualizar.items():
                            if isinstance(col_data, list): # Caso especial para relacionamentos
                                for col in col_data:
                                    cursor.execute(f"UPDATE {tab_name} SET {col} = ? WHERE {col} IN ({placeholders})", (id_mestre, *ids_para_deletar))
                            else: # Caso normal
                                col = col_data
                                cursor.execute(f"UPDATE {tab_name} SET {col} = ? WHERE {col} IN ({placeholders})", (id_mestre, *ids_para_deletar))
                                
                        cursor.execute(f"DELETE FROM pessoas WHERE id_pessoa IN ({placeholders})", tuple(ids_para_deletar)); registros_fundidos += len(ids_para_deletar)
                    
                if progress_win.stop_event.is_set(): raise InterruptedError
                
                success_msg = f"Correção concluída! {total_grupos} grupos de duplicatas encontrados e {registros_fundidos} registros fundidos."
                progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
            finally:
                cursor.execute("PRAGMA foreign_keys = ON")
                logging.info("Verificação de chaves estrangeiras reativada.")

        except InterruptedError:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada pelo usuário."))
        except Exception as e:
            logging.error(f"Erro ao corrigir duplicatas: {e}", exc_info=True)
            progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro: {e}"))

    def importar_prefeituras_eleitorado_csv(self, prefeituras_path, eleitorado_path, progress_win):
        try:
            class InterruptedError(Exception): pass
            
            with self.conn:
                cursor = self.conn.cursor()
                if progress_win.stop_event.is_set(): raise InterruptedError
                progress_win.after(0, lambda: progress_win.update_progress("Fase 1/2: Importando municípios...", 0.0))
                
                if os.path.exists(prefeituras_path):
                    with open(prefeituras_path, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f, delimiter=';')
                        municipios_data = [ { 'cidade_key': data_helpers.normalize_city_key(r.get('CIDADE')), 'cidade': r.get('CIDADE'), 'uf': 'SP', 'sg_ue': r.get('SG_UE'), 'cod_ibge': r.get('COD.IBGE'), 'populacao': data_helpers.safe_int(r.get('POPULACAO')), 'dens_demo': data_helpers.safe_int(r.get('DENS.DEMO'), None), 'gentilico': r.get('GENTILICO'), 'area': data_helpers.safe_int(r.get('AREA'), None), 'idhm_geral': data_helpers.safe_int(r.get('IDHM_GERAL'), None), 'idhm_long': data_helpers.safe_int(r.get('IDHM_LONG'), None), 'idhm_renda': data_helpers.safe_int(r.get('IDHM_RENDA'), None), 'idhm_educ': data_helpers.safe_int(r.get('IDHM_EDUC'), None), 'aniversario': r.get('ANIVERSARIO') } for r in (data_helpers.normalize_csv_row(row) for row in reader) if r.get('CIDADE') ]
                        cursor.executemany('INSERT OR REPLACE INTO municipios (cidade_key, cidade, uf, sg_ue, cod_ibge, populacao, dens_demo, gentilico, area, idhm_geral, idhm_long, idhm_renda, idhm_educ, aniversario) VALUES (:cidade_key, :cidade, :uf, :sg_ue, :cod_ibge, :populacao, :dens_demo, :gentilico, :area, :idhm_geral, :idhm_long, :idhm_renda, :idhm_educ, :aniversario)', municipios_data)

                if progress_win.stop_event.is_set(): raise InterruptedError
                progress_win.after(0, lambda: progress_win.update_progress("Fase 2/2: Atualizando eleitorado...", 0.5))
                
                if os.path.exists(eleitorado_path):
                    ano_eleitorado = data_helpers.safe_int(re.search(r'\d{4}', os.path.basename(eleitorado_path)).group(), 2024)
                    eleitorado_por_cidade = defaultdict(lambda: {'masculino': 0, 'feminino': 0, 'nao_informado': 0})
                    with open(eleitorado_path, 'r', encoding='latin-1') as f:
                        reader = csv.DictReader(f, delimiter=';')
                        for row in reader:
                            norm_row = data_helpers.normalize_csv_row(row)
                            cidade_normalizada = data_helpers.normalize_city_key(norm_row.get('CIDADE'))
                            genero, votos = norm_row.get('GENERO'), data_helpers.safe_int(norm_row.get('VOTOS'))
                            if genero == 'MASCULINO': eleitorado_por_cidade[cidade_normalizada]['masculino'] += votos
                            elif genero == 'FEMININO': eleitorado_por_cidade[cidade_normalizada]['feminino'] += votos
                            else: eleitorado_por_cidade[cidade_normalizada]['nao_informado'] += votos
                    
                    updates_para_fazer = []
                    for cidade_key, d in eleitorado_por_cidade.items():
                        cursor.execute("SELECT id FROM municipios WHERE cidade_key = ?", (cidade_key,))
                        municipio_res = cursor.fetchone()
                        if municipio_res:
                            updates_para_fazer.append({'id_municipio': municipio_res['id'], 'ano': ano_eleitorado, 'total': d['masculino'] + d['feminino'] + d['nao_informado'], 'mas': d['masculino'], 'fem': d['feminino'], 'ni': d['nao_informado']})
                    
                    if updates_para_fazer:
                        cursor.executemany('INSERT OR REPLACE INTO eleitorado (id_municipio, ano, total, masculino, feminino, nao_informado) VALUES (:id_municipio, :ano, :total, :mas, :fem, :ni)', updates_para_fazer)
                
            if progress_win.stop_event.is_set(): raise InterruptedError
            progress_win.after(0, lambda: progress_win.operation_finished("Importação concluída!"))
            
        except InterruptedError:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada."))
        except Exception as e:
            progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro: {e}"))

    def importar_orgaos_publicos_csv(self, filepath: str, progress_win):
            try:
                class InterruptedError(Exception): pass
                with self.conn:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        rows = list(csv.DictReader(f, delimiter=';'))
                    cursor = self.conn.cursor()
                    
                    total_rows = len(rows)
                    for i, row in enumerate(rows):
                        if progress_win.stop_event.is_set(): raise InterruptedError
                        progress = (i + 1) / total_rows
                        norm_row = data_helpers.normalize_csv_row(row)
                        org_nome, cidade_nome = norm_row.get('ORGAO_NOME'), norm_row.get('CIDADE')
                        progress_win.after(0, lambda p=progress, o=org_nome or cidade_nome, i=i, t=total_rows: progress_win.update_progress(f"Processando: {o}", p, f"Registro {i+1}/{t}"))
                        
                        if not cidade_nome: continue
                        cidade_key = data_helpers.normalize_city_key(cidade_nome)
                        cursor.execute("SELECT id FROM municipios WHERE cidade_key = ?", (cidade_key,))
                        municipio_result = cursor.fetchone()
                        id_municipio = municipio_result['id'] if municipio_result else cursor.execute("INSERT INTO municipios (cidade, cidade_key, uf) VALUES (?, ?, 'SP')", (cidade_nome, cidade_key)).lastrowid

                        if not org_nome: continue
                        
                        org_data = {
                            "nome_fantasia": org_nome,
                            "cnpj": norm_row.get('CNPJ') or None,
                            "endereco": norm_row.get('LOGRADOURO'),
                            "numero": norm_row.get('NUMERO'),
                            "complemento": norm_row.get('COMPLEMENTO'),
                            "cep": re.sub(r'\D', '', norm_row.get('CEP', '')), # Remove caracteres não numéricos do CEP
                            "bairro": norm_row.get('BAIRRO'),
                            "cidade": cidade_nome,
                            "uf": norm_row.get('UF') or 'SP', # Define 'SP' como padrão se a UF estiver vazia
                            "telefone": re.sub(r'\D', '', norm_row.get('TELEFONE', '')),
                            "email": norm_row.get('EMAIL'),
                            "website": norm_row.get('SITE'),
                            "id_municipio": id_municipio,
                            "tipo_organizacao": "Prefeitura" # Mantém o tipo fixo para esta importação
                        }

                        id_organizacao = None
                        if org_data["cnpj"]:
                            cursor.execute("SELECT id_organizacao FROM organizacoes WHERE cnpj = ?", (org_data["cnpj"],))
                            res = cursor.fetchone(); id_organizacao = res['id_organizacao'] if res else None
                        if not id_organizacao:
                            cursor.execute("SELECT id_organizacao FROM organizacoes WHERE nome_fantasia = ? AND tipo_organizacao = ?", (org_nome, "Prefeitura"))
                            res = cursor.fetchone(); id_organizacao = res['id_organizacao'] if res else None
                        
                        if id_organizacao:
                            update_clauses = ', '.join([f"{key} = ?" for key in org_data.keys()])
                            cursor.execute(f"UPDATE organizacoes SET {update_clauses} WHERE id_organizacao = ?", (*org_data.values(), id_organizacao))
                        else:
                            columns = ', '.join(org_data.keys()); placeholders = ', '.join(['?'] * len(org_data)); cursor.execute(f"INSERT INTO organizacoes ({columns}) VALUES ({placeholders})", tuple(org_data.values()))
                
                if progress_win.stop_event.is_set():
                    progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada."))
                else:
                    progress_win.after(0, lambda: progress_win.operation_finished(f"Importação concluída! {len(rows)} registros processados."))
            except InterruptedError:
                progress_win.after(0, lambda: progress_win.operation_finished("", "Importação cancelada."))
            except Exception as e:
                logging.error(f"Erro ao importar órgãos públicos: {e}", exc_info=True)
                progress_win.after(0, lambda e=e: progress_win.operation_finished("", f"Erro: {e}"))