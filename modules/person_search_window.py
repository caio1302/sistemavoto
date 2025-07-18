import customtkinter as ctk

class PersonSearchWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, exclude_id=None):
        super().__init__(parent)
        self.repos = repos
        self.parent_form = parent
        self.exclude_id = exclude_id
        self.selected_person = None

        self.title("Buscar Pessoa")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._create_widgets()
        self.search_entry.focus_set()
        
        # --- Para debounce ---
        self._search_job_id = None

    def _create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Digite para buscar por nome ou apelido...")
        self.search_entry.grid(row=0, column=0, padx=(0,10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_key_release) # MUDANÇA: Usa debounce

        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Pessoas Encontradas")
        self.results_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def _on_key_release(self, event=None):
        """Dispara a busca com um pequeno delay para evitar buscas a cada tecla."""
        if self._search_job_id:
            self.after_cancel(self._search_job_id)
        self._search_job_id = self.after(300, self._perform_search) # Atraso de 300ms

    # MUDANÇA: Lógica de busca agora usa o método otimizado do repositório
    def _perform_search(self):
        search_term = self.search_entry.get().strip()
        
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if len(search_term) < 2:
            ctk.CTkLabel(self.results_frame, text="Digite ao menos 2 caracteres para buscar.").pack(pady=10)
            return

        person_repo = self.repos.get("person")
        if not person_repo: return

        # Busca a primeira página de resultados que correspondem ao termo
        results = person_repo.get_paginated_pessoas(
            page=1, 
            items_per_page=100, # Mostra até 100 resultados
            search_term=search_term,
            sort_by='Nome',     # Ordena por nome
            sort_desc=False     # Em ordem crescente
        )
        
        # Filtra para remover o ID excluído, se houver
        if self.exclude_id:
            results = [p for p in results if p.id_pessoa != self.exclude_id]

        if not results:
            ctk.CTkLabel(self.results_frame, text="Nenhuma pessoa encontrada.").pack(pady=10)
            return

        for pessoa in results:
            display_text = f"{pessoa.nome} ({pessoa.apelido or 'N/A'})"
            btn = ctk.CTkButton(self.results_frame, text=display_text,
                                anchor="w", fg_color="transparent",
                                command=lambda p=pessoa: self._select_person(p))
            btn.pack(fill="x", pady=2, padx=5)

    def _select_person(self, pessoa):
        self.selected_person = pessoa
        self.destroy()

    def get_selection(self):
        self.wait_window()
        return self.selected_person