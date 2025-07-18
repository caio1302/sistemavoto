import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import config
from functions import ui_helpers
from dto.task import Task
from .datepicker import DatePicker
# --- ALTERAÇÃO: Importa a classe correta 'CTkAutocompleteComboBox' ---
from modules.custom_widgets import CTkAutocompleteComboBox

class TaskManagementWindow(tk.Toplevel):
    def __init__(self, parent, repos: dict, app, sq_candidato_pre_fill=None, nome_urna_pre_fill=None):
        super().__init__(parent)
        self.repos = repos
        self.app = app
        self.parent_app = parent 

        self.sq_candidato_pre_fill_on_open = sq_candidato_pre_fill 
        self.nome_urna_pre_fill_on_open = nome_urna_pre_fill   

        self.title("Gerenciador de Tarefas e Agendamentos")
        self.geometry("1000x700") 
        self.resizable(True, True)
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        ui_helpers.center_window(self)

        self.current_selected_task_id = 0 

        self._create_task_widgets()
        self._populate_tasks_tree_ui() 
        if self.sq_candidato_pre_fill_on_open: 
            self._clear_task_form_for_new() 

    def _create_task_widgets(self):
        main_frame = ttk.Frame(self, padding="10", style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_section_pane = ttk.Frame(main_frame, style="TFrame")
        top_section_pane.pack(fill=tk.BOTH, expand=True)

        filter_options_frame = ttk.LabelFrame(top_section_pane, text="Filtros e Ações da Lista", style="TLabelframe")
        filter_options_frame.pack(fill=tk.X, pady=(0, 10))
        filter_options_frame.columnconfigure(1, weight=1)

        ttk.Label(filter_options_frame, text="Status:", background='white').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.status_filter_var = tk.StringVar(value="Todas") 
        status_filter_options = ["Todas", "Pendente", "Em Andamento", "Concluída", "Cancelada"]
        
        # --- ALTERAÇÃO: Usando a classe correta e removendo 'state' para permitir digitação/autocompletar ---
        self.status_filter_combobox = CTkAutocompleteComboBox(filter_options_frame, values=status_filter_options, 
                                                              variable=self.status_filter_var, command=self._populate_tasks_tree_ui,
                                                              height=28)
        self.status_filter_combobox.grid(row=0, column=1, sticky='ew', padx=(0,10))


        self.order_by_priority_var = tk.BooleanVar(value=True) 
        self.order_by_date_var = tk.BooleanVar(value=True)     
        ttk.Checkbutton(filter_options_frame, text="Ordenar por Prioridade", variable=self.order_by_priority_var, command=self._populate_tasks_tree_ui).grid(row=0, column=2, sticky='w', padx=(10,0))
        ttk.Checkbutton(filter_options_frame, text="Ordenar por Prazo", variable=self.order_by_date_var, command=self._populate_tasks_tree_ui).grid(row=0, column=3, sticky='w', padx=(10,0))
        ttk.Button(filter_options_frame, text="Atualizar Lista", command=self._populate_tasks_tree_ui).grid(row=0, column=4, sticky='e', padx=10, pady=5)


        cols_tasks = ('ID', 'Candidato', 'Descrição', 'Criação', 'Prazo', 'Responsável', 'Status', 'Prioridade')
        self.tasks_list_treeview = ttk.Treeview(top_section_pane, columns=cols_tasks, show='headings', selectmode='browse', height=10)
        vsb_tasks_list = ttk.Scrollbar(top_section_pane, orient="vertical", command=self.tasks_list_treeview.yview)
        self.tasks_list_treeview.configure(yscrollcommand=vsb_tasks_list.set)

        col_configs = {
            'ID': {'width': 40, 'anchor': 'center'}, 'Candidato': {'width': 150, 'anchor': 'w'},
            'Descrição': {'width': 280, 'anchor': 'w'}, 'Criação': {'width': 90, 'anchor': 'center'},
            'Prazo': {'width': 90, 'anchor': 'center'}, 'Responsável': {'width': 120, 'anchor': 'w'},
            'Status': {'width': 90, 'anchor': 'center'}, 'Prioridade': {'width': 80, 'anchor': 'center'}
        }
        for col_name, config_dict in col_configs.items():
            self.tasks_list_treeview.heading(col_name, text=col_name)
            self.tasks_list_treeview.column(col_name, width=config_dict['width'], anchor=config_dict['anchor'], stretch=tk.YES if col_name == 'Descrição' else tk.NO)
        
        vsb_tasks_list.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.tasks_list_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.tasks_list_treeview.bind("<<TreeviewSelect>>", self._on_task_selected_in_tree)

        bottom_section_pane = ttk.LabelFrame(main_frame, text="Detalhes da Tarefa Selecionada / Nova Tarefa", style="TLabelframe")
        bottom_section_pane.pack(fill=tk.X, pady=10)

        task_form_grid = ttk.Frame(bottom_section_pane, style="TFrame")
        task_form_grid.pack(fill=tk.X, padx=10, pady=5)
        
        task_form_grid.columnconfigure(1, weight=1) 
        task_form_grid.columnconfigure(3, weight=1)

        ttk.Label(task_form_grid, text="SQ Candidato:", background='white').grid(row=0, column=0, sticky='w', pady=2, padx=5)
        self.task_sq_candidato_entry = ttk.Entry(task_form_grid, width=18) 
        self.task_sq_candidato_entry.grid(row=0, column=1, sticky='ew', pady=2, padx=5)
        
        ttk.Label(task_form_grid, text="Nome Candidato:", background='white').grid(row=0, column=2, sticky='w', pady=2, padx=5)
        self.task_nome_candidato_display_entry = ttk.Entry(task_form_grid, width=35, state='readonly') 
        self.task_nome_candidato_display_entry.grid(row=0, column=3, sticky='ew', pady=2, padx=5)
            
        ttk.Label(task_form_grid, text="Descrição da Tarefa:", background='white').grid(row=1, column=0, sticky='nw', pady=2, padx=5)
        self.task_descricao_text = tk.Text(task_form_grid, height=3, width=50, font=(config.FONT_FAMILY, 10), wrap="word", relief='solid', borderwidth=1, undo=True)
        self.task_descricao_text.grid(row=1, column=1, columnspan=3, sticky='nsew', pady=2, padx=5)
        task_form_grid.grid_rowconfigure(1, weight=1)

        ttk.Label(task_form_grid, text="Data Criação:", background='white').grid(row=2, column=0, sticky='w', pady=2, padx=5)
        self.task_data_criacao_entry = ttk.Entry(task_form_grid, width=18)
        self.task_data_criacao_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=5)
        
        ttk.Label(task_form_grid, text="Prazo:", background='white').grid(row=2, column=2, sticky='w', pady=2, padx=5)
        self.task_data_prazo_entry = ttk.Entry(task_form_grid, width=18)
        self.task_data_prazo_entry.config(state="readonly")
        self.task_data_prazo_entry.bind("<Button-1>", lambda e, w=self.task_data_prazo_entry: DatePicker(self, w))
        self.task_data_prazo_entry.grid(row=2, column=3, sticky='ew', pady=2, padx=5)
        
        ttk.Label(task_form_grid, text="Responsável:", background='white').grid(row=3, column=0, sticky='w', pady=2, padx=5)
        self.task_responsavel_entry = ttk.Entry(task_form_grid, width=25)
        self.task_responsavel_entry.grid(row=3, column=1, sticky='ew', pady=2, padx=5)

        ttk.Label(task_form_grid, text="Status:", background='white').grid(row=3, column=2, sticky='w', pady=2, padx=5)
        task_status_options = ["Pendente", "Em Andamento", "Concluída", "Cancelada"]
        # --- ALTERAÇÃO: Usando a classe correta ---
        self.task_status_combobox = CTkAutocompleteComboBox(task_form_grid, values=task_status_options, height=28)
        self.task_status_combobox.grid(row=3, column=3, sticky='ew', pady=2, padx=5)

        ttk.Label(task_form_grid, text="Prioridade:", background='white').grid(row=4, column=0, sticky='w', pady=2, padx=5)
        task_priority_options = ["Baixa", "Normal", "Alta", "Urgente"]
        # --- ALTERAÇÃO: Usando a classe correta ---
        self.task_prioridade_combobox = CTkAutocompleteComboBox(task_form_grid, values=task_priority_options, height=28)
        self.task_prioridade_combobox.grid(row=4, column=1, sticky='ew', pady=2, padx=5)

        ttk.Label(task_form_grid, text="Notas Adicionais:", background='white').grid(row=5, column=0, sticky='nw', pady=2, padx=5)
        self.task_notas_text = tk.Text(task_form_grid, height=3, width=50, font=(config.FONT_FAMILY, 10), wrap="word", relief='solid', borderwidth=1, undo=True)
        self.task_notas_text.grid(row=5, column=1, columnspan=3, sticky='nsew', pady=2, padx=5)
        task_form_grid.grid_rowconfigure(5, weight=1)

        task_form_button_frame = ttk.Frame(bottom_section_pane, style="TFrame")
        task_form_button_frame.pack(pady=10)
        ttk.Button(task_form_button_frame, text="Limpar Formulário (Nova Tarefa)", command=self._clear_task_form_for_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(task_form_button_frame, text="Salvar Tarefa", command=self._save_task_from_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(task_form_button_frame, text="Marcar como Concluída", command=lambda: self._update_status_of_selected_task_in_tree("Concluída")).pack(side=tk.LEFT, padx=5)
        ttk.Button(task_form_button_frame, text="Deletar Tarefa", command=self._delete_selected_task_in_tree).pack(side=tk.LEFT, padx=5)

    def _populate_tasks_tree_ui(self):
        for item in self.tasks_list_treeview.get_children(): self.tasks_list_treeview.delete(item)

        crm_repo = self.repos.get("crm")
        person_repo = self.repos.get("person")
        if not crm_repo or not person_repo: return

        status_filter_val = self.status_filter_var.get()
        if status_filter_val == "Todas": status_filter_val = None 
        
        all_tasks_from_db = crm_repo.get_all_tasks(
            status_filter=status_filter_val,
            order_by_priority=self.order_by_priority_var.get(),
            order_by_date=self.order_by_date_var.get()
        )
        
        for task_obj in all_tasks_from_db:
            nome_candidato_para_display = "Geral (Sem Contato)"
            if task_obj.sq_candidato:
                cand_temp = person_repo.get_candidate_by_sq(task_obj.sq_candidato, 2024, "*")
                nome_candidato_para_display = cand_temp.nome_urna if cand_temp else f"SQ:{task_obj.sq_candidato}"
            
            values = (
                task_obj.id_tarefa, nome_candidato_para_display, task_obj.descricao_tarefa,
                task_obj.data_criacao.split(" ")[0] if task_obj.data_criacao else "", 
                task_obj.data_prazo, task_obj.responsavel_tarefa, 
                task_obj.status_tarefa, task_obj.prioridade_tarefa
            )
            self.tasks_list_treeview.insert('', 'end', iid=str(task_obj.id_tarefa), values=values)

    def _on_task_selected_in_tree(self, event=None):
        selected_item_iid = self.tasks_list_treeview.focus()
        if not selected_item_iid:
            self._clear_task_form_for_new()
            return
        
        task_id_selected = int(selected_item_iid)
        
        crm_repo = self.repos.get("crm")
        person_repo = self.repos.get("person")
        if not crm_repo or not person_repo: return

        selected_task_object = crm_repo.get_task_by_id(task_id_selected)

        if selected_task_object:
            self.current_selected_task_id = selected_task_object.id_tarefa
            
            self.task_sq_candidato_entry.delete(0, tk.END)
            self.task_sq_candidato_entry.insert(0, selected_task_object.sq_candidato or "")
            
            nome_cand_form = ""
            if selected_task_object.sq_candidato:
                cand_form = person_repo.get_candidate_by_sq(selected_task_object.sq_candidato, 2024, "*")
                nome_cand_form = cand_form.nome_urna if cand_form else f"SQ:{selected_task_object.sq_candidato}"
            
            self.task_nome_candidato_display_entry.configure(state='normal')
            self.task_nome_candidato_display_entry.delete(0, tk.END)
            self.task_nome_candidato_display_entry.insert(0, nome_cand_form)
            self.task_nome_candidato_display_entry.configure(state='readonly')
            
            self.task_descricao_text.delete("1.0", tk.END)
            self.task_descricao_text.insert("1.0", selected_task_object.descricao_tarefa)
            self.task_data_criacao_entry.delete(0, tk.END)
            self.task_data_criacao_entry.insert(0, selected_task_object.data_criacao)
            self.task_data_prazo_entry.delete(0, tk.END)
            self.task_data_prazo_entry.insert(0, selected_task_object.data_prazo)
            self.task_responsavel_entry.delete(0, tk.END)
            self.task_responsavel_entry.insert(0, selected_task_object.responsavel_tarefa)
            self.task_status_combobox.set(selected_task_object.status_tarefa)
            self.task_prioridade_combobox.set(selected_task_object.prioridade_tarefa)
            self.task_notas_text.delete("1.0", tk.END)
            self.task_notas_text.insert("1.0", selected_task_object.notas_tarefa)
        else:
             self._clear_task_form_for_new() 

    def _clear_task_form_for_new(self):
        self.current_selected_task_id = 0 
        self.tasks_list_treeview.selection_remove(self.tasks_list_treeview.selection()) 

        self.task_sq_candidato_entry.delete(0, tk.END)
        self.task_nome_candidato_display_entry.configure(state='normal')
        self.task_nome_candidato_display_entry.delete(0, tk.END)

        if self.sq_candidato_pre_fill_on_open:
            self.task_sq_candidato_entry.insert(0, self.sq_candidato_pre_fill_on_open)
        
        if self.nome_urna_pre_fill_on_open:
            self.task_nome_candidato_display_entry.insert(0, self.nome_urna_pre_fill_on_open)
        self.task_nome_candidato_display_entry.configure(state='readonly') 

        self.task_descricao_text.delete("1.0", tk.END)
        self.task_data_criacao_entry.delete(0, tk.END)
        self.task_data_criacao_entry.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")) 
        self.task_data_prazo_entry.delete(0, tk.END)
        self.task_responsavel_entry.delete(0, tk.END)
        self.task_status_combobox.set("Pendente")    
        self.task_prioridade_combobox.set("Normal")  
        self.task_notas_text.delete("1.0", tk.END)
        
        self.task_descricao_text.focus_set() 

    def _save_task_from_form(self):
        descricao_tarefa_val = self.task_descricao_text.get("1.0", tk.END).strip()
        if not descricao_tarefa_val:
            messagebox.showwarning("Campo Obrigatório", "A descrição da tarefa não pode estar vazia.", parent=self)
            return

        sq_candidato_val_form = self.task_sq_candidato_entry.get().strip()
        final_sq_candidato_to_save = sq_candidato_val_form if sq_candidato_val_form else None

        if not final_sq_candidato_to_save and not messagebox.askyesno("Tarefa Geral", "Nenhum candidato associado (SQ em branco).\nDeseja salvar como uma tarefa geral do sistema?", parent=self):
            return 

        task_object_to_save = Task(
            id_tarefa=self.current_selected_task_id, sq_candidato=final_sq_candidato_to_save,
            descricao_tarefa=descricao_tarefa_val, data_criacao=self.task_data_criacao_entry.get().strip(),
            data_prazo=self.task_data_prazo_entry.get().strip(), responsavel_tarefa=self.task_responsavel_entry.get().strip(),
            status_tarefa=self.task_status_combobox.get().strip(), 
            prioridade_tarefa=self.task_prioridade_combobox.get().strip(),
            notas_tarefa=self.task_notas_text.get("1.0", tk.END).strip()
        )
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        if crm_repo.save_task(task_object_to_save):
            messagebox.showinfo("Sucesso", "Tarefa salva com sucesso!", parent=self)
            self._populate_tasks_tree_ui() 
            if self.current_selected_task_id == 0: self._clear_task_form_for_new() 
        else:
            messagebox.showerror("Erro", "Falha ao salvar a tarefa no banco de dados.", parent=self)

    def _update_status_of_selected_task_in_tree(self, new_status_str: str):
        selected_item_iid = self.tasks_list_treeview.focus()
        if not selected_item_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma tarefa para atualizar.", parent=self)
            return
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        task_id_to_update = int(selected_item_iid)
        if messagebox.askyesno("Confirmar Alteração de Status", f"Deseja marcar a tarefa ID {task_id_to_update} como '{new_status_str}'?", parent=self):
            if crm_repo.update_task_status(task_id_to_update, new_status_str):
                messagebox.showinfo("Sucesso", f"Status da tarefa ID {task_id_to_update} alterado para '{new_status_str}'.", parent=self)
                self._populate_tasks_tree_ui() 
                if self.current_selected_task_id == task_id_to_update: 
                    self.task_status_combobox.set(new_status_str)
            else:
                messagebox.showerror("Erro", "Falha ao atualizar o status da tarefa.", parent=self)

    def _delete_selected_task_in_tree(self):
        selected_item_iid = self.tasks_list_treeview.focus()
        if not selected_item_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma tarefa para deletar.", parent=self)
            return
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        if messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja apagar esta tarefa?", icon='warning', parent=self):
            task_id_to_delete = int(selected_item_iid)
            if crm_repo.delete_task(task_id_to_delete):
                messagebox.showinfo("Sucesso", "Tarefa deletada com sucesso.", parent=self)
                self._populate_tasks_tree_ui() 
                if self.current_selected_task_id == task_id_to_delete: self._clear_task_form_for_new()
            else:
                messagebox.showerror("Erro", "Falha ao deletar a tarefa do banco de dados.", parent=self)