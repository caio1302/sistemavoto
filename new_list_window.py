import customtkinter as ctk
from tkinter import messagebox
from functions import ui_helpers

class NewListWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict):
        super().__init__(parent)
        # MODIFICADO: Recebe 'repos'
        self.repos = repos
        self.parent_view = parent

        self.title("Criar Nova Lista")
        self.geometry("400x200")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()
        self.after(50, lambda: ui_helpers.center_window(self))
        self.entry_nome.focus_set()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(main_frame, text="Nome da Lista:").grid(row=0, column=0, sticky="w", padx=(0,10))
        self.entry_nome = ctk.CTkEntry(main_frame, placeholder_text="Ex: Apoiadores 2024")
        self.entry_nome.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(main_frame, text="Tipo da Lista:").grid(row=1, column=0, sticky="w", padx=(0,10), pady=(15,0))
        self.option_menu_tipo = ctk.CTkOptionMenu(main_frame, values=["Pessoas", "Organizacoes"])
        self.option_menu_tipo.grid(row=1, column=1, sticky="w", pady=(15,0))

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="se", padx=20, pady=10)
        ctk.CTkButton(button_frame, text="Salvar Lista", command=self._save).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")

    def _save(self):
        nome = self.entry_nome.get().strip()
        tipo = self.option_menu_tipo.get()

        if not nome:
            messagebox.showerror("Erro de Validação", "O nome da lista não pode ser vazio.", parent=self)
            return

        misc_repo = self.repos.get("misc")
        if not misc_repo:
            messagebox.showerror("Erro Crítico", "Repositório 'misc' não encontrado.", parent=self)
            return

        success = misc_repo.save_lista(nome, tipo)
        if success:
            messagebox.showinfo("Sucesso", "Nova lista criada com sucesso!", parent=self)
            self.parent_view.refresh_lists_panel()
            self.destroy()
        # A mensagem de erro de nome duplicado já é tratada pelo repositório