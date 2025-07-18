import customtkinter as ctk
from tkinter import ttk, messagebox
from .atendimento_form_window import AtendimentoFormWindow
from dto.pessoa import Pessoa
from datetime import datetime

class AtendimentosView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._create_widgets()
        self.refresh_atendimentos_list()

    # MUDANÇA: Novo método para reagir ao evento global
    def on_data_updated(self):
        """
        Este método é chamado pelo sistema de eventos da MainApplication
        sempre que dados relevantes para esta view são alterados.
        """
        self.refresh_atendimentos_list()

    def _create_widgets(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text="Gestão de Atendimentos", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header_frame, text="Novo Atendimento", command=self.open_atendimento_form).grid(row=0, column=2, sticky="e")
        
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Status", "Prioridade", "Título", "Solicitante", "Responsável", "Data Abertura")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        col_widths = {"ID": 50, "Status": 120, "Prioridade": 100, "Título": 350, "Solicitante": 200, "Responsável": 150, "Data Abertura": 120}
        for col, width in col_widths.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w")
        self.tree.column("ID", anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self.on_atendimento_double_click)

    def on_atendimento_double_click(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        atendimento_id = int(selected_item)
        self.open_atendimento_form(atendimento_id=atendimento_id)

    def open_atendimento_form(self, atendimento_id=None, pessoa_pre_selecionada: Pessoa | None = None):
        if hasattr(self, 'atendimento_form') and self.atendimento_form.winfo_exists():
            self.atendimento_form.focus()
            return
        
        self.atendimento_form = AtendimentoFormWindow(self, self.repos, self.app, atendimento_id=atendimento_id, pessoa_pre_selecionada=pessoa_pre_selecionada)

    def refresh_atendimentos_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        atendimentos = crm_repo.get_all_atendimentos()
        for atendimento in atendimentos:
            solicitante = atendimento['nome_solicitante'] or "N/A (Sistema)"
            data_abertura_str = atendimento.get('data_abertura')
            data_formatada = ""
            if data_abertura_str:
                try:
                    data_formatada = datetime.strptime(data_abertura_str, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    data_formatada = data_abertura_str.split(" ")[0]

            values = (
                atendimento['id_atendimento'],
                atendimento.get('status', ''),
                atendimento.get('prioridade', ''),
                atendimento.get('titulo', ''),
                solicitante,
                atendimento.get('responsavel_atendimento', ''),
                data_formatada
            )
            self.tree.insert("", "end", values=values, iid=atendimento['id_atendimento'])