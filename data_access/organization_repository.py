import sqlite3
import logging
from tkinter import messagebox
# MUDANÇA: Importa 'fields' para introspecção do dataclass
from dataclasses import fields
from dto.organizacao import Organizacao

class OrganizationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all_organizacoes(self, search_term: str = "", limit: int = 50, offset: int = 0) -> list[Organizacao]:
        try:
            cursor = self.conn.cursor()
            params = []
            query = "SELECT id_organizacao, nome_fantasia, cnpj, telefone, cidade FROM organizacoes"
            if search_term:
                query += " WHERE nome_fantasia LIKE ? OR razao_social LIKE ?"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            query += " ORDER BY nome_fantasia ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, tuple(params))
            return [Organizacao.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar lista de organizações: {e}", exc_info=True)
            return []

    def count_organizacoes(self, search_term: str = "") -> int:
        try:
            cursor = self.conn.cursor()
            params = []
            query = "SELECT COUNT(id_organizacao) FROM organizacoes"
            if search_term:
                query += " WHERE nome_fantasia LIKE ? OR razao_social LIKE ?"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Erro ao contar organizações: {e}", exc_info=True)
            return 0

    def get_organization_details(self, org_id: int) -> Organizacao | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM organizacoes WHERE id_organizacao = ?", (org_id,))
            row = cursor.fetchone()
            return Organizacao.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar detalhes da organização ID {org_id}: {e}", exc_info=True)
            return None

    def save_organizacao(self, org: Organizacao) -> Organizacao | None:
        # --- CORREÇÃO AQUI ---
        # Usa dataclasses.fields para obter os nomes dos campos corretamente
        campos_tabela = {f.name for f in fields(Organizacao)} - {'id_organizacao', 'tags', 'listas'}
        
        data = {key: getattr(org, key) for key in campos_tabela if hasattr(org, key)}
        
        if 'cnpj' in data and data['cnpj'] == '': 
            data['cnpj'] = None
        
        try:
            with self.conn:
                cursor = self.conn.cursor()
                if org.id_organizacao == 0:
                    valid_data = {k: v for k, v in data.items() if v is not None and v != ''}
                    columns = ', '.join(valid_data.keys())
                    placeholders = ', '.join(['?'] * len(valid_data))
                    set_clauses = ', '.join([f"{key} = ?" for key in data.keys()])
                    sql = f"INSERT INTO organizacoes ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(valid_data.values()))
                    org.id_organizacao = cursor.lastrowid
                else:
                    # O ID já está no objeto 'org', então não precisa ser removido de 'data'
                    # se o loop de campos já o excluiu
                    set_clauses = ', '.join([f"{key} = ?" for key in data.keys()])
                    sql = f"UPDATE organizacoes SET {set_clauses} WHERE id_organizacao = ?"
                    values = tuple(data.values()) + (org.id_organizacao,)
                    cursor.execute(sql, values)
            return org
        except sqlite3.Error as e:
            logging.error(f"Erro em save_organizacao: {e}", exc_info=True)
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível salvar a organização.\n\nDetalhe: {e}")
            return None

    def delete_organizacao(self, id_organizacao: int) -> bool:
        if not id_organizacao: return False
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM organizacoes WHERE id_organizacao = ?", (id_organizacao,))
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        
    def get_all_geocoded_organizacoes(self) -> list[Organizacao]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM organizacoes WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND geo_visivel = 1"
            cursor.execute(query)
            return [Organizacao.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar organizações geocodificadas: {e}", exc_info=True)
            return []