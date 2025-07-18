# popups/login_window.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import secrets
from datetime import datetime, timedelta
import logging
import os
import sys
import customtkinter

import config
from functions import ui_helpers
from data_access.user_repository import UserRepository

def get_saved_token_path():
    return config.LAST_SESSION_PATH

def save_token_to_file(token):
    try:
        with open(get_saved_token_path(), 'w') as f:
            f.write(token)
    except Exception as e:
        logging.error(f"Não foi possível salvar o token no arquivo: {e}")

def read_token_from_file():
    try:
        token_path = get_saved_token_path()
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logging.error(f"Não foi possível ler o token do arquivo: {e}")
    return None

def delete_token_file():
    token_path = get_saved_token_path()
    if os.path.exists(token_path):
        try:
            os.remove(token_path)
            logging.info("Arquivo de token de sessão local excluído.")
        except OSError as e:
            logging.warning(f"Não foi possível remover o arquivo de token local: {e}")

class LoginWindow(customtkinter.CTk):
    def __init__(self, user_repo: UserRepository):
        super().__init__()
        self.user_repo = user_repo
        self.successful_user = None # --- NOVO ---        
        self.title("e-Votos - Autenticação")
        self.geometry("400x580") 
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._create_widgets()
        self._set_tab_order() # MUDANÇA: Chama o novo método para configurar o Tab
        ui_helpers.center_window(self)
        self.focus_force()

    def _create_widgets(self):
        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        try:
            logo_path = config.CUSTOM_LOGO_PATH if os.path.exists(config.CUSTOM_LOGO_PATH) else config.LOGO_PATH
            pil_image = Image.open(logo_path)
            ctk_logo_image = customtkinter.CTkImage(light_image=pil_image, dark_image=pil_image, size=(200, 40))
            logo_label = customtkinter.CTkLabel(main_frame, image=ctk_logo_image, text="")
            logo_label.pack(pady=(20, 40))
        except Exception:
            logo_label = customtkinter.CTkLabel(main_frame, text="e-Votos", font=customtkinter.CTkFont(size=32, weight="bold"))
            logo_label.pack(pady=(20, 40))

        customtkinter.CTkLabel(main_frame, text="Usuário").pack(anchor="w")
        self.user_entry = customtkinter.CTkEntry(main_frame, width=300, height=40)
        self.user_entry.pack(fill=tk.X, pady=(5, 20))
        self.user_entry.bind("<Return>", lambda e: self.pass_entry.focus_set())
        self.user_entry.focus_set()

        customtkinter.CTkLabel(main_frame, text="Senha").pack(anchor="w")
        self.pass_entry = customtkinter.CTkEntry(main_frame, show="*", width=300, height=40)
        self.pass_entry.pack(fill=tk.X, pady=(5, 15))
        self.pass_entry.bind("<Return>", self._perform_login)

        self.remember_me_var = tk.BooleanVar()
        # MUDANÇA: Nomeia os widgets para podermos controlá-los
        self.remember_me_checkbox = customtkinter.CTkCheckBox(main_frame, text="Lembrar-me", variable=self.remember_me_var)
        self.remember_me_checkbox.pack(anchor="w", pady=(5, 25))
        
        self.login_button = customtkinter.CTkButton(main_frame, text="Acessar", command=self._perform_login, height=45)
        self.login_button.pack(fill=tk.X, ipady=5)
    
    # MUDANÇA: Novo método para controlar o fluxo da tecla Tab
    def _set_tab_order(self):
        """Configura manualmente a ordem de foco para a tecla Tab."""
        # A ordem é: usuário -> senha -> checkbox -> botão -> (volta para usuário)
        
        self.user_entry.bind("<Tab>", lambda e: self.pass_entry.focus_set() or "break")
        self.pass_entry.bind("<Tab>", lambda e: self.remember_me_checkbox.focus_set() or "break")
        self.remember_me_checkbox.bind("<Tab>", lambda e: self.login_button.focus_set() or "break")
        self.login_button.bind("<Tab>", lambda e: self.user_entry.focus_set() or "break")
        
        # Agora, a ordem reversa (Shift + Tab)
        # O evento para Shift-Tab pode variar um pouco entre sistemas, 
        # '<Shift-Tab>' ou '<Shift-KeyPress-Tab>' são comuns.
        self.login_button.bind("<Shift-KeyPress-Tab>", lambda e: self.remember_me_checkbox.focus_set() or "break")
        self.remember_me_checkbox.bind("<Shift-KeyPress-Tab>", lambda e: self.pass_entry.focus_set() or "break")
        self.pass_entry.bind("<Shift-KeyPress-Tab>", lambda e: self.user_entry.focus_set() or "break")
        self.user_entry.bind("<Shift-KeyPress-Tab>", lambda e: self.login_button.focus_set() or "break")


    def _perform_login(self, event=None):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showerror("Erro", "Usuário e senha são obrigatórios.", parent=self)
            return
        
        verified_user = self.user_repo.verify_user(username, password)
        if verified_user:
            self.successful_user = verified_user # --- NOVO ---            
            self._generate_and_save_token(verified_user, remember=self.remember_me_var.get())
            self.withdraw()
            self.after(100, self._restart_app)
        else:
            logging.warning(f"Tentativa de login falhou para o usuário: {username}")
            messagebox.showerror("Erro", "Usuário ou senha inválidos.", parent=self)

    def _restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _generate_and_save_token(self, user, remember: bool):
        token = secrets.token_hex(32)
        validity_duration = timedelta(hours=24) if remember else timedelta(minutes=2)
        valid_until = datetime.now() + validity_duration
        valid_until_str = valid_until.strftime("%Y-%m-%d %H:%M:%S")
        
        self.user_repo.save_session_token(user.id_usuario, token, valid_until_str)
        save_token_to_file(token)