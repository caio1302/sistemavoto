import customtkinter as ctk
# MUDANÇA AQUI: Importar ttk explicitamente de tkinter
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from functions import ui_helpers
from .custom_widgets import CTkAutocompleteComboBox
from dto.pessoa import Pessoa
from .person_search_window import PersonSearchWindow
from .organization_search_window import OrganizationSearchWindow

class AtendimentoFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app, atendimento_id=None, pessoa_pre_selecionada: Pessoa | None = None):
        super().__init__(parent)
        self.repos = repos
        self.app = app
        self.atendimento_id = atendimento_id
        
        self.atendimento_data = {}
        self.selected_person_id = None
        self.selected_org_id = None

        title = "Novo Atendimento" if not self.atendimento_id else "Detalhes do Atendimento"
        self.title(title)
        self.geometry("800x800")
        
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self._create_widgets()

        if self.atendimento_id:
            self._load_atendimento_data()
        elif pessoa_pre_selecionada:
            self.selected_person_id = pessoa_pre_selecionada.id_pessoa
            # Para entries com state='readonly', precisa habilitar e desabilitar para setar texto.
            original_solicitante_state = self.solicitante_entry.cget("state") 
            self.solicitante_entry.configure(state="normal")
            self.solicitante_entry.delete(0, "end")
            self.solicitante_entry.insert(0, f"Pessoa: {pessoa_pre_selecionada.nome}")
            self.solicitante_entry.configure(state=original_solicitante_state)
        
        self.after(100, self.setup_focus_and_position)
        
    def setup_focus_and_position(self):
        ui_helpers.center_window(self)
        self.entry_titulo.focus_set()
        self.lift()
        self.focus_force()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(4, weight=0) # Linha da descrição de demanda não expande tanto.
        main_frame.grid_rowconfigure(6, weight=1) # Histórico de updates expande verticalmente.


        # Título
        ctk.CTkLabel(main_frame, text="Título:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,5))
        self.entry_titulo = ctk.CTkEntry(main_frame)
        self.entry_titulo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Solicitante (Pessoa/Organização)
        solicitante_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        solicitante_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        solicitante_frame.grid_columnconfigure(0, weight=1) # Campo de solicitante se expande.
        self.solicitante_entry = ctk.CTkEntry(solicitante_frame, state="readonly", placeholder_text="Nenhum solicitante vinculado...")
        self.solicitante_entry.grid(row=0, column=0, sticky="ew")
        # Alturas fixas para os botões para alinhar com o entry
        ctk.CTkButton(solicitante_frame, text="Vincular Pessoa", width=120, height=28, command=self._search_person).grid(row=0, column=1, padx=(10,5))
        ctk.CTkButton(solicitante_frame, text="Vincular Organização", width=150, height=28, command=self._search_organization).grid(row=0, column=2, padx=5)
        
        # Descrição da Demanda
        ctk.CTkLabel(main_frame, text="Descrição da Demanda:").grid(row=3, column=0, columnspan=2, sticky="w", pady=(0,5))
        self.text_descricao = ctk.CTkTextbox(main_frame, height=80)
        self.text_descricao.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Detalhes (Responsável, Status, Prioridade)
        details_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        details_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        details_frame.columnconfigure((0,2), weight=0) # Labels não expandem
        details_frame.columnconfigure((1,3), weight=1) # Inputs/Dropdowns expandem

        ctk.CTkLabel(details_frame, text="Responsável:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_responsavel = ctk.CTkEntry(details_frame)
        self.entry_responsavel.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(details_frame, text="Status:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        status_options = ["Aberto", "Em Andamento", "Concluído", "Cancelado"]
        self.option_status = CTkAutocompleteComboBox(details_frame, values=status_options, height=28)
        self.option_status.grid(row=0, column=3, sticky="ew", padx=5, pady=5)
        
        ctk.CTkLabel(details_frame, text="Prioridade:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        priority_options = ["Baixa", "Normal", "Alta", "Urgente"]
        self.option_prioridade = CTkAutocompleteComboBox(details_frame, values=priority_options, height=28)
        self.option_prioridade.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Histórico de Atualizações
        self.updates_section = ctk.CTkFrame(main_frame)
        self.updates_section.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=10)
        self.updates_section.columnconfigure(0, weight=1)
        self.updates_section.rowconfigure(1, weight=1)

        ctk.CTkLabel(self.updates_section, text="Histórico de Atualizações", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        style = ttk.Style() 
        bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1] if ctk.get_appearance_mode() == "Dark" else ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0]
        text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"][1] if ctk.get_appearance_mode() == "Dark" else ctk.ThemeManager.theme["CTkLabel"]["text_color"][0]
        header_bg = ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"][1] if ctk.get_appearance_mode() == "Dark" else ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"][0]
        
        style.theme_use("clam")
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0, rowheight=24)
        style.map("Custom.Treeview", background=[('selected', ctk.ThemeManager.theme["CTkButton"]["fg_color"][1] if ctk.get_appearance_mode() == "Dark" else ctk.ThemeManager.theme["CTkButton"]["fg_color"][0])])
        style.configure("Custom.Treeview.Heading", background=header_bg, foreground=text_color, relief="flat", font=ctk.CTkFont(family="Calibri", size=10, weight="bold"))


        self.updates_tree = ttk.Treeview(self.updates_section, columns=("Data", "Autor", "Descrição"), show="headings", height=4, style="Custom.Treeview")
        self.updates_tree.heading("Data", text="Data"); self.updates_tree.column("Data", width=120)
        self.updates_tree.heading("Autor", text="Autor"); self.updates_tree.column("Autor", width=150)
        self.updates_tree.heading("Descrição", text="Descrição"); self.updates_tree.column("Descrição", width=450)
        self.updates_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        ctk.CTkLabel(self.updates_section, text="Nova Atualização:").grid(row=2, column=0, sticky="w", padx=10, pady=(10,5))
        self.text_new_update = ctk.CTkTextbox(self.updates_section, height=60)
        self.text_new_update.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        ctk.CTkButton(self.updates_section, text="Registrar Atualização", command=self._save_update).grid(row=4, column=0, pady=5, padx=10)
        
        self.updates_section.grid_remove() 
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="se", padx=20, pady=10)
        ctk.CTkButton(button_frame, text="Salvar", command=self._save).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Fechar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")

    def _load_atendimento_data(self):
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        self.atendimento_data = crm_repo.get_atendimento_by_id(self.atendimento_id)
        if not self.atendimento_data:
            messagebox.showerror("Erro", "Atendimento não encontrado.", parent=self)
            self.destroy(); return
            
        self.entry_titulo.insert(0, self.atendimento_data.get('titulo', ''))
        self.text_descricao.insert("1.0", self.atendimento_data.get('descricao_demanda', ''))
        self.entry_responsavel.insert(0, self.atendimento_data.get('responsavel_atendimento', ''))
        self.option_status.set(self.atendimento_data.get('status', 'Aberto'))
        self.option_prioridade.set(self.atendimento_data.get('prioridade', 'Normal'))
        
        solicitante = self.atendimento_data.get('nome_solicitante', "N/A (Sistema)")
        original_solicitante_state = self.solicitante_entry.cget("state")
        self.solicitante_entry.configure(state="normal")
        self.solicitante_entry.delete(0, ctk.END)
        self.solicitante_entry.insert(0, solicitante)
        self.solicitante_entry.configure(state=original_solicitante_state)
        
        self.selected_person_id = self.atendimento_data.get('id_pessoa')
        self.selected_org_id = self.atendimento_data.get('id_organizacao')
        
        self.updates_section.grid() 
        self.refresh_updates_list()

    def refresh_updates_list(self):
        if not self.updates_tree.winfo_exists(): return

        for item in self.updates_tree.get_children(): 
            if self.updates_tree.winfo_exists(): 
                self.updates_tree.delete(item)
            else: return
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        updates = crm_repo.get_updates_for_atendimento(self.atendimento_id)
        for update in updates:
            if self.updates_tree.winfo_exists():
                self.updates_tree.insert("", "end", values=(update['data_update'], update['autor_update'], update['descricao_update']))
            else: return


    def _save_update(self):
        descricao = self.text_new_update.get("1.0", "end-1c").strip()
        if not descricao:
            messagebox.showwarning("Campo Vazio", "A descrição da atualização não pode ser vazia.", parent=self)
            return
        
        autor_update = self.app.logged_in_user.nome_usuario if hasattr(self.app, 'logged_in_user') and self.app.logged_in_user else "Sistema"

        update_data = {
            "id_atendimento": self.atendimento_id,
            "data_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "autor_update": autor_update,
            "descricao_update": descricao
        }
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        if crm_repo.save_atendimento_update(update_data):
            self.text_new_update.delete("1.0", "end")
            self.refresh_updates_list()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar a atualização.", parent=self)

    def _search_person(self):
        search_win = PersonSearchWindow(self, self.repos)
        person = search_win.get_selection()
        if person:
            self.selected_person_id = person.id_pessoa
            self.selected_org_id = None
            original_solicitante_state = self.solicitante_entry.cget("state")
            self.solicitante_entry.configure(state="normal")
            self.solicitante_entry.delete(0, ctk.END)
            self.solicitante_entry.insert(0, f"Pessoa: {person.nome}")
            self.solicitante_entry.configure(state=original_solicitante_state)

    def _search_organization(self):
        search_win = OrganizationSearchWindow(self, self.repos)
        org = search_win.get_selection()
        if org:
            self.selected_org_id = org.id_organizacao
            self.selected_person_id = None
            original_solicitante_state = self.solicitante_entry.cget("state")
            self.solicitante_entry.configure(state="normal")
            self.solicitante_entry.delete(0, ctk.END)
            self.solicitante_entry.insert(0, f"Organização: {org.nome_fantasia}")
            self.solicitante_entry.configure(state=original_solicitante_state)

    def _save(self):
        titulo = self.entry_titulo.get().strip()
        if not titulo:
            messagebox.showerror("Erro de Validação", "O título é obrigatório.", parent=self)
            return
            
        if self.selected_person_id is None and self.selected_org_id is None:
            messagebox.showwarning("Solicitante Necessário", "Vincule uma Pessoa ou Organização a este atendimento.", parent=self)
            return

        atendimento_data = {
            "id_pessoa": self.selected_person_id,
            "id_organizacao": self.selected_org_id,
            "titulo": titulo,
            "descricao_demanda": self.text_descricao.get("1.0", "end-1c").strip(),
            "responsavel_atendimento": self.entry_responsavel.get().strip(),
            "status": self.option_status.get(), 
            "prioridade": self.option_prioridade.get() 
        }
        
        if not self.atendimento_id:
            atendimento_data["data_abertura"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        success = crm_repo.save_atendimento(atendimento_data, self.atendimento_id or 0)
        if success:
            messagebox.showinfo("Sucesso", "Atendimento salvo com sucesso!", parent=self)

            self.app.dispatch("data_changed", source="atendimento_form")
            
            # --- ALTERAÇÃO: A janela agora fecha sempre ao salvar com sucesso ---
            self.destroy()
        else:
            messagebox.showerror("Erro", "Falha ao salvar o atendimento.", parent=self)