import customtkinter as ctk
from tkinter import messagebox
from functions import ui_helpers
from .person_search_window import PersonSearchWindow
# --- ALTERAÇÃO: Importa a classe correta 'CTkAutocompleteComboBox' ---
from .custom_widgets import CTkAutocompleteComboBox

class AddRelationWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, person_id_origem):
        super().__init__(parent)
        self.repos = repos
        self.parent_form = parent
        self.person_id_origem = person_id_origem
        
        self.selected_person_destino = None

        self.title("Adicionar Relação")
        self.geometry("450x200")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._create_widgets()
        self.after(50, lambda: ui_helpers.center_window(self)) # Centraliza após renderizar

    def _create_widgets(self):
        self.columnconfigure(1, weight=1)
        
        row_counter = 0

        # Campo Tipo de Relação
        ctk.CTkLabel(self, text="Tipo de Relação:").grid(row=row_counter, column=0, padx=10, pady=10, sticky="w")
        rel_types = ["", "Pai", "Mãe", "Filho(a)", "Cônjuge", "Irmão/Irmã", "Assessor(a)", "Sócio(a)", "Amigo(a)", "Outro"]
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        self.relation_type_menu = CTkAutocompleteComboBox(self, values=rel_types, height=28)
        self.relation_type_menu.grid(row=row_counter, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        row_counter += 1

        # Campo Pessoa Relacionada
        ctk.CTkLabel(self, text="Pessoa Relacionada:").grid(row=row_counter, column=0, padx=10, pady=10, sticky="w")
        self.person_entry = ctk.CTkEntry(self, placeholder_text="Clique em 'Buscar' para selecionar...", state="readonly")
        self.person_entry.grid(row=row_counter, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self, text="Buscar...", command=self._search_person).grid(row=row_counter, column=2, padx=10, pady=10)
        row_counter += 1

        # Botões de Ação (Salvar/Cancelar)
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=row_counter, column=0, columnspan=3, pady=20, sticky="e")
        ctk.CTkButton(button_frame, text="Salvar Relação", command=self._save).pack(side="right", padx=10)
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", command=self.destroy).pack(side="right")
        row_counter += 1

        self.rowconfigure(row_counter, weight=1)

    def _search_person(self):
        search_win = PersonSearchWindow(self, self.repos, exclude_id=self.person_id_origem)
        person = search_win.get_selection()
        if person:
            self.selected_person_destino = person
            original_state = self.person_entry.cget("state") 
            self.person_entry.configure(state="normal")
            self.person_entry.delete(0, ctk.END)
            self.person_entry.insert(0, person.nome)
            self.person_entry.configure(state=original_state)

    def _save(self):
        relation_type = self.relation_type_menu.get()
        if not self.selected_person_destino:
            messagebox.showerror("Erro", "Nenhuma pessoa selecionada.", parent=self)
            return
        if not relation_type:
            messagebox.showwarning("Campo Vazio", "Selecione o tipo de relação.", parent=self)
            return

        person_repo = self.repos.get("person")
        if not person_repo:
            messagebox.showerror("Erro Crítico", "Repositório de Pessoas não encontrado.", parent=self)
            return

        success = person_repo.save_relacionamento(self.person_id_origem, self.selected_person_destino.id_pessoa, relation_type)
        if success:
            messagebox.showinfo("Sucesso", "Nova relação salva com sucesso!", parent=self)
            if hasattr(self.parent_form, 'refresh_relationships_list'):
                self.parent_form.refresh_relationships_list()
            self.destroy()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o relacionamento. (Verifique se a relação já existe).", parent=self)