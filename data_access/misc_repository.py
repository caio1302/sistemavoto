import sqlite3
import logging
import json
import os
from tkinter import messagebox
from tag_definitions import TAG_DEFINITIONS
import config

class MiscRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.ui_tags = {}
        self._load_ui_tags()

    def _load_ui_tags(self):
        self.ui_tags = {tag_id: default_text for section in TAG_DEFINITIONS.values() for tag_id, default_text in section.items()}
        if os.path.exists(config.TAGS_PATH):
            try:
                with open(config.TAGS_PATH, 'r', encoding='utf-8') as f:
                    custom_tags = json.load(f)
                    self.ui_tags.update(custom_tags)
            except Exception as e:
                logging.warning(f"Não foi possível carregar o arquivo de tags da UI: {e}", exc_info=True)

    def get_ui_tags(self) -> dict:
        return self.ui_tags

    def save_ui_tags_to_file(self, tags_to_save: dict) -> bool:
        try:
            with open(config.TAGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(tags_to_save, f, indent=4, ensure_ascii=False)
            self._load_ui_tags()
            return True
        except IOError as e:
            messagebox.showerror("Erro de Arquivo", f"Não foi possível salvar as tags: {e}")
            return False

    def delete_ui_tags_file(self) -> bool:
        try:
            if os.path.exists(config.TAGS_PATH):
                os.remove(config.TAGS_PATH)
            self._load_ui_tags()
            return True
        except OSError as e:
            messagebox.showerror("Erro de Arquivo", f"Não foi possível apagar o arquivo de tags: {e}")
            return False

    def get_app_setting(self, key: str) -> str | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result['value'] if result else None
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar configuração '{key}': {e}")
            return None

    def save_app_setting(self, key: str, value: str) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao salvar configuração '{key}': {e}")
            return False

    def get_all_lists(self) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id_lista, nome, tipo FROM listas ORDER BY tipo, nome ASC")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error: return []
            
    def get_lookup_table_data(self, table_name: str) -> list[dict]:
        """
        Busca dados de tabelas de lookup simples como uma lista de dicionários [{'id': 1, 'nome': 'Valor'}].
        """
        valid_tables = ["tratamentos", "profissoes", "escolaridades", "temas", "tags"]
        if table_name not in valid_tables: 
            return []
        
        try:
            cursor = self.conn.cursor()
            id_col_name = "id_tag" if table_name == "tags" else ("id_tema" if table_name == "temas" else "id")
            
            cursor.execute(f"SELECT {id_col_name} as id, nome FROM {table_name} ORDER BY nome ASC")
            
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar dados de lookup da tabela {table_name}: {e}", exc_info=True)
            return []

    def get_municipio_cod_tse(self, cidade: str) -> str | None:
        from functions import data_helpers
        if not cidade: return None
        try:
            cidade_key = data_helpers.normalize_city_key(cidade)
            cursor = self.conn.cursor()
            query = "SELECT sg_ue FROM municipios WHERE cidade_key = ?"
            cursor.execute(query, (cidade_key,))
            result = cursor.fetchone()
            return str(result['sg_ue']) if result and result['sg_ue'] else None
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar sg_ue para a cidade '{cidade}': {e}", exc_info=True)
            return None
    
    # Todos os outros métodos podem ser omitidos se não forem alterados, ou colados aqui...
    # Para garantir a completude, o restante das funções que você tinha serão adicionadas abaixo.
    def save_lista(self, nome: str, tipo: str) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO listas (nome, tipo) VALUES (?, ?)", (nome, tipo))
            return True
        except sqlite3.IntegrityError:
            messagebox.showwarning("Nome Duplicado", f"Uma lista com o nome '{nome}' já existe.", parent=None)
            return False
        except sqlite3.Error: return False

    def delete_lista(self, list_id: int) -> bool:
        if list_id in [1, 2]:
            messagebox.showerror("Ação Proibida", "Não é possível apagar as listas padrão.", parent=None)
            return False
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM listas WHERE id_lista = ?", (list_id,))
                return cursor.rowcount > 0
        except sqlite3.Error: return False

    def get_all_temas(self) -> list[dict]:
        return self.get_lookup_table_data("temas")

    def get_anos_de_eleicao(self) -> list[str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT ano_eleicao FROM candidaturas WHERE ano_eleicao IS NOT NULL ORDER BY ano_eleicao DESC")
            return [str(row['ano_eleicao']) for row in cursor.fetchall()]
        except sqlite3.Error: return []

    def get_cidades_por_ano(self, ano: int) -> list[str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM candidaturas WHERE ano_eleicao = ? AND cargo IN ('PREFEITO', 'VEREADOR')", (ano,))
            is_municipal = cursor.fetchone()[0] > 0
            if is_municipal:
                cursor.execute("SELECT DISTINCT cidade FROM candidaturas WHERE ano_eleicao = ? AND cidade IS NOT NULL AND cidade NOT IN ('BRASIL', 'SP') ORDER BY cidade ASC", (ano,))
            else:
                cursor.execute("SELECT DISTINCT cidade FROM votos_por_municipio WHERE ano_eleicao = ? AND cidade IS NOT NULL ORDER BY cidade ASC", (ano,))
            return [row['cidade'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Não foi possível carregar a lista de cidades para o ano {ano}: {e}", exc_info=True)
            return []

    def get_city_list_from_db(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT cidade FROM municipios WHERE cidade IS NOT NULL AND cidade != '' ORDER BY cidade ASC")
            return [row['cidade'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Não foi possível carregar a lista de cidades: {e}", exc_info=True)
            return []