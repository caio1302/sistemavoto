import sqlite3
import logging
from tkinter import messagebox
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura
from functions import data_helpers
import os
from pathlib import Path
import config

class PersonRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _build_from_where_clauses(self, **filters) -> tuple[str, list]:
        from_clause = """
            FROM pessoas p
            LEFT JOIN (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY id_pessoa ORDER BY ano_eleicao DESC) as rn
                FROM candidaturas
            ) c ON p.id_pessoa = c.id_pessoa AND c.rn = 1
        """
        
        where_clauses = []
        params = []
        
        search_term = filters.get('search_term')
        if search_term:
            where_clauses.append("(p.nome LIKE ? OR p.apelido LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        cidade = filters.get('cidade')
        if cidade and cidade.upper() != "TODAS":
            where_clauses.append("c.cidade = ?")
            params.append(data_helpers.normalize_city_key(cidade))

        if filters.get('only_candidates'):
            where_clauses.append("c.sq_candidato IS NOT NULL")
            
        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
            
        return from_clause + where_sql, params

    def get_paginated_pessoas(self, page: int = 1, items_per_page: int = 50, sort_by: str = "ID", sort_desc: bool = True, **filters) -> list[Pessoa]:
        try:
            from_where_sql, params = self._build_from_where_clauses(**filters)
            selection = "p.*, c.id_candidatura, c.ano_eleicao, c.sq_candidato, c.nome_urna, c.numero_urna, c.partido, c.cargo, c.votos, c.situacao, c.cidade as cidade_candidatura_recente, CASE WHEN c.sq_candidato IS NOT NULL THEN 1 ELSE 0 END as is_candidate"
            query = f"SELECT {selection} {from_where_sql}"

            sort_map = {"ID": "p.id_pessoa", "Nome": "p.nome", "Apelido": "p.apelido", "Celular": "p.celular", "Cidade": "cidade_candidatura_recente"}
            sort_column_sql = sort_map.get(sort_by, "p.id_pessoa")
            sort_direction = "DESC" if sort_desc else "ASC"
            
            query += f" ORDER BY {sort_column_sql} {sort_direction} LIMIT ? OFFSET ?"
            offset = (page - 1) * items_per_page
            params.extend([items_per_page, offset])

            cursor = self.conn.cursor()
            cursor.execute(query, tuple(params))
            return [Pessoa.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar lista paginada de pessoas: {e}", exc_info=True)
            return []

    def count_pessoas(self, **filters) -> int:
        try:
            from_where_sql, params = self._build_from_where_clauses(**filters)
            query = f"SELECT COUNT(p.id_pessoa) {from_where_sql}"

            cursor = self.conn.cursor()
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Erro ao contar pessoas: {e}", exc_info=True)
            return 0
    
    def get_person_details(self, person_id: int) -> Pessoa | None:
        try:
            selection = "p.*, c.id_candidatura, c.ano_eleicao, c.sq_candidato, c.nome_urna, c.numero_urna, c.partido, c.cargo, c.votos, c.situacao, o.nome_fantasia as nome_organizacao_trabalho, t.nome as nome_tratamento"
            base_query = """
                FROM pessoas p
                LEFT JOIN (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY id_pessoa ORDER BY ano_eleicao DESC) as rn
                    FROM candidaturas
                ) c ON p.id_pessoa = c.id_pessoa AND c.rn = 1
                LEFT JOIN organizacoes o ON p.id_organizacao_trabalho = o.id_organizacao
                LEFT JOIN tratamentos t ON p.id_tratamento = t.id
                WHERE p.id_pessoa = ?
            """
            query = f"SELECT {selection} {base_query}"
            cursor = self.conn.cursor()
            cursor.execute(query, (person_id,))
            person_row = cursor.fetchone()
            if not person_row: return None
            
            pessoa_obj = Pessoa.from_dict(dict(person_row))
            
            pessoa_obj.historico_candidaturas = self.get_candidaturas_for_pessoa(person_id)
            pessoa_obj.relacionamentos = self.get_relacionamentos_for_pessoa(person_id)
            
            return pessoa_obj
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar detalhes da pessoa ID {person_id}: {e}", exc_info=True)
            return None

    def search_candidaturas(self, search_term: str, criteria: str, ano_ref: int | str) -> list[Candidatura]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT p.*, c.* FROM pessoas p JOIN candidaturas c ON p.id_pessoa = c.id_pessoa"
            params, where_clauses = [], []
            if criteria == 'Nome':
                where_clauses.append("(p.nome LIKE ? OR p.apelido LIKE ?)")
                params.extend([f'%{search_term}%', f'%{search_term}%'])
            elif criteria == 'Partido':
                where_clauses.append("c.partido LIKE ?")
                params.append(f'%{search_term}%')
            elif criteria == 'Cidade':
                cidade_key = data_helpers.normalize_city_key(search_term)
                where_clauses.append("c.cidade LIKE ?")
                params.append(f'%{cidade_key}%')
            if ano_ref and str(ano_ref).lower() != "todos":
                where_clauses.append("c.ano_eleicao = ?")
                params.append(ano_ref)
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            query += " ORDER BY c.ano_eleicao DESC, p.nome ASC"
            cursor.execute(query, tuple(params))
            return [Candidatura.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar candidaturas: {e}", exc_info=True)
            return []
    def get_candidaturas_por_cidade_exata(self, cidade: str, ano: int, cargo: str, situacoes: list[str], limit: int | None = None) -> list[Candidatura]:
        """
        Busca candidaturas com base em uma correspondência exata de cidade, ano, cargo e situação.
        Esta função é otimizada para o módulo Cerimonial.
        """
        try:
            cursor = self.conn.cursor()
            cidade_key = data_helpers.normalize_city_key(cidade)
            
            situacao_placeholders = ','.join(['?'] * len(situacoes))
            query = f"""
                SELECT p.*, c.* 
                FROM pessoas p
                JOIN candidaturas c ON p.id_pessoa = c.id_pessoa
                WHERE c.cidade = ? 
                  AND c.ano_eleicao = ? 
                  AND c.cargo = ? 
                  AND c.situacao IN ({situacao_placeholders})
                ORDER BY c.votos DESC
            """
            
            params = [cidade_key, ano, cargo] + situacoes
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, tuple(params))
            return [Candidatura.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar candidaturas por cidade exata ({cidade}/{ano}/{cargo}): {e}", exc_info=True)
            return []        

    def get_candidaturas_for_pessoa(self, id_pessoa: int) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM candidaturas WHERE id_pessoa = ? ORDER BY ano_eleicao DESC"
            cursor.execute(query, (id_pessoa,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def save_pessoa(self, pessoa: Pessoa) -> Pessoa | None:
        campos_tabela_pessoa = {
            'nome', 'apelido', 'cpf', 'data_nascimento', 'genero', 'email', 'celular',
            'telefone_residencial', 'caminho_foto', 'notas_pessoais', 'voto',
            'id_tratamento', 'id_profissao', 'id_escolaridade', 'id_organizacao_trabalho',
            'rg', 'titulo_eleitor',
            'endereco', 'numero', 'complemento', 'bairro', 'cep', 'cidade', 'uf',
            'latitude', 'longitude', 'geo_visivel'
        }
        data = {field: getattr(pessoa, field) for field in campos_tabela_pessoa if hasattr(pessoa, field)}
        if 'cpf' in data and data['cpf'] == '': data['cpf'] = None
        
        try:
            with self.conn:
                cursor = self.conn.cursor()
                if pessoa.id_pessoa == 0:
                    valid_data = {k: v for k, v in data.items() if v is not None and v != ''}
                    columns = ', '.join(valid_data.keys())
                    placeholders = ', '.join(['?'] * len(valid_data))
                    sql = f"INSERT INTO pessoas ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(valid_data.values()))
                    pessoa.id_pessoa = cursor.lastrowid
                else:
                    data.pop('id_pessoa', None)
                    set_clauses = ', '.join([f"{key} = ?" for key in data.keys()])
                    sql = f"UPDATE pessoas SET {set_clauses} WHERE id_pessoa = ?"
                    values = tuple(data.values()) + (pessoa.id_pessoa,)
                    cursor.execute(sql, values)
            
            return pessoa
        except sqlite3.Error as e:
            logging.error(f"Erro em save_pessoa: {e}", exc_info=True)
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível salvar os dados da pessoa.\n\nDetalhe: {e}")
            return None
            
    def delete_pessoa(self, id_pessoa: int) -> bool:
        if not id_pessoa: return False
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM pessoas WHERE id_pessoa = ?", (id_pessoa,))
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def update_pessoa_photo_path(self, person_id: int, photo_path: str | None) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE pessoas SET caminho_foto = ? WHERE id_pessoa = ?", (photo_path, person_id))
            return True
        except sqlite3.Error:
            return False

    def get_relacionamentos_for_pessoa(self, person_id: int) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT r.id_relacionamento, r.tipo_relacao, r.id_pessoa_destino, p.nome as nome_pessoa_destino FROM relacionamentos r JOIN pessoas p ON r.id_pessoa_destino = p.id_pessoa WHERE r.id_pessoa_origem = ?"
            cursor.execute(query, (person_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e: 
            logging.error(f"Erro ao buscar relacionamentos para a pessoa ID {person_id}: {e}")
            return []

    def save_relacionamento(self, id_origem: int, id_destino: int, tipo_relacao: str) -> bool:
        mapa_reciproco = {
            "Pai": "Filho(a)", "Mãe": "Filho(a)", "Filho(a)": "Pai/Mãe", "Cônjuge": "Cônjuge",
            "Irmão/Irmã": "Irmão/Irmã", "Assessor(a)": "Assessorado(a)", "Assessorado(a)": "Assessor(a)", "Sócio(a)": "Sócio(a)"
        }
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO relacionamentos (id_pessoa_origem, id_pessoa_destino, tipo_relacao) VALUES (?, ?, ?)", (id_origem, id_destino, tipo_relacao))
                tipo_reciproco = mapa_reciproco.get(tipo_relacao)
                if tipo_reciproco and tipo_reciproco != "Pai/Mãe":
                    cursor.execute("INSERT OR IGNORE INTO relacionamentos (id_pessoa_origem, id_pessoa_destino, tipo_relacao) VALUES (?, ?, ?)", (id_destino, id_origem, tipo_reciproco))
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao salvar relacionamento recíproco: {e}", exc_info=True)
            return False

    def delete_relacionamento(self, id_relacionamento: int) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM relacionamentos WHERE id_relacionamento = ?", (id_relacionamento,))
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            return False

    def get_list_ids_for_pessoa(self, person_id: int) -> list[int]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id_lista FROM pessoa_listas_assoc WHERE id_pessoa = ?", (person_id,))
            return [row['id_lista'] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def update_list_associations_for_pessoa(self, person_id: int, list_ids: list[int]):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM pessoa_listas_assoc WHERE id_pessoa = ?", (person_id,))
                if list_ids:
                    associations_to_insert = [(person_id, list_id) for list_id in list_ids]
                    cursor.executemany("INSERT INTO pessoa_listas_assoc (id_pessoa, id_lista) VALUES (?, ?)", associations_to_insert)
            return True
        except sqlite3.Error:
            return False
            
    def get_all_geocoded_pessoas(self) -> list[Pessoa]:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT p.*, c.id_candidatura, c.ano_eleicao, c.sq_candidato, c.nome_urna, c.numero_urna, c.partido, c.cargo, c.votos, c.situacao
                FROM pessoas p
                LEFT JOIN (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY id_pessoa ORDER BY ano_eleicao DESC) as rn
                    FROM candidaturas
                ) c ON p.id_pessoa = c.id_pessoa AND c.rn = 1
                WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL AND p.geo_visivel = 1
            """
            cursor.execute(query)
            return [Pessoa.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar pessoas geocodificadas: {e}")
            return []
    
    # --- MÉTODO ALTERADO ---
    def clear_person_photo_path(self, person_id: int) -> bool:
        """Define o caminho_foto de uma pessoa como NULL e apaga o arquivo físico."""
        photo_path_to_delete = None
        try:
            with self.conn:
                cursor = self.conn.cursor()
                # 1. Busca o caminho do arquivo antes de apagar do DB
                cursor.execute("SELECT caminho_foto FROM pessoas WHERE id_pessoa = ?", (person_id,))
                result = cursor.fetchone()
                photo_path_to_delete = result['caminho_foto'] if result else None
                
                # 2. Limpa o caminho no banco de dados
                cursor.execute("UPDATE pessoas SET caminho_foto = NULL WHERE id_pessoa = ?", (person_id,))

            # 3. Se havia um caminho, tenta apagar o arquivo
            if photo_path_to_delete:
                try:
                    full_path = Path(config.BASE_PATH) / photo_path_to_delete
                    if full_path.is_file():
                        os.remove(full_path)
                        logging.info(f"Arquivo de foto removido do disco: {full_path}")
                except Exception as e:
                    logging.warning(f"Não foi possível remover o arquivo de foto {photo_path_to_delete}: {e}")

            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao limpar caminho da foto para a pessoa ID {person_id}: {e}", exc_info=True)
            return False