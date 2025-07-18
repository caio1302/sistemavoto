import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
import shutil
import os
import logging

import config
from functions import ui_helpers
from modules.person_search_window import PersonSearchWindow

class AppParamsWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent)
        # MODIFICADO: Recebe 'repos' e 'app'
        self.repos = repos
        self.app = app
        
        self.selected_owner_id = None
        self.new_logo_path = None

        self.title("Parâmetros Gerais do Sistema")
        self.geometry("600x450")
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.grid_columnconfigure(0, weight=1)

        self._create_widgets()
        self._load_current_settings()
        self.after(50, lambda: ui_helpers.center_window(self))

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)

        owner_frame = ctk.CTkFrame(main_frame)
        owner_frame.pack(fill="x", pady=10, ipady=10)
        owner_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(owner_frame, text="Candidato Proprietário:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.owner_entry = ctk.CTkEntry(owner_frame, state="readonly", placeholder_text="Nenhum definido")
        self.owner_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(owner_frame, text="Buscar e Definir...", command=self._search_owner).grid(row=0, column=2, padx=10, pady=10)

        map_frame = ctk.CTkFrame(main_frame)
        map_frame.pack(fill="x", pady=10, ipady=10)
        map_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(map_frame, text="Tema do Mapa:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        
        map_themes = ["Padrão (Colorido)", "Satélite", "Monocromático Claro", "Monocromático Escuro"]
        self.map_theme_var = ctk.StringVar(value="Padrão (Colorido)")
        self.map_theme_menu = ctk.CTkOptionMenu(map_frame, variable=self.map_theme_var, values=map_themes)
        self.map_theme_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        logo_frame = ctk.CTkFrame(main_frame)
        logo_frame.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(logo_frame, text="Logo do Sistema:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        self.logo_path_label = ctk.CTkLabel(logo_frame, text="Nenhum logo customizado.", text_color="gray", wraplength=500)
        self.logo_path_label.pack(anchor="w", padx=10)
        ctk.CTkButton(logo_frame, text="Alterar Logo...", command=self._select_logo).pack(anchor="w", padx=10, pady=10)
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="e", padx=20, pady=20)
        ctk.CTkButton(button_frame, text="Salvar Parâmetros", command=self._save_settings).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")

    def _load_current_settings(self):
        misc_repo = self.repos.get("misc")
        person_repo = self.repos.get("person")
        if not misc_repo or not person_repo: return

        owner_id = misc_repo.get_app_setting('proprietario_id_pessoa')
        if owner_id:
            self.selected_owner_id = int(owner_id)
            owner_details = person_repo.get_person_details(self.selected_owner_id)
            if owner_details:
                self.owner_entry.configure(state="normal")
                self.owner_entry.delete(0, "end")
                self.owner_entry.insert(0, owner_details.nome)
                self.owner_entry.configure(state="readonly")
        
        map_theme = misc_repo.get_app_setting('map_theme')
        if map_theme in self.map_theme_menu.cget("values"):
            self.map_theme_var.set(map_theme)
        
        if os.path.exists(config.CUSTOM_LOGO_PATH):
            self.logo_path_label.configure(text=config.CUSTOM_LOGO_PATH)

    def _search_owner(self):
        # MODIFICADO: Passa 'repos'
        search_win = PersonSearchWindow(self, self.repos)
        person = search_win.get_selection()
        if person:
            self.selected_owner_id = person.id_pessoa
            self.owner_entry.configure(state="normal")
            self.owner_entry.delete(0, "end")
            self.owner_entry.insert(0, person.nome)
            self.owner_entry.configure(state="readonly")

    def _select_logo(self):
        filepath = filedialog.askopenfilename(
            title="Selecione a nova imagem para o logo (.png)",
            filetypes=[("Imagens PNG", "*.png")], parent=self)
        if filepath:
            self.new_logo_path = filepath
            self.logo_path_label.configure(text=f"Novo: {filepath}")

    def _save_settings(self):
        try:
            misc_repo = self.repos.get("misc")
            if not misc_repo: return

            if self.selected_owner_id:
                misc_repo.save_app_setting('proprietario_id_pessoa', str(self.selected_owner_id))

            misc_repo.save_app_setting('map_theme', self.map_theme_var.get())

            if self.new_logo_path:
                dest_path = config.CUSTOM_LOGO_PATH
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(self.new_logo_path, dest_path)
            
            messagebox.showinfo("Sucesso", "Parâmetros salvos com sucesso!", parent=self)
            
            # Notifica a aplicação principal que dados que afetam a UI foram alterados
            if hasattr(self.app, 'on_data_updated'):
                self.app.on_data_updated() # Você pode criar um evento para isso também

            self.destroy()

        except Exception as e:
            logging.error(f"Erro ao salvar parâmetros: {e}", exc_info=True)
            messagebox.showerror("Erro", f"Não foi possível salvar os parâmetros: {e}", parent=self)