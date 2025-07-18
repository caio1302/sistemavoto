import customtkinter as ctk
from tkinter import messagebox

class OrganizationSearchWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict):
        super().__init__(parent)
        # MODIFICADO: Recebe 'repos'
        self.repos = repos
        self.parent_form = parent
        self.selected_org = None

        self.title("Buscar Organização")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._create_widgets()
        self.search_entry.focus_set()

    def _create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Digite para buscar...")
        self.search_entry.grid(row=0, column=0, padx=(0,10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Organizações Encontradas")
        self.results_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def _on_search(self, event=None):
        search_term = self.search_entry.get().lower()
        
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        org_repo = self.repos.get("organization")
        if not org_repo: return

        # A busca agora pode usar o 'search_term' diretamente no repositório
        results = org_repo.get_all_organizacoes(search_term=search_term, limit=100)

        if not results:
            ctk.CTkLabel(self.results_frame, text="Nenhuma organização encontrada.").pack(pady=10)
            return

        for org in results:
            btn = ctk.CTkButton(self.results_frame, text=f"{org.nome_fantasia} (CNPJ: {org.cnpj or 'N/A'})",
                                anchor="w", fg_color="transparent",
                                command=lambda o=org: self._select_organization(o))
            btn.pack(fill="x", pady=2, padx=5)

    def _select_organization(self, org):
        self.selected_org = org
        self.destroy()

    def get_selection(self):
        self.wait_window()
        return self.selected_org