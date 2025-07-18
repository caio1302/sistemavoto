# --- START OF FILE popups/edit_candidate_window.py ---

import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
from PIL import Image, ImageTk
from pathlib import Path
import os
import shutil

from datetime import datetime
from .datepicker import DatePicker # Importa a nossa classe DatePicker
from functions import formatters   # Importa as nossas funções de formatação
import re                          # Importa a biblioteca de expressões regulares

import config
from functions import ui_helpers, data_helpers
from dto.candidatura import Candidatura
from dto.interaction import Interaction

# Importar as janelas de popup que são abertas a partir desta
from .global_tag_manager_window import GlobalTagManagerWindow
from .task_management_window import TaskManagementWindow


class EditCandidateWindow(tk.Toplevel):
    def __init__(self, parent, loader_instance, candidate_obj: Candidatura):
        super().__init__(parent)
        self.parent_app = parent # Instância de AppConsultaCandidatos
        self.loader = loader_instance
        self.candidate = candidate_obj # Objeto Candidate completo, já deve ter interações e tags

        ano_eleicao_display = f" ({self.candidate.ano_eleicao})" if self.candidate.ano_eleicao and str(self.candidate.ano_eleicao) != "0" else ""
        title_prefix = self.loader.tags.get("edit_candidate_window_title_prefix", "Editar Contato")
        self.title(f"{title_prefix} - {self.candidate.nome_urna}{ano_eleicao_display}")
        
        self.geometry("1100x750") 
        self.resizable(True, True)
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()

        self.form_field_widgets = {} 
        self.is_protected_editing_enabled = False 
        self.protected_field_keys = ['sq_candidato', 'nome_urna', 'nome_completo', 'partido',
                                     'cargo', 'numero', 'uf', 'cidade', 'votos', 'situacao', 'ano_eleicao']
        
        self._tag_checkbox_vars = {} 
        self.images_tk = [] # Para manter referência das imagens da foto

        self._create_widgets()
        self._update_protected_fields_state() 
        ui_helpers.center_window(self)
        self.focus_set() 
        self.bind("<Escape>", lambda e: self.destroy())

    def _get_form_value(self, key):
        val = getattr(self.candidate, key, '') 
        return str(val) if val is not None else ''

    def _create_widgets(self):
        main_frame = tk.Frame(self, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0)) 

        left_panel = tk.Frame(main_frame, bg='white', width=220) 
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False) 

        self.photo_label = tk.Label(left_panel, bg='white', relief="solid", borderwidth=1, width=180, height=225) 
        self.photo_label.pack(pady=(10, 5), padx=5) 
        self._load_and_display_photo()

        ttk.Button(left_panel, text="Atualizar Foto", command=self._update_photo).pack(pady=(0,5), fill=tk.X, padx=5)
        
        self.toggle_edit_button = ttk.Button(left_panel, text="Habilitar Edição Protegida", command=self._toggle_protected_fields_edit)
        self.toggle_edit_button.pack(pady=(10,5), fill=tk.X, padx=5)

        rel_frame = tk.Frame(left_panel, bg='white')
        rel_frame.pack(fill=tk.X, pady=3, padx=5)
        rel_options = ["", "Aliado", "Apoiador Estratégico", "Apoiador Comum", "Neutro", "Oposição Construtiva", "Oposição Declarada", "Contato Inicial", "Sem Relação Definida"]
        self.rel_combobox_var = tk.StringVar()
        rel_combobox = ttk.Combobox(rel_frame, textvariable=self.rel_combobox_var, values=rel_options, font=(config.FONT_FAMILY, 10), state='readonly')
        
        current_rel_value = self._get_form_value("nivel_relacionamento").strip()
        self.placeholder_text_rel = "Nível de Relacionamento..." 

        if not current_rel_value or current_rel_value not in rel_options:
            rel_combobox.set(self.placeholder_text_rel)
            rel_combobox.config(foreground='grey')
        else:
            rel_combobox.set(current_rel_value)

        def on_focus_in_rel_combobox(event):
            if rel_combobox.get() == self.placeholder_text_rel:
                rel_combobox.set(''); rel_combobox.config(foreground='black')
        def on_focus_out_rel_combobox(event):
            if not rel_combobox.get().strip():
                rel_combobox.set(self.placeholder_text_rel); rel_combobox.config(foreground='grey')
        def on_rel_combo_selected(event):
            selected_val = rel_combobox.get()
            self.rel_combobox_var.set("" if selected_val == self.placeholder_text_rel else selected_val)
            rel_combobox.config(foreground='black') 
        
        rel_combobox.bind("<FocusIn>", on_focus_in_rel_combobox)
        rel_combobox.bind("<FocusOut>", on_focus_out_rel_combobox)
        rel_combobox.bind("<<ComboboxSelected>>", on_rel_combo_selected)
        rel_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.form_field_widgets["nivel_relacionamento"] = {'widget': rel_combobox, 'is_protected': False}


        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10, padx=5)
        ttk.Button(left_panel, text="Criar Tarefa para Contato", command=self._create_task_for_contact).pack(pady=5, fill=tk.X, padx=5)

        right_panel = tk.Frame(main_frame, bg='white')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True)

        self._populate_tab_eleicao_pessoal(self._create_tab_frame(notebook, "Dados Eleitorais e Pessoais"))
        self._populate_tab_politica_tags(self._create_tab_frame(notebook, "Informações Políticas e Tags"))
        self._populate_tab_contato_crm(self._create_tab_frame(notebook, "Detalhes de Contato (CRM)"))
        self._populate_tab_interacoes_notas(self._create_tab_frame(notebook, "Histórico de Interações e Notas"))

        footer_frame = tk.Frame(self, bg='white', pady=10) 
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Separator(footer_frame).pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10)) 

        btn_container_frame = tk.Frame(footer_frame, bg='white') 
        btn_container_frame.pack()

        style = ttk.Style() 
        style.configure('Accent.TButton', font=(config.FONT_FAMILY, 10, 'bold')) 

        ttk.Button(btn_container_frame, text="SALVAR DADOS DE CONTATO E FECHAR", command=self._save_and_close, style='Accent.TButton', width=40).pack(side=tk.LEFT, padx=10, ipady=5)
        ttk.Button(btn_container_frame, text="CANCELAR", command=self.destroy, width=15).pack(side=tk.LEFT, padx=10, ipady=5)

    def _toggle_protected_fields_edit(self):
        self.is_protected_editing_enabled = not self.is_protected_editing_enabled
        self._update_protected_fields_state()

    def _update_protected_fields_state(self):
        new_state = 'normal' if self.is_protected_editing_enabled else 'readonly'
        button_text = "Bloquear Edição Protegida" if self.is_protected_editing_enabled else "Habilitar Edição Protegida"
        self.toggle_edit_button.config(text=button_text)

        for key, widget_info in self.form_field_widgets.items():
            widget = widget_info['widget']
            is_protected = widget_info['is_protected']
            
            if is_protected:
                if isinstance(widget, (ttk.Entry, ttk.Combobox)):
                    widget.config(state=new_state)
                    if new_state == 'readonly' and isinstance(widget, ttk.Entry):
                         widget.config(foreground='grey') 
                    elif isinstance(widget, ttk.Entry):
                         widget.config(foreground='black')
                elif isinstance(widget, tk.Text):
                    text_widget_bg = 'white' if new_state == 'normal' else '#F0F0F0'
                    widget.config(state=new_state, background=text_widget_bg)
            elif key == "nivel_relacionamento" and isinstance(widget, ttk.Combobox): # Combo de relacionamento é sempre readonly
                widget.config(state='readonly')


    def _create_form_row(self, parent_tab_frame, label_text: str, field_key: str, widget_type='entry', options=None, is_protected_field=False, num_lines=3):
        row_frame = tk.Frame(parent_tab_frame, bg='white')
        row_frame.pack(fill=tk.X, pady=3)
        
        tk.Label(row_frame, text=f"{label_text}:", bg='white', anchor='w', width=26).pack(side=tk.LEFT, padx=(0, 5)) 
        
        current_value = self._get_form_value(field_key)
        widget = None

        if widget_type == 'entry':
            widget = ttk.Entry(row_frame, font=(config.FONT_FAMILY, 10))
            widget.insert(0, current_value)
        elif widget_type == 'combobox':
            widget = ttk.Combobox(row_frame, values=options or [], font=(config.FONT_FAMILY, 10))
            if current_value in (options or []): widget.set(current_value)
            else: widget.set('') 
        elif widget_type == 'text':
            text_container_frame = tk.Frame(row_frame, bd=1, relief='sunken')
            text_container_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            widget = tk.Text(text_container_frame, height=num_lines, width=40, font=(config.FONT_FAMILY, 10), wrap="word", relief='flat', undo=True)
            scrollbar = ttk.Scrollbar(text_container_frame, orient="vertical", command=widget.yview)
            widget.config(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            widget.insert('1.0', current_value)

        if widget:
            if widget_type != 'text': 
                 widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.form_field_widgets[field_key] = {'widget': widget, 'is_protected': is_protected_field}

    def _create_tab_frame(self, notebook_widget, tab_text: str) -> tk.Frame:
        tab_content_frame = tk.Frame(notebook_widget, bg='white', padx=20, pady=20)
        notebook_widget.add(tab_content_frame, text=tab_text)
        return tab_content_frame

    def _populate_tab_eleicao_pessoal(self, tab_frame):
        self._create_form_row(tab_frame, "ID Interno (SQ_Candidato)", "sq_candidato", is_protected_field=True)
        self._create_form_row(tab_frame, "Nome na Urna (Conforme Eleição)", "nome_urna", is_protected_field=True)
        self._create_form_row(tab_frame, "Nome Completo (Conforme Eleição)", "nome_completo", is_protected_field=True)
        self._create_form_row(tab_frame, "Partido (Conforme Eleição)", "partido", is_protected_field=True)
        self._create_form_row(tab_frame, "Cargo (Conforme Eleição)", "cargo", is_protected_field=True)
        self._create_form_row(tab_frame, "Número de Campanha", "numero", is_protected_field=True)
        self._create_form_row(tab_frame, "Votos Recebidos", "votos", is_protected_field=True)
        self._create_form_row(tab_frame, "Cidade da Candidatura", "cidade", is_protected_field=True)
        self._create_form_row(tab_frame, "UF da Candidatura", "uf", is_protected_field=True)
        if 'ano_eleicao' not in self.form_field_widgets : 
             self.form_field_widgets['ano_eleicao'] = {'widget': None, 'is_protected': True}
        self._create_form_row(tab_frame, "Situação da Candidatura", "situacao", is_protected_field=True)
        
        ttk.Separator(tab_frame, orient='horizontal').pack(fill='x', pady=10)

        # --- MODIFICAÇÃO AQUI ---
        self._create_form_row(tab_frame, "Data de Nascimento", "data_nascimento")
        data_nasc_widget = self.form_field_widgets["data_nascimento"]["widget"]
        data_nasc_widget.config(state="readonly")
        data_nasc_widget.bind("<Button-1>", lambda event, w=data_nasc_widget: DatePicker(self, w))
        # --- FIM DA MODIFICAÇÃO --     
        
        # self._create_form_row(tab_frame, "Data de Nascimento", "data_nascimento")
        self._create_form_row(tab_frame, "Endereço Pessoal Completo", "endereco")
        self._create_form_row(tab_frame, "CEP", "cep")

    def _populate_tab_politica_tags(self, tab_frame):
        self._create_form_row(tab_frame, "Responsável (Equipe Interna)", "responsavel_equipe")
        self._create_form_row(tab_frame, "Origem Principal do Contato", "origem_contato")
        self._create_form_row(tab_frame, "Áreas de Interesse Político/Social", "areas_interesse", widget_type='text', num_lines=4)
        self._create_form_row(tab_frame, "Breve Perfil e Histórico Político", "perfil_historico", widget_type='text', num_lines=5)
        
        ttk.Separator(tab_frame, orient='horizontal').pack(fill='x', pady=10)
        
        tags_section_frame = ttk.LabelFrame(tab_frame, text="Tags de Relacionamento (CRM)", style="TLabelframe")
        tags_section_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tags_canvas_container = ttk.Frame(tags_section_frame) 
        tags_canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tags_canvas = tk.Canvas(tags_canvas_container, bg='white', height=120, highlightthickness=0) 
        tags_scrollbar = ttk.Scrollbar(tags_canvas_container, orient="vertical", command=tags_canvas.yview)
        tags_canvas.config(yscrollcommand=tags_scrollbar.set)
        
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tags_checkboxes_inner_frame = ttk.Frame(tags_canvas, style="TFrame")
        tags_canvas.create_window((0, 0), window=self.tags_checkboxes_inner_frame, anchor="nw")
        
        def on_tags_frame_configure(event): 
            tags_canvas.configure(scrollregion=tags_canvas.bbox("all"))
        self.tags_checkboxes_inner_frame.bind("<Configure>", on_tags_frame_configure)

        self._populate_tags_checkboxes_ui() 

        tag_buttons_frame = ttk.Frame(tags_section_frame, style="TFrame")
        tag_buttons_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(tag_buttons_frame, text="Gerenciar Tags Globais de CRM...", command=self._open_global_tag_manager_popup).pack(side=tk.LEFT)


    def _populate_tab_contato_crm(self, tab_frame):
        # Validador para permitir apenas números
        vcmd = (self.register(formatters.validate_numeric_input), '%P')

        # Funções de bind para aplicar e remover formatação
        def apply_format(widget, formatter_func):
            current_val = widget.get()
            formatted_val = formatter_func(current_val)
            # Evita loops infinitos de re-formatação
            if current_val != formatted_val:
                widget.delete(0, tk.END)
                widget.insert(0, formatted_val)

        def remove_format(widget):
            unformatted_val = re.sub(r'\D', '', widget.get())
            widget.delete(0, tk.END)
            widget.insert(0, unformatted_val)

        # Validação de E-mail
        def validate_and_style_email(widget):
            email = widget.get()
            if formatters.validate_email(email):
                widget.config(foreground='black')
            else:
                widget.config(foreground='red')

        # --- Campos de E-mail com Validação ---
        self._create_form_row(tab_frame, "E-mail Principal", "email_principal")
        email1_widget = self.form_field_widgets["email_principal"]["widget"]
        email1_widget.bind("<FocusOut>", lambda e, w=email1_widget: validate_and_style_email(w))

        self._create_form_row(tab_frame, "E-mail Secundário (Opcional)", "email_secundario")
        email2_widget = self.form_field_widgets["email_secundario"]["widget"]
        email2_widget.bind("<FocusOut>", lambda e, w=email2_widget: validate_and_style_email(w))
        
        # --- Campos de Telefone com Máscara ---
        self._create_form_row(tab_frame, "Celular Principal", "celular")
        celular_widget = self.form_field_widgets["celular"]["widget"]
        celular_widget.config(validate='key', validatecommand=vcmd)
        celular_widget.bind("<FocusOut>", lambda e, w=celular_widget: apply_format(w, formatters.format_celular))
        celular_widget.bind("<FocusIn>", lambda e, w=celular_widget: remove_format(w))

        self._create_form_row(tab_frame, "Telefone Fixo", "telefone_fixo")
        telefone_widget = self.form_field_widgets["telefone_fixo"]["widget"]
        telefone_widget.config(validate='key', validatecommand=vcmd)
        telefone_widget.bind("<FocusOut>", lambda e, w=telefone_widget: apply_format(w, formatters.format_telefone))
        telefone_widget.bind("<FocusIn>", lambda e, w=telefone_widget: remove_format(w))

        ttk.Separator(tab_frame, orient='horizontal').pack(fill='x', pady=10)
        
        self._create_form_row(tab_frame, "Nome do Assessor", "assessor_principal")
        
        self._create_form_row(tab_frame, "Telefone do Assessor", "telefone_assessor")
        assessor_tel_widget = self.form_field_widgets["telefone_assessor"]["widget"]
        assessor_tel_widget.config(validate='key', validatecommand=vcmd)
        assessor_tel_widget.bind("<FocusOut>", lambda e, w=assessor_tel_widget: apply_format(w, formatters.format_celular))
        assessor_tel_widget.bind("<FocusIn>", lambda e, w=assessor_tel_widget: remove_format(w))

        ttk.Separator(tab_frame, orient='horizontal').pack(fill='x', pady=10)
        self._create_form_row(tab_frame, "Instagram", "instagram")
        self._create_form_row(tab_frame, "Facebook", "facebook")
        self._create_form_row(tab_frame, "X / Twitter", "x_twitter")
        self._create_form_row(tab_frame, "Website", "website")

    def _populate_tab_interacoes_notas(self, tab_frame):
        main_paned_window = tk.PanedWindow(tab_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg='white', sashwidth=6) # Aumentei sashwidth
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        top_pane_outer_frame = ttk.Frame(main_paned_window, style="TFrame")
        
        hist_frame = ttk.LabelFrame(top_pane_outer_frame, text="Histórico de Interações com o Contato", style="TLabelframe")
        hist_frame.pack(fill=tk.X, expand=False, pady=(0, 10), padx=5) 
        
        cols_interactions = ('Data', 'Tipo', 'Responsável', 'Descrição')
        self.interactions_tree = ttk.Treeview(hist_frame, columns=cols_interactions, show='headings', selectmode='browse', height=5) # Altura reduzida
        vsb_interactions = ttk.Scrollbar(hist_frame, orient="vertical", command=self.interactions_tree.yview)
        self.interactions_tree.configure(yscrollcommand=vsb_interactions.set)
        
        self.interactions_tree.heading('Data', text='Data'); self.interactions_tree.column('Data', width=120, minwidth=100, anchor='w', stretch=tk.NO)
        self.interactions_tree.heading('Tipo', text='Tipo'); self.interactions_tree.column('Tipo', width=120, minwidth=100, anchor='w', stretch=tk.NO)
        self.interactions_tree.heading('Responsável', text='Responsável'); self.interactions_tree.column('Responsável', width=130, minwidth=100, anchor='w', stretch=tk.NO)
        self.interactions_tree.heading('Descrição', text='Descrição'); self.interactions_tree.column('Descrição', width=400, minwidth=200, anchor='w', stretch=tk.YES) 
        
        vsb_interactions.pack(side=tk.RIGHT, fill=tk.Y, pady=(5,0), padx=(0,5)) 
        self.interactions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5,0), padx=5) 
        
        del_interaction_button = ttk.Button(hist_frame, text="Apagar Interação Selecionada", command=self._delete_selected_interaction)
        del_interaction_button.pack(pady=(5,10)) 
        
        self._populate_interactions_tree_ui() 

        obs_frame = ttk.Frame(top_pane_outer_frame, style="TFrame")
        obs_frame.pack(fill=tk.X, expand=False, pady=(5,0), padx=5)
        self._create_form_row(obs_frame, "Observações Gerais do Contato", "observacoes_gerais", widget_type='text', num_lines=3)

        main_paned_window.add(top_pane_outer_frame, minsize=250) # Aumentei minsize do painel superior

        bottom_pane_outer_frame = ttk.Frame(main_paned_window, style="TFrame") 
        
        add_interaction_frame = ttk.LabelFrame(bottom_pane_outer_frame, text="Registrar Nova Interação", style="TLabelframe")
        add_interaction_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(10,0)) 
        
        new_interaction_form_frame = ttk.Frame(add_interaction_frame, style="TFrame")
        new_interaction_form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # --- CAMPO DE NOVA INTERAÇÃO COM DATEPICKER ---
        row1_new_inter = ttk.Frame(new_interaction_form_frame, style="TFrame")
        row1_new_inter.pack(fill=tk.X, pady=2)
        ttk.Label(row1_new_inter, text="Data (DD/MM/AAAA HH:MM):", background='white').pack(side=tk.LEFT, padx=(0,5))
        self.new_interaction_data_entry = ttk.Entry(row1_new_inter, width=17)
        self.new_interaction_data_entry.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.new_interaction_data_entry.pack(side=tk.LEFT, padx=(0, 15))
        # Nota: Deixado como texto para permitir a entrada de Hora/Minuto.
        # Se você quiser um DatePicker aqui, precisaremos de um widget separado para a hora.
        
        ttk.Label(row1_new_inter, text="Tipo:", background='white').pack(side=tk.LEFT, padx=(0,5))
        interaction_types = ['Ligação Telefônica', 'Reunião Presencial', 'Mensagem (WhatsApp)', 'E-mail', 'Evento Público', 'Visita', 'Outro']
        self.new_interaction_tipo_combo = ttk.Combobox(row1_new_inter, values=interaction_types, width=22, state='readonly')
        self.new_interaction_tipo_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(row1_new_inter, text="Responsável (Equipe):", background='white').pack(side=tk.LEFT, padx=(0,5))
        self.new_interaction_resp_entry = ttk.Entry(row1_new_inter, width=20)
        self.new_interaction_resp_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        row2_new_inter = ttk.Frame(new_interaction_form_frame, style="TFrame")
        row2_new_inter.pack(fill=tk.BOTH, expand=True, pady=2)
        ttk.Label(row2_new_inter, text="Descrição Detalhada da Interação:", background='white').pack(anchor='nw')
        self.new_interaction_desc_text = tk.Text(row2_new_inter, height=3, font=(config.FONT_FAMILY, 10), wrap="word", relief='solid', borderwidth=1, undo=True)
        self.new_interaction_desc_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(add_interaction_frame, text="Salvar Nova Interação", command=self._save_new_interaction_from_ui).pack(pady=10)
        
        main_paned_window.add(bottom_pane_outer_frame, minsize=180) # Aumentei minsize do painel inferior

        self.after(150, lambda: main_paned_window.sash_place(0, 0, main_paned_window.winfo_height() // 2 + 40)) # Ajustar sash place
    
        
    def _populate_interactions_tree_ui(self):
        for item in self.interactions_tree.get_children(): 
            self.interactions_tree.delete(item)
        
        for inter_obj in self.candidate.interacoes: 
            values = (
                inter_obj.data_interacao, 
                inter_obj.tipo_interacao, 
                inter_obj.responsavel_interacao, 
                inter_obj.descricao
            )
            self.interactions_tree.insert('', 'end', iid=str(inter_obj.id_interacao), values=values) 
            
    def _save_new_interaction_from_ui(self):
        new_inter_obj = Interaction(
            sq_candidato=self.candidate.sq_candidato, 
            data_interacao=self.new_interaction_data_entry.get().strip(),
            tipo_interacao=self.new_interaction_tipo_combo.get().strip(),
            descricao=self.new_interaction_desc_text.get("1.0", "end-1c").strip(), 
            responsavel_interacao=self.new_interaction_resp_entry.get().strip()
        )
        if not new_inter_obj.descricao: 
            messagebox.showwarning("Campo Vazio", "A descrição da interação não pode estar vazia.", parent=self)
            return

        if self.loader.save_interaction(new_inter_obj):
            messagebox.showinfo("Sucesso", "Nova interação salva com sucesso!", parent=self)
            self.new_interaction_desc_text.delete("1.0", "end")
            self.new_interaction_data_entry.delete(0, tk.END)
            self.new_interaction_data_entry.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))
            self.new_interaction_tipo_combo.set('')
            self.new_interaction_resp_entry.delete(0, tk.END)

            self.candidate.interacoes = self.loader.get_interactions_for_candidate(self.candidate.sq_candidato)
            self._populate_interactions_tree_ui()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar a nova interação.", parent=self)
            
    def _delete_selected_interaction(self):
        selected_item_iid = self.interactions_tree.focus() 
        if not selected_item_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma interação para apagar.", parent=self)
            return
        
        if messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja apagar permanentemente esta interação?", icon='warning', parent=self):
            interaction_id_to_delete = int(selected_item_iid) 
            if self.loader.delete_interaction(interaction_id_to_delete):
                messagebox.showinfo("Sucesso", "Interação apagada com sucesso.", parent=self)
                self.candidate.interacoes = [inter for inter in self.candidate.interacoes if inter.id_interacao != interaction_id_to_delete]
                self.interactions_tree.delete(selected_item_iid)
            else:
                messagebox.showerror("Erro", "Não foi possível apagar a interação do banco de dados.", parent=self)

    def _populate_tags_checkboxes_ui(self):
        for widget in self.tags_checkboxes_inner_frame.winfo_children(): 
            widget.destroy()
        self._tag_checkbox_vars.clear() 
        
        all_available_tags = self.loader.get_all_contact_tag_names() 
        candidate_current_tags = set(self.candidate.tags) 
        
        num_cols = 3 
        for i in range(num_cols):
             self.tags_checkboxes_inner_frame.columnconfigure(i, weight=1) 
        
        for idx, tag_name in enumerate(all_available_tags):
            var = tk.BooleanVar(value=(tag_name in candidate_current_tags))
            self._tag_checkbox_vars[tag_name] = var
            cb = ttk.Checkbutton(self.tags_checkboxes_inner_frame, text=tag_name, variable=var, style="TCheckbutton")
            cb.grid(row=idx // num_cols, column=idx % num_cols, sticky="w", padx=5, pady=1)

    def _open_global_tag_manager_popup(self):
        # Usando a referência _open_popup da instância principal da aplicação
        self.parent_app._open_popup(GlobalTagManagerWindow, self.loader, self) 

    def _load_and_display_photo(self):
        self.images_tk.clear() 
        try:
            photo_path_str = data_helpers.get_candidate_photo_path(self.candidate.to_dict())
            img_obj = Image.open(photo_path_str)
            img_obj.thumbnail((180, 225), Image.LANCZOS) 
            photo_tk_obj = ImageTk.PhotoImage(img_obj) 
            self.images_tk.append(photo_tk_obj) 
            self.photo_label.config(image=photo_tk_obj, width=180, height=225) 
        except Exception:
            try:
                img_placeholder = Image.open(config.PLACEHOLDER_PHOTO_PATH)
                img_placeholder.thumbnail((180, 225), Image.LANCZOS)
                photo_tk_obj = ImageTk.PhotoImage(img_placeholder)
                self.images_tk.append(photo_tk_obj)
                self.photo_label.config(image=photo_tk_obj, width=180, height=225)
            except Exception: 
                self.photo_label.config(text="Foto Indisponível", image='', width=20, height=10)


    def _update_photo(self):
        if not self.candidate.sq_candidato:
            messagebox.showerror("Erro", "SQ_CANDIDATO (ID do candidato) não encontrado.", parent=self)
            return

        filepath_selected = filedialog.askopenfilename(
            title="Selecione a nova foto", 
            filetypes=[("Imagens", "*.jpg *.jpeg *.png"), ("Todos os arquivos", "*.*")]
        )
        if not filepath_selected: return 

        try:
            os.makedirs(config.FOTOS_ATUALIZADAS_PATH, exist_ok=True)
            dest_filename = f"{self.candidate.sq_candidato}{Path(filepath_selected).suffix}"
            dest_path_absolute = Path(config.FOTOS_ATUALIZADAS_PATH) / dest_filename
            shutil.copy(filepath_selected, dest_path_absolute) 
            self.candidate.foto_customizada = os.path.relpath(dest_path_absolute, config.BASE_PATH).replace('\\', '/')
            self._load_and_display_photo() 
            messagebox.showinfo("Sucesso", "Foto selecionada. Clique em 'Salvar' para confirmar a alteração no banco de dados.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro ao Salvar Foto", f"Ocorreu um erro ao processar a foto: {e}", parent=self)

    def _create_task_for_contact(self):
        # Usando a referência _open_popup da instância principal da aplicação
        self.parent_app._open_popup(TaskManagementWindow, self.loader, 
                                    sq_candidato_pre_fill=self.candidate.sq_candidato, 
                                    nome_urna_pre_fill=self.candidate.nome_urna)

    def _save_and_close(self):
        for field_key, widget_info_dict in self.form_field_widgets.items():
            if widget_info_dict['widget'] is None and field_key == 'ano_eleicao': # Pula ano_eleicao se não tiver widget
                continue

            widget_obj = widget_info_dict['widget']
            is_field_protected = widget_info_dict['is_protected']

            if hasattr(self.candidate, field_key) and (not is_field_protected or self.is_protected_editing_enabled):
                value_from_ui_str = ""
                if field_key == "nivel_relacionamento": 
                    combo_val_str = self.rel_combobox_var.get().strip()
                    value_from_ui_str = "" if combo_val_str == self.placeholder_text_rel else combo_val_str
                elif isinstance(widget_obj, tk.Text):
                    value_from_ui_str = widget_obj.get("1.0", "end-1c").strip()
                elif isinstance(widget_obj, (ttk.Entry, ttk.Combobox)):
                    value_from_ui_str = widget_obj.get().strip()
                
                setattr(self.candidate, field_key, value_from_ui_str)
        
        # Correção aqui: a função agora é save_candidate_contact_data
        if not self.loader.save_candidate_contact_data(self.candidate):
             messagebox.showerror("Erro", "Não foi possível salvar os dados de contato (informações principais).", parent=self)
             return 

        selected_crm_tag_names_list = [tag_name for tag_name, var_bool in self._tag_checkbox_vars.items() if var_bool.get()]
        if not self.loader.save_tags_for_candidate(self.candidate.sq_candidato, selected_crm_tag_names_list):
             messagebox.showerror("Erro", "Não foi possível salvar as tags de CRM do contato. Os outros dados foram salvos.", parent=self)

        messagebox.showinfo("Sucesso", "Dados de contato e tags de CRM salvos com sucesso!", parent=self)
        self.parent_app.refresh_current_report() 
        self.destroy()

# --- END OF FILE popups/edit_candidate_window.py ---