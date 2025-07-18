import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import logging # Adicionado para registrar avisos

from functions import ui_helpers
from popups.datepicker import DatePicker
from .custom_widgets import CTkAutocompleteComboBox

class ProposicaoFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app, proposicao_id=None):
        super().__init__(parent)
        self.repos = repos
        self.app = app
        
        self.proposicao_id = proposicao_id if proposicao_id is not None else 0
        self.proposicao_data = {}
        self.tema_checkboxes = {}

        self.title("Nova Proposição" if not self.proposicao_id else "Editar Proposição")
        self.geometry("750x600")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) 

        self._create_widgets()
        
        if self.proposicao_id:
            self._load_proposicao_data()

        self.after(50, lambda: ui_helpers.center_window(self))
        self.entry_titulo.focus_set()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        # Título
        ctk.CTkLabel(main_frame, text="Título:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_titulo = ctk.CTkEntry(main_frame, placeholder_text="Título completo da proposição")
        self.entry_titulo.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Tipo
        ctk.CTkLabel(main_frame, text="Tipo:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tipos_proposicao = ["", "Projeto de Lei", "Indicação", "Requerimento", "Moção", "Outro"]
        self.option_tipo = CTkAutocompleteComboBox(main_frame, values=tipos_proposicao, height=28)
        self.option_tipo.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        # Autor
        ctk.CTkLabel(main_frame, text="Autor(es):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.entry_autor = ctk.CTkEntry(main_frame, placeholder_text="Nome do autor ou autores")
        self.entry_autor.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        # Descrição
        ctk.CTkLabel(main_frame, text="Descrição / Ementa:").grid(row=3, column=0, sticky="nw", padx=10, pady=5)
        self.text_descricao = ctk.CTkTextbox(main_frame, height=100)
        self.text_descricao.grid(row=3, column=1, sticky="nsew", padx=10, pady=5)

        # Detalhes (Data, Status)
        details_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        details_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
        details_frame.columnconfigure((0, 2), weight=0)
        details_frame.columnconfigure((1, 3), weight=1)

        # Data
        ctk.CTkLabel(details_frame, text="Data:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_data = ctk.CTkEntry(details_frame, placeholder_text="Clique para selecionar...")
        self.entry_data.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.entry_data.bind("<1>", lambda e: DatePicker(self, self.entry_data))

        # Status
        ctk.CTkLabel(details_frame, text="Status:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
        status_proposicao = ["", "Protocolado", "Em Comissão", "Aprovado", "Rejeitado", "Arquivado"]
        self.option_status = CTkAutocompleteComboBox(details_frame, values=status_proposicao, height=28)
        self.option_status.grid(row=0, column=3, sticky="ew", padx=10, pady=5)

        # Temas
        temas_frame = ctk.CTkScrollableFrame(main_frame, label_text="Temas Relacionados")
        temas_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        temas_frame.columnconfigure(0, weight=1)
        
        misc_repo = self.repos.get("misc")
        if misc_repo:
            all_temas = misc_repo.get_all_temas()
            for tema in all_temas:
                # --- CORREÇÃO AQUI: Verifica se 'tema' é um dicionário e tem as chaves necessárias ---
                if isinstance(tema, dict) and 'id_tema' in tema and 'nome' in tema:
                    var = ctk.BooleanVar()
                    cb = ctk.CTkCheckBox(temas_frame, text=tema['nome'], variable=var)
                    cb.pack(anchor="w", padx=10, pady=5)
                    self.tema_checkboxes[tema['id_tema']] = var
                else:
                    logging.warning(f"Item 'tema' inválido recebido do banco de dados: {tema}")


        # Botões do rodapé
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="se", padx=20, pady=10)
        ctk.CTkButton(button_frame, text="Salvar", command=self._save).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Fechar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")

    def _load_proposicao_data(self):
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        data = crm_repo.get_proposicao_by_id(self.proposicao_id)
        if not data:
            messagebox.showerror("Erro", "Proposição não encontrada.", parent=self)
            self.destroy()
            return
        
        self.proposicao_data = data
        
        self.entry_titulo.insert(0, data.get('titulo', ''))
        self.option_tipo.set(data.get('tipo', ''))
        self.entry_autor.insert(0, data.get('autor', ''))
        self.text_descricao.insert("1.0", data.get('descricao', ''))
        self.option_status.set(data.get('status', ''))
        
        data_db = data.get('data_proposicao', '')
        if data_db:
            try:
                data_display = datetime.strptime(data_db, "%Y-%m-%d").strftime("%d/%m/%Y")
                self.entry_data.insert(0, data_display)
            except (ValueError, TypeError):
                self.entry_data.insert(0, data_db)

        temas_ids = data.get('temas_ids', [])
        for tema_id, var in self.tema_checkboxes.items():
            if tema_id in temas_ids:
                var.set(True)

    def _save(self):
        titulo = self.entry_titulo.get().strip()
        if not titulo:
            messagebox.showerror("Erro de Validação", "O título da proposição é obrigatório.", parent=self)
            return

        data_str = self.entry_data.get().strip()
        data_db = ""
        if data_str:
            try:
                data_db = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Erro de Formato", "A data deve estar no formato DD/MM/AAAA.", parent=self)
                return
        
        proposicao_data = {
            "titulo": titulo,
            "tipo": self.option_tipo.get(),
            "autor": self.entry_autor.get().strip(),
            "data_proposicao": data_db,
            "status": self.option_status.get(),
            "descricao": self.text_descricao.get("1.0", "end-1c").strip(),
        }
        
        selected_temas = [tema_id for tema_id, var in self.tema_checkboxes.items() if var.get()]
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        success = crm_repo.save_proposicao(proposicao_data, selected_temas, self.proposicao_id)
        if success:
            messagebox.showinfo("Sucesso", "Proposição salva com sucesso!", parent=self)
            
            self.app.dispatch("data_changed", source="proposicao_form")

            self.destroy()
        else:
            messagebox.showerror("Erro", "Falha ao salvar a proposição no banco de dados.", parent=self)