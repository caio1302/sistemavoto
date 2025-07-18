import customtkinter as ctk
from tkinter import ttk, messagebox
from .proposicao_form_window import ProposicaoFormWindow
from datetime import datetime

class ProposicoesView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        
        self.selected_proposicao_id = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)

        self._create_widgets()
        self.refresh_proposicoes_list()

    # MUDANÇA: Novo método para reagir ao evento global
    def on_data_updated(self):
        """
        Este método é chamado pelo sistema de eventos da MainApplication
        sempre que dados relevantes para esta view são alterados.
        """
        self.refresh_proposicoes_list()

    def _create_widgets(self):
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text="Gestão de Proposições", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header_frame, text="Nova Proposição", command=self.open_proposicao_form).grid(row=0, column=1, sticky="e")
        
        tree_frame = ctk.CTkFrame(left_panel)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Tipo", "Título", "Autor", "Status", "Data")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        col_widths = {"ID": 50, "Tipo": 150, "Título": 400, "Autor": 200, "Status": 120, "Data": 100}
        for col, width in col_widths.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w")
        self.tree.column("ID", anchor="center"); self.tree.column("Data", anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        self.right_panel = ctk.CTkFrame(self, width=280)
        self.right_panel.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.right_panel.grid_propagate(False)
        self.right_panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self.right_panel, text="Detalhes da Proposição", font=ctk.CTkFont(weight="bold")).pack(pady=10, padx=10, anchor="w")
        self.details_title = ctk.CTkLabel(self.right_panel, text="Selecione um item na lista", wraplength=260, justify="left")
        self.details_title.pack(pady=5, padx=10, anchor="w")
        self.details_text = ctk.CTkTextbox(self.right_panel, state="disabled", fg_color="transparent")
        self.details_text.pack(pady=5, padx=10, fill="both", expand=True)

        self.buttons_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.buttons_frame.pack(pady=10, padx=10, fill="x", side="bottom")

    def refresh_proposicoes_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        proposicoes = crm_repo.get_all_proposicoes()
        for prop in proposicoes:
            data_db = prop.get('data_proposicao', '')
            data_display = ""
            if data_db:
                try:
                    data_display = datetime.strptime(data_db, "%Y-%m-%d").strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    data_display = data_db
            
            values = (
                prop['id_proposicao'], prop.get('tipo', ''), prop.get('titulo', ''),
                prop.get('autor', ''), prop.get('status', ''), data_display
            )
            self.tree.insert("", "end", values=values, iid=prop['id_proposicao'])
        self._clear_details_panel()

    def on_item_select(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item: return
        self.selected_proposicao_id = int(selected_item)
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        proposicao = crm_repo.get_proposicao_by_id(self.selected_proposicao_id)
        self._populate_details_panel(proposicao)

    def on_item_double_click(self, event=None):
        if not self.selected_proposicao_id: return
        self.open_proposicao_form(proposicao_id=self.selected_proposicao_id)

    def _populate_details_panel(self, proposicao):
        self._clear_details_panel()
        if not proposicao: return
        
        self.details_title.configure(text=proposicao.get('titulo', ''))
        
        details_content = (
            f"Tipo: {proposicao.get('tipo', 'N/A')}\n"
            f"Autor: {proposicao.get('autor', 'N/A')}\n"
            f"Data: {proposicao.get('data_proposicao', 'N/A')}\n"
            f"Status: {proposicao.get('status', 'N/A')}\n\n"
            f"Descrição:\n{proposicao.get('descricao', '')}"
        )
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", details_content)
        self.details_text.configure(state="disabled")

        edit_btn = ctk.CTkButton(self.buttons_frame, text="Editar", command=self.on_item_double_click)
        edit_btn.pack(side="left", padx=5)
        delete_btn = ctk.CTkButton(self.buttons_frame, text="Apagar", fg_color="#D32F2F", hover_color="#B71C1C", command=self._delete_selected_proposicao)
        delete_btn.pack(side="left", padx=5)

    def _clear_details_panel(self):
        self.details_title.configure(text="Selecione um item na lista")
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.configure(state="disabled")
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()

    def _delete_selected_proposicao(self):
        if not self.selected_proposicao_id: return
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        
        titulo = self.tree.item(self.selected_proposicao_id, 'values')[2]
        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja apagar a proposição:\n\n'{titulo}'?", icon='warning'):
            if crm_repo.delete_proposicao(self.selected_proposicao_id):
                self.refresh_proposicoes_list()
    
    def open_proposicao_form(self, proposicao_id=None):
        if hasattr(self, 'proposicao_form') and self.proposicao_form.winfo_exists():
            self.proposicao_form.focus()
            return
        
        self.proposicao_form = ProposicaoFormWindow(self, self.repos, self.app, proposicao_id=proposicao_id)