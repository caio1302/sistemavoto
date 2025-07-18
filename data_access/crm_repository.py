import sqlite3
import logging

class CrmRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # --- Métodos de Atendimento ---

    def get_atendimentos_for_pessoa(self, id_pessoa: int) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT id_atendimento, titulo, data_abertura, status FROM atendimentos WHERE id_pessoa = ? ORDER BY data_abertura DESC"
            cursor.execute(query, (id_pessoa,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar atendimentos para a pessoa ID {id_pessoa}: {e}")
            return []

    def get_urgent_atendimentos(self, limit: int = 5) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT a.*, COALESCE(p.nome, org.nome_fantasia) as nome_solicitante 
                FROM atendimentos a 
                LEFT JOIN pessoas p ON a.id_pessoa = p.id_pessoa 
                LEFT JOIN organizacoes org ON a.id_organizacao = org.id_organizacao 
                WHERE a.status IN ('Aberto', 'Em Andamento') AND a.prioridade IN ('Alta', 'Urgente')
                ORDER BY 
                    CASE a.prioridade 
                        WHEN 'Urgente' THEN 1 
                        WHEN 'Alta' THEN 2 
                        ELSE 3 
                    END,
                    a.data_abertura ASC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar atendimentos urgentes: {e}")
            return []

    def get_all_atendimentos(self) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT a.*, COALESCE(p.nome, org.nome_fantasia) as nome_solicitante 
                FROM atendimentos a 
                LEFT JOIN pessoas p ON a.id_pessoa = p.id_pessoa 
                LEFT JOIN organizacoes org ON a.id_organizacao = org.id_organizacao 
                ORDER BY a.data_abertura DESC
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_atendimento_by_id(self, atendimento_id: int) -> dict | None:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT a.*, COALESCE(p.nome, org.nome_fantasia) as nome_solicitante 
                FROM atendimentos a 
                LEFT JOIN pessoas p ON a.id_pessoa = p.id_pessoa 
                LEFT JOIN organizacoes org ON a.id_organizacao = org.id_organizacao 
                WHERE a.id_atendimento = ?
            """
            cursor.execute(query, (atendimento_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None

    def save_atendimento(self, atendimento_data: dict, atendimento_id: int = 0) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                if atendimento_id == 0:
                    columns = ', '.join(atendimento_data.keys())
                    placeholders = ', '.join(['?'] * len(atendimento_data))
                    sql = f"INSERT INTO atendimentos ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(atendimento_data.values()))
                else:
                    set_clauses = ', '.join([f"{key} = ?" for key in atendimento_data.keys()])
                    sql = f"UPDATE atendimentos SET {set_clauses} WHERE id_atendimento = ?"
                    values = tuple(atendimento_data.values()) + (atendimento_id,)
                    cursor.execute(sql, values)
            return True
        except sqlite3.Error:
            return False

    def get_updates_for_atendimento(self, atendimento_id: int) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM atendimento_updates WHERE id_atendimento = ? ORDER BY data_update DESC"
            cursor.execute(query, (atendimento_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def save_atendimento_update(self, update_data: dict) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                columns = ', '.join(update_data.keys())
                placeholders = ', '.join(['?'] * len(update_data))
                sql = f"INSERT INTO atendimento_updates ({columns}) VALUES ({placeholders})"
                values = tuple(update_data.values())
                cursor.execute(sql, values)
            return True
        except sqlite3.Error:
            return False

    # --- Métodos de Proposição ---

    def get_all_proposicoes(self) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM proposicoes ORDER BY data_proposicao DESC"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_proposicao_by_id(self, proposicao_id: int) -> dict | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM proposicoes WHERE id_proposicao = ?", (proposicao_id,))
            proposicao_data = cursor.fetchone()
            if not proposicao_data: return None
            
            proposicao_dict = dict(proposicao_data)
            cursor.execute("SELECT id_tema FROM proposicao_temas_assoc WHERE id_proposicao = ?", (proposicao_id,))
            proposicao_dict['temas_ids'] = [row['id_tema'] for row in cursor.fetchall()]
            return proposicao_dict
        except sqlite3.Error:
            return None

    def save_proposicao(self, proposicao_data: dict, temas_ids: list[int], proposicao_id: int = 0) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                effective_id = proposicao_id
                if effective_id == 0:
                    sql = "INSERT INTO proposicoes (titulo, tipo, autor, data_proposicao, status, descricao) VALUES (?, ?, ?, ?, ?, ?)"
                    values = (proposicao_data.get('titulo'), proposicao_data.get('tipo'), proposicao_data.get('autor'), proposicao_data.get('data_proposicao'), proposicao_data.get('status'), proposicao_data.get('descricao'))
                    cursor.execute(sql, values)
                    effective_id = cursor.lastrowid
                else:
                    sql = "UPDATE proposicoes SET titulo = ?, tipo = ?, autor = ?, data_proposicao = ?, status = ?, descricao = ? WHERE id_proposicao = ?"
                    values = (proposicao_data.get('titulo'), proposicao_data.get('tipo'), proposicao_data.get('autor'), proposicao_data.get('data_proposicao'), proposicao_data.get('status'), proposicao_data.get('descricao'), proposicao_id)
                    cursor.execute(sql, values)
                
                if not effective_id: raise sqlite3.Error("Não foi possível obter o ID da proposição.")
                
                cursor.execute("DELETE FROM proposicao_temas_assoc WHERE id_proposicao = ?", (effective_id,))
                if temas_ids:
                    assoc_data = [(effective_id, tema_id) for tema_id in temas_ids]
                    cursor.executemany("INSERT INTO proposicao_temas_assoc (id_proposicao, id_tema) VALUES (?, ?)", assoc_data)
            return True
        except sqlite3.Error:
            return False

    def delete_proposicao(self, proposicao_id: int) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM proposicoes WHERE id_proposicao = ?", (proposicao_id,))
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    # --- Métodos de Evento ---

    def get_eventos_for_month(self, year: int, month: int) -> list[dict]:
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM eventos WHERE data_evento BETWEEN ? AND ?"
            cursor.execute(query, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_upcoming_events(self, days=7) -> list[dict]:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM eventos WHERE data_evento BETWEEN ? AND ? ORDER BY data_evento ASC"
            cursor.execute(query, (today, end_date))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_events_for_day(self, target_date) -> list[dict]:
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            cursor = self.conn.cursor()
            query = "SELECT * FROM eventos WHERE data_evento = ? ORDER BY hora_inicio ASC"
            cursor.execute(query, (date_str,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar eventos para o dia {target_date}: {e}")
            return []

    def get_evento_by_id(self, evento_id: int) -> dict | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM eventos WHERE id_evento = ?", (evento_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar evento ID {evento_id}: {e}", exc_info=True)
            return None

    def save_evento(self, evento_data: dict, evento_id: int = 0) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                if evento_id == 0:
                    cols = ', '.join(evento_data.keys())
                    placeholders = ', '.join(['?'] * len(evento_data))
                    sql = f"INSERT INTO eventos ({cols}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(evento_data.values()))
                else:
                    set_clauses = ', '.join([f"{key} = ?" for key in evento_data.keys()])
                    sql = f"UPDATE eventos SET {set_clauses} WHERE id_evento = ?"
                    values = tuple(evento_data.values()) + (evento_id,)
                    cursor.execute(sql, values)
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao salvar evento: {e}", exc_info=True)
            return False

    def delete_evento(self, evento_id: int) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM eventos WHERE id_evento = ?", (evento_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logging.error(f"Erro ao deletar evento ID {evento_id}: {e}", exc_info=True)
            return False