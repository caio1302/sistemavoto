import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

from functions import ui_helpers
from popups.datepicker import DatePicker

class EventoFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app, evento_id=None, pre_selected_date=None):
        super().__init__(parent)
        self.repos = repos
        self.app = app # MUDANÇA: Armazena a instância da aplicação principal
        self.evento_id = evento_id
        
        self.title("Novo Evento" if not self.evento_id else "Editar Evento")
        self.geometry("600x450")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) 

        self._create_widgets()

        if self.evento_id:
            self._load_evento_data()
        elif pre_selected_date:
            self.entry_data.insert(0, pre_selected_date.strftime("%d/%m/%Y"))

        self.after(50, lambda: ui_helpers.center_window(self))
        self.entry_titulo.focus_set()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(main_frame, text="Título do Evento:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,5))
        self.entry_titulo = ctk.CTkEntry(main_frame, placeholder_text="Ex: Reunião com Lideranças")
        self.entry_titulo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,15))
        
        ctk.CTkLabel(main_frame, text="Descrição / Pauta:").grid(row=2, column=0, columnspan=2, sticky="nw", pady=(0,5))
        self.text_descricao = ctk.CTkTextbox(main_frame, height=100)
        self.text_descricao.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0,15))
        
        details_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        details_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        details_frame.grid_columnconfigure((1,3), weight=1)
        
        ctk.CTkLabel(details_frame, text="Data:").grid(row=0, column=0, sticky="w")
        self.entry_data = ctk.CTkEntry(details_frame)
        self.entry_data.grid(row=0, column=1, sticky="ew", padx=10)
        self.entry_data.bind("<1>", lambda e: DatePicker(self, self.entry_data))
        
        ctk.CTkLabel(details_frame, text="Local:").grid(row=1, column=0, sticky="w", pady=(10,0))
        self.entry_local = ctk.CTkEntry(details_frame)
        self.entry_local.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(10,0), padx=10)
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="e", padx=20, pady=10)
        ctk.CTkButton(button_frame, text="Salvar Evento", command=self._save).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")

    def _load_evento_data(self):
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        evento = crm_repo.get_evento_by_id(self.evento_id)
        if not evento:
            messagebox.showerror("Erro", "Evento não encontrado.", parent=self)
            self.destroy(); return
        
        self.entry_titulo.insert(0, evento.get('titulo', ''))
        self.text_descricao.insert("1.0", evento.get('descricao', ''))
        self.entry_local.insert(0, evento.get('local', ''))
        
        data_db = evento.get('data_evento', '')
        if data_db:
            try:
                data_display = datetime.strptime(data_db, "%Y-%m-%d").strftime("%d/%m/%Y")
                self.entry_data.insert(0, data_display)
            except (ValueError, TypeError):
                self.entry_data.insert(0, data_db)

    def _save(self):
        titulo = self.entry_titulo.get().strip()
        data_str = self.entry_data.get().strip()
        if not titulo or not data_str:
            messagebox.showerror("Erro de Validação", "Título e Data são obrigatórios.", parent=self)
            return
        
        try:
            data_db = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erro de Formato", "A data deve estar no formato DD/MM/AAAA.", parent=self)
            return
        
        evento_data = {
            "titulo": titulo, 
            "data_evento": data_db, 
            "hora_inicio": None,
            "hora_fim": None,
            "local": self.entry_local.get().strip(),
            "descricao": self.text_descricao.get("1.0", "end-1c").strip(),
        }

        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        success = crm_repo.save_evento(evento_data, self.evento_id or 0)
        if success:
            messagebox.showinfo("Sucesso", "Evento salvo com sucesso!", parent=self)
            
            # MUDANÇA: Dispara o evento global
            self.app.dispatch("data_changed", source="evento_form")

            self.destroy()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o evento.", parent=self)