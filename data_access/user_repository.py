import sqlite3
import hashlib
from datetime import datetime, timedelta
import logging
from dto.user import User

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def verify_user(self, username: str, password_str: str) -> User | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = ?", (username,))
            user_row = cursor.fetchone()
            if user_row:
                user_data = dict(user_row)
                if user_data.get('hash_senha') == hashlib.sha256(password_str.encode('utf-8')).hexdigest():
                    return User.from_dict(user_data)
            return None
        except sqlite3.Error as e:
            logging.error(f"Erro em verify_user: {e}", exc_info=True)
            return None

    def verify_login_token(self, token: str) -> User | None:
        if not token: return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE login_token = ?", (token,))
            user_row = cursor.fetchone()
            if user_row:
                user_data = dict(user_row)
                validade_str = user_data.get('token_validade')
                if validade_str and datetime.now() < datetime.strptime(validade_str, "%Y-%m-%d %H:%M:%S"):
                    return User.from_dict(user_data)
                elif validade_str:
                    self._clear_token_for_user(User.from_dict(user_data))
            return None
        except Exception as e:
            logging.error(f"Erro em verify_login_token: {e}", exc_info=True)
            return None

    def _clear_token_for_user(self, user: User):
        try:
            with self.conn:
                self.conn.execute("UPDATE usuarios SET login_token = NULL, token_validade = NULL WHERE id_usuario = ?", (user.id_usuario,))
        except sqlite3.Error as e:
            logging.error(f"Erro ao limpar token para usuário {user.nome_usuario}: {e}", exc_info=True)

    def save_session_token(self, user_id: int, token: str, valid_until_str: str):
        try:
            with self.conn:
                self.conn.execute("UPDATE usuarios SET login_token = ?, token_validade = ? WHERE id_usuario = ?", (token, valid_until_str, user_id))
        except sqlite3.Error as e:
            logging.error(f"Erro ao salvar token de sessão no DB: {e}", exc_info=True)

    def get_all_users(self) -> list[User]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM usuarios ORDER BY nivel_acesso, nome_usuario")
            return [User.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro em get_all_users: {e}", exc_info=True)
            return []

    def get_user_by_id(self, user_id: int) -> User | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE id_usuario = ?", (user_id,))
            row = cursor.fetchone()
            return User.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            logging.error(f"Erro em get_user_by_id: {e}", exc_info=True)
            return None

    def save_user(self, user: User) -> User | None:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                if user.id_usuario == 0:
                    if not user.hash_senha: raise ValueError("Senha é obrigatória para novos usuários.")
                    sql = "INSERT INTO usuarios (nome_usuario, hash_senha, nome_completo, data_nascimento, telefone, email, caminho_foto, nivel_acesso) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                    params = (user.nome_usuario, user.hash_senha, user.nome_completo, user.data_nascimento, user.telefone, user.email, user.caminho_foto, user.nivel_acesso)
                    cursor.execute(sql, params)
                    user.id_usuario = cursor.lastrowid
                else:
                    if user.hash_senha:
                        sql = "UPDATE usuarios SET nome_usuario=?, hash_senha=?, nome_completo=?, data_nascimento=?, telefone=?, email=?, caminho_foto=?, nivel_acesso=? WHERE id_usuario = ?"
                        params = (user.nome_usuario, user.hash_senha, user.nome_completo, user.data_nascimento, user.telefone, user.email, user.caminho_foto, user.nivel_acesso, user.id_usuario)
                    else:
                        sql = "UPDATE usuarios SET nome_usuario=?, nome_completo=?, data_nascimento=?, telefone=?, email=?, caminho_foto=?, nivel_acesso=? WHERE id_usuario = ?"
                        params = (user.nome_usuario, user.nome_completo, user.data_nascimento, user.telefone, user.email, user.caminho_foto, user.nivel_acesso, user.id_usuario)
                    cursor.execute(sql, params)
            return user
        except Exception as e:
            logging.error(f"Erro em save_user: {e}", exc_info=True)
            return None

    def delete_user(self, user_id: int) -> bool:
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id_usuario = ?", (user_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logging.error(f"Erro em delete_user: {e}", exc_info=True)
            return False