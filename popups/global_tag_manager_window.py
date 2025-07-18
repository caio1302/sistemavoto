# --- START OF FILE popups/global_tag_manager_window.py ---

import tkinter as tk
from tkinter import ttk, messagebox

from functions import ui_helpers

class GlobalTagManagerWindow(tk.Toplevel):
    def __init__(self, parent_app_or_toplevel, loader_instance, parent_edit_window_instance=None):
        super().__init__(parent_app_or_toplevel) 
        self.loader = loader_instance
        self.parent_edit_window_ref = parent_edit_window_instance 

        self.title("Gerenciar Tags Globais de CRM")
        self.geometry("450x500") 
        self.resizable(False, True) 
        self.configure(bg="white")
        self.transient(parent_app_or_toplevel) 
        self.grab_set()
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        ui_helpers.center_window(self)

        self._create_tag_manager_widgets()
        self._populate_global_tag_list_ui()

    def _create_tag_manager_widgets(self):
        main_frame = ttk.Frame(self, padding="10", style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        list_tags_frame = ttk.LabelFrame(main_frame, text="Tags de CRM Existentes", style="TLabelframe")
        list_tags_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        cols_tags = ('Tag',)
        self.global_tags_tree = ttk.Treeview(list_tags_frame, columns=cols_tags, show='headings', selectmode='browse', height=10)
        vsb_tags = ttk.Scrollbar(list_tags_frame, orient="vertical", command=self.global_tags_tree.yview)
        self.global_tags_tree.configure(yscrollcommand=vsb_tags.set)
        
        self.global_tags_tree.heading('Tag', text='Nome da Tag de CRM'); self.global_tags_tree.column('Tag', width=300, anchor='w')
        
        vsb_tags.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0,5))
        self.global_tags_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        button_frame_for_list = ttk.Frame(list_tags_frame, style="TFrame")
        button_frame_for_list.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame_for_list, text="Apagar Tag Selecionada", command=self._delete_selected_global_tag).pack(side=tk.LEFT, expand=True, padx=5)

        add_tag_frame = ttk.LabelFrame(main_frame, text="Adicionar Nova Tag de CRM", style="TLabelframe")
        add_tag_frame.pack(fill=tk.X)
        
        ttk.Label(add_tag_frame, text="Nome da Nova Tag:", background='white').pack(pady=(5,0), padx=10, anchor='w')
        self.new_global_tag_entry = ttk.Entry(add_tag_frame, width=40)
        self.new_global_tag_entry.pack(fill=tk.X, padx=10, pady=(0,5))
        ttk.Button(add_tag_frame, text="Adicionar Tag Global", command=self._add_new_global_tag).pack(pady=5)

        ttk.Button(main_frame, text="Fechar Gerenciador de Tags", command=self.destroy).pack(pady=(10,0))


    def _populate_global_tag_list_ui(self):
        for item in self.global_tags_tree.get_children(): 
            self.global_tags_tree.delete(item)
        
        all_crm_tags = self.loader.get_all_contact_tag_names() 
        for tag_name_crm in all_crm_tags:
            self.global_tags_tree.insert('', 'end', iid=tag_name_crm, values=(tag_name_crm,)) 

    def _add_new_global_tag(self):
        new_tag_name_to_add = self.new_global_tag_entry.get().strip()
        if not new_tag_name_to_add:
            messagebox.showwarning("Campo Vazio", "O nome da tag de CRM não pode ser vazio.", parent=self)
            return
        
        if self.loader.add_global_contact_tag(new_tag_name_to_add):
            messagebox.showinfo("Sucesso", f"Tag de CRM '{new_tag_name_to_add}' adicionada globalmente.", parent=self)
            self.new_global_tag_entry.delete(0, tk.END) 
            self._populate_global_tag_list_ui() 
        else: 
            messagebox.showinfo("Informação", f"A tag de CRM '{new_tag_name_to_add}' já existe ou ocorreu um erro ao adicionar.", parent=self)

    def _delete_selected_global_tag(self):
        selected_item_iid = self.global_tags_tree.focus() 
        if not selected_item_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma tag de CRM para apagar.", parent=self)
            return
        
        tag_name_to_delete_crm = selected_item_iid
        msg_confirm = (f"Tem certeza que deseja apagar a tag de CRM '{tag_name_to_delete_crm}'?\n\n"
                       "Isso a removerá de TODOS os contatos que a utilizam.")
        if messagebox.askyesno("Confirmar Exclusão Global", msg_confirm, icon='warning', parent=self):
            if self.loader.delete_global_contact_tag(tag_name_to_delete_crm):
                messagebox.showinfo("Sucesso", f"Tag de CRM '{tag_name_to_delete_crm}' apagada globalmente.", parent=self)
                self._populate_global_tag_list_ui() 
            else:
                messagebox.showerror("Erro", "Falha ao apagar a tag de CRM do banco de dados.", parent=self)

    def destroy(self):
        if self.parent_edit_window_ref and self.parent_edit_window_ref.winfo_exists():
            # Atualiza os checkboxes de tag na janela de edição ao fechar
            self.parent_edit_window_ref._populate_tags_checkboxes_ui()
        super().destroy()

# --- END OF FILE popups/global_tag_manager_window.py ---