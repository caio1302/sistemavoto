import customtkinter as ctk
from tkinter import messagebox, ttk
from PIL import Image
import tkinter as tk
import os
import logging
import math
import threading

import config
from dto.pessoa import Pessoa
from dto.organizacao import Organizacao
from modules.new_list_window import NewListWindow
from functions import data_helpers
# --- ALTERAÇÃO: Remove a importação da classe que não existe mais ---
from modules.custom_widgets import CTkScrollableComboBox
from modules.organization_form_window import OrganizationFormWindow

class ContactsView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        
        self.person_current_page = 1
        self.person_total_pages = 0
        self.person_items_per_page = 50
        self.person_last_sort_column = "ID" 
        self.person_last_sort_reverse = True 

        self.org_current_page = 1
        self.org_total_pages = 0
        self.org_items_per_page = 50
        self.org_last_sort_column = "ID"
        self.org_last_sort_reverse = False

        self.selected_contact_id = None
        self.selected_org_id = None
        self.active_list_button = None
        self.current_view_mode = 'Pessoas'
        self._data_fetch_lock = threading.Lock()
        self._search_job_id = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=450)
        self.grid_rowconfigure(0, weight=1)
        
        self._load_icons()
        self._create_widgets()
        self.refresh_lists_panel()

    def _load_icons(self):
        try:
            self.icon_placeholder = ctk.CTkImage(Image.open(config.PLACEHOLDER_PHOTO_PATH), size=(120, 150))
        except Exception as e:
            logging.warning(f"Erro ao carregar ícone placeholder: {e}")
            self.icon_placeholder = None

    def _create_widgets(self):
        self.left_panel = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.left_panel.grid_propagate(False)        
        ctk.CTkLabel(self.left_panel, text="Listas de Contatos", font=ctk.CTkFont(weight="bold")).pack(pady=10, padx=10)
        self.lists_scrollable_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="")
        self.lists_scrollable_frame.pack(fill="both", expand=True, padx=5)
        new_list_buttons_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        new_list_buttons_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(new_list_buttons_frame, text="Nova Lista", command=self.open_new_list_form).pack(fill="x")
        
        self.content_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.content_panel.grid(row=0, column=1, sticky="nsew")
        self.content_panel.grid_rowconfigure(0, weight=1)
        self.content_panel.grid_columnconfigure(0, weight=1)
        self._create_person_panel()
        self._create_org_panel()

        self.right_panel = ctk.CTkFrame(self, corner_radius=0, width=450)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        self.right_panel.grid_propagate(False)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self._create_right_panel_widgets()
        self._clear_right_panel()

    def _create_person_panel(self):
        self.person_panel = ctk.CTkFrame(self.content_panel, corner_radius=0, fg_color="transparent")
        self.person_panel.grid_rowconfigure(2, weight=1) 
        self.person_panel.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.person_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header.grid_columnconfigure(0, weight=1)
        self.person_title_label = ctk.CTkLabel(header, text="Pessoas", font=ctk.CTkFont(size=16, weight="bold"))
        self.person_title_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="Nova Pessoa", command=lambda: self.app.dispatch("open_form", form_name="person", parent_view=self)).grid(row=0, column=1, sticky="e")
        filters = ctk.CTkFrame(self.person_panel, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))
        filters.grid_columnconfigure(0, weight=1)
        self.person_search_entry = ctk.CTkEntry(filters, placeholder_text="Buscar por nome ou apelido...")
        self.person_search_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.person_search_entry.bind("<KeyRelease>", self._on_search_key_release)
        misc_repo = self.repos.get("misc")
        cidades = ["TODAS"] + (misc_repo.get_city_list_from_db() if misc_repo else [])
        self.cidade_selector = CTkScrollableComboBox(filters, values=cidades, command=self._on_filter_changed)
        self.cidade_selector.set("TODAS")
        self.cidade_selector.grid(row=0, column=2, padx=(0,10))
        self.only_candidates_var = ctk.BooleanVar(value=False) 
        self.only_candidates_checkbox = ctk.CTkCheckBox(filters, text="Apenas Candidatos", variable=self.only_candidates_var, command=self._on_filter_changed)
        self.only_candidates_checkbox.grid(row=0, column=3, padx=(0,10))
        tree_frame = ctk.CTkFrame(self.person_panel)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        self._style_treeview()
        cols = ("ID", "Nome", "Apelido", "Data de Nascimento", "Celular", "Email", "Cidade") 
        self.person_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Custom.Treeview")
        col_configs = {"ID": {'width': 50, 'anchor': 'center'}, "Nome": {'width': 250}, "Apelido": {'width': 150}, "Data de Nascimento": {'width': 120, 'anchor': 'center'}, "Celular": {'width': 120}, "Email": {'width': 220}, "Cidade": {'width': 150}}
        for col, config in col_configs.items():
            self.person_tree.heading(col, text=col, command=lambda _col=col: self._sort_treeview_column('Pessoas', _col))
            self.person_tree.column(col, width=config.get('width', 150), anchor=config.get('anchor', 'w'))
        self.person_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.person_tree.bind("<Double-1>", self.on_tree_double_click)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.person_tree.yview, style="Vertical.TScrollbar")
        self.person_tree.configure(yscrollcommand=scrollbar.set)
        self.person_tree.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns")
        self.person_pagination_frame = self._create_pagination_controls(self.person_panel, 'Pessoas')
        self.person_pagination_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
    def _create_org_panel(self):
        self.org_panel = ctk.CTkFrame(self.content_panel, corner_radius=0, fg_color="transparent")
        self.org_panel.grid_rowconfigure(2, weight=1); self.org_panel.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.org_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header.grid_columnconfigure(0, weight=1)
        self.org_title_label = ctk.CTkLabel(header, text="Organizações", font=ctk.CTkFont(size=16, weight="bold"))
        self.org_title_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="Nova Organização", command=lambda: self.open_organization_form(None)).grid(row=0, column=1, sticky="e")
        filters = ctk.CTkFrame(self.org_panel, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))
        filters.grid_columnconfigure(0, weight=1)
        self.org_search_entry = ctk.CTkEntry(filters, placeholder_text="Buscar por nome fantasia ou razão social...")
        self.org_search_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.org_search_entry.bind("<KeyRelease>", self._on_search_key_release)
        tree_frame = ctk.CTkFrame(self.org_panel); tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        cols = ("ID", "Nome Fantasia", "CNPJ", "Telefone", "Cidade")
        self.org_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Custom.Treeview")
        col_configs_org = {"ID": {'width': 50, 'anchor':'center'}, "Nome Fantasia": {'width': 350}, "CNPJ": {'width': 160, 'anchor': 'center'}, "Telefone": {'width': 150}, "Cidade": {'width': 200}}
        for col, config in col_configs_org.items():
            self.org_tree.heading(col, text=col, command=lambda _col=col: self._sort_treeview_column('Organizacoes', _col))
            self.org_tree.column(col, width=config.get('width', 150), anchor=config.get('anchor', 'w'))
        self.org_tree.bind("<<TreeviewSelect>>", self.on_tree_select); self.org_tree.bind("<Double-1>", self.on_tree_double_click)
        scrollbar_org = ttk.Scrollbar(tree_frame, orient="vertical", command=self.org_tree.yview, style="Vertical.TScrollbar")
        self.org_tree.configure(yscrollcommand=scrollbar_org.set); self.org_tree.grid(row=0, column=0, sticky="nsew"); scrollbar_org.grid(row=0, column=1, sticky="ns")
        self.org_pagination_frame = self._create_pagination_controls(self.org_panel, 'Organizacoes')
        self.org_pagination_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
    
    def _create_right_panel_widgets(self):
        header_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(0, weight=1)
        self.details_title = ctk.CTkLabel(header_frame, text="Detalhes", font=ctk.CTkFont(size=14, weight="bold"))
        self.details_title.grid(row=0, column=0, sticky="w")
        
        button_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")
        
        self.edit_button = ctk.CTkButton(button_frame, text="Editar", width=70, command=self.edit_selected, state="disabled")
        self.edit_button.pack(side="left", padx=(0, 5))
        self.delete_button = ctk.CTkButton(button_frame, text="Apagar", width=70, fg_color="#D32F2F", hover_color="#B71C1C", command=self.delete_selected, state="disabled")
        self.delete_button.pack(side="left")

        self.details_scrollframe = ctk.CTkScrollableFrame(self.right_panel, label_text="")
        self.details_scrollframe.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.details_scrollframe.grid_columnconfigure(0, weight=1)

    def _render_separator(self, parent):
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=5, pady=10)

    def _get_photo_from_path(self, pessoa: Pessoa) -> ctk.CTkImage:
        photo_path = data_helpers.get_candidate_photo_path(pessoa, self.repos)
        try:
            return ctk.CTkImage(Image.open(photo_path), size=(120, 150))
        except:
            return self.icon_placeholder

    def _render_person_basic_info(self, parent, details_dto: Pessoa):
        photo = self._get_photo_from_path(details_dto)
        ctk.CTkLabel(parent, text="", image=photo).pack(pady=(5,10))
        self._render_separator(parent)
        if details_dto.nome: ctk.CTkLabel(parent, text=details_dto.nome.title(), font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10)
        if details_dto.apelido: ctk.CTkLabel(parent, text=f'"{details_dto.apelido.title()}"', text_color="gray").pack(anchor="w", padx=10)
        if details_dto.idade is not None: ctk.CTkLabel(parent, text=f"{details_dto.idade} anos").pack(anchor="w", padx=10, pady=(5,0))
        if details_dto.celular: ctk.CTkLabel(parent, text=f"Cel: {details_dto.celular}").pack(anchor="w", padx=10, pady=(5,0))
        if details_dto.email: ctk.CTkLabel(parent, text=f"Email: {details_dto.email}").pack(anchor="w", padx=10)
        
    def _render_person_address(self, parent, details_dto: Pessoa):
        if not (details_dto.endereco or details_dto.cidade): return
        self._render_separator(parent)
        ctk.CTkLabel(parent, text="Endereço", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
        addr = f"{details_dto.endereco or 'Endereço não informado'}, {details_dto.numero or 'S/N'}"
        city_state = f"{details_dto.cidade or ''} - {details_dto.uf or ''}"
        ctk.CTkLabel(parent, text=addr).pack(anchor="w", padx=10)
        ctk.CTkLabel(parent, text=city_state).pack(anchor="w", padx=10)
        
    def _render_candidaturas(self, parent, pessoa: Pessoa):
        historico = pessoa.historico_candidaturas
        if not historico: return
        self._render_separator(parent)
        ctk.CTkLabel(parent, text="Histórico de Candidaturas", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(0, 5))
        for cand in historico:
            # --- CORREÇÃO AQUI: Trata o valor de 'votos' como 0 se for None antes de formatar ---
            votos_f = f"{(cand.get('votos') or 0):,}".replace(",",".")
            text = f"• {cand['ano_eleicao']} - {cand['cargo']}: {votos_f} votos ({cand['cidade']}) - {cand['situacao']}"
            ctk.CTkLabel(parent, text=text, wraplength=400, justify="left").pack(anchor="w", padx=15, pady=1)

    def _render_atendimentos(self, parent, pessoa: Pessoa):
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        atendimentos = crm_repo.get_atendimentos_for_pessoa(pessoa.id_pessoa)
        if not atendimentos: return
        self._render_separator(parent)    
        ctk.CTkLabel(parent, text="Atendimentos Recentes", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(0, 5))
        for atend in atendimentos[:5]:
            command_func = lambda a_id=atend['id_atendimento']: self.app.dispatch("navigate", module_name="Atendimentos") and self.after(100, lambda a_id=a_id: self.app._current_module_frame.open_atendimento_form(atendimento_id=a_id))
            btn = ctk.CTkButton(parent, text=f"• {atend['titulo']} ({atend['status']})", fg_color="transparent", anchor="w",
                                text_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover=False,
                                command=command_func)
            btn.pack(fill="x", padx=10, pady=0)

    def _populate_right_panel_person(self, details_dto: Pessoa):
        if not self.details_scrollframe.winfo_exists(): return

        for widget in self.details_scrollframe.winfo_children(): widget.destroy()
        
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.details_title.configure(text=details_dto.apelido or details_dto.nome)
        
        self._render_person_basic_info(self.details_scrollframe, details_dto)
        self._render_person_address(self.details_scrollframe, details_dto)
        self._render_candidaturas(self.details_scrollframe, details_dto)
        self._render_atendimentos(self.details_scrollframe, details_dto)

    def _populate_right_panel_org(self, details_dto: Organizacao):
        if not self.details_scrollframe.winfo_exists(): return

        for widget in self.details_scrollframe.winfo_children(): widget.destroy()
        self.edit_button.configure(state="normal"); self.delete_button.configure(state="normal")
        self.details_title.configure(text=details_dto.nome_fantasia)
        
        ctk.CTkLabel(self.details_scrollframe, text=details_dto.nome_fantasia.upper(), font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10,0))
        if details_dto.razao_social: ctk.CTkLabel(self.details_scrollframe, text=details_dto.razao_social, text_color="gray").pack(anchor="w", padx=10)
        
        self._render_separator(self.details_scrollframe)
        ctk.CTkLabel(self.details_scrollframe, text=f"Tipo: {details_dto.tipo_organizacao or 'N/A'}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
        if details_dto.cnpj: ctk.CTkLabel(self.details_scrollframe, text=f"CNPJ: {details_dto.cnpj}").pack(anchor="w", padx=10)
        if details_dto.telefone: ctk.CTkLabel(self.details_scrollframe, text=f"Tel: {details_dto.telefone}").pack(anchor="w", padx=10)
        if details_dto.email: ctk.CTkLabel(self.details_scrollframe, text=f"Email: {details_dto.email}").pack(anchor="w", padx=10)
        if details_dto.website: ctk.CTkLabel(self.details_scrollframe, text=f"Site: {details_dto.website}").pack(anchor="w", padx=10)
        
        addr_text = f"{details_dto.endereco or 'N/A'}, {details_dto.numero or 'S/N'} - {details_dto.cidade or ''}/{details_dto.uf or ''}"
        if details_dto.endereco or details_dto.cidade:
            self._render_separator(self.details_scrollframe)
            ctk.CTkLabel(self.details_scrollframe, text="Endereço", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
            ctk.CTkLabel(self.details_scrollframe, text=addr_text).pack(anchor="w", padx=10)

    def _clear_right_panel(self, clear_selection=True):
        if not self.details_scrollframe.winfo_exists(): return

        if clear_selection:
            self.selected_contact_id = None
            self.selected_org_id = None
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.details_title.configure(text="Detalhes")
        for widget in self.details_scrollframe.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.details_scrollframe, text="Selecione um contato na lista para ver os detalhes.", wraplength=200, text_color="gray").pack(expand=True, padx=20, pady=20)

    def _style_treeview(self):
        style = ttk.Style()
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        header_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"])
        selected_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        theme_to_use = "clam" if "clam" in style.theme_names() else "default"
        style.theme_use(theme_to_use)
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, 
                        fieldbackground=bg_color, borderwidth=0, rowheight=28)
        style.map("Custom.Treeview", background=[('selected', selected_color)])
        style.configure("Custom.Treeview.Heading", background=header_bg, foreground=text_color, 
                        relief="flat", font=ctk.CTkFont(family="Calibri", size=11, weight="bold"))
        style.map("Custom.Treeview.Heading", relief=[('active','flat'), ('pressed','flat')])

    def _apply_appearance_mode(self, color_tuple):
        return color_tuple[1] if ctk.get_appearance_mode() == "Dark" else color_tuple[0]
        
    def _initial_load(self):
        first_person_button = None
        for child in self.lists_scrollable_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                 first_btn_in_frame = next((btn for btn in child.winfo_children() if isinstance(btn, ctk.CTkButton)), None)
                 if first_btn_in_frame:
                     first_person_button = first_btn_in_frame
                     break
        if first_person_button:
            self.on_list_button_click('Pessoas', first_person_button)
        
    def on_list_button_click(self, list_type: str, button: ctk.CTkButton):
        if self.active_list_button and self.active_list_button.winfo_exists():
            self.active_list_button.configure(fg_color="transparent")
        if button and button.winfo_exists():
            button.configure(fg_color=("gray75", "gray25"))
            self.active_list_button = button
        if list_type == 'Pessoas':
            self.org_panel.grid_remove()
            self.person_panel.grid(row=0, column=0, sticky="nsew")
            self.current_view_mode = 'Pessoas'
            self.person_current_page = 1 
            self._trigger_data_fetch()
        elif list_type == 'Organizacoes':
            self.person_panel.grid_remove()
            self.org_panel.grid(row=0, column=0, sticky="nsew")
            self.current_view_mode = 'Organizacoes'
            self.org_current_page = 1
            self._trigger_data_fetch()

    def _on_search_key_release(self, event=None):
        if self._search_job_id: self.after_cancel(self._search_job_id)
        self._search_job_id = self.after(400, self._on_filter_changed)

    def _on_filter_changed(self, event=None):
        if self.current_view_mode == 'Pessoas': self.person_current_page = 1
        else: self.org_current_page = 1
        self._trigger_data_fetch()

    def _trigger_data_fetch(self):
        tree = self.person_tree if self.current_view_mode == 'Pessoas' else self.org_tree
        if not tree.winfo_exists():
            return

        if not self._data_fetch_lock.acquire(blocking=False): return
        
        for item in tree.get_children(): 
            if tree.winfo_exists():
                tree.delete(item)
            else:
                self._data_fetch_lock.release()
                return

        if tree.winfo_exists():
            tree.insert('', 'end', text="Carregando dados, por favor aguarde...")
        
        threading.Thread(target=self._fetch_and_display_data_thread, daemon=True).start()

    def _fetch_and_display_data_thread(self):
        try:
            if self.current_view_mode == 'Pessoas':
                repo = self.repos.get("person")
                if not repo: return
                filters = {'search_term': self.person_search_entry.get().strip(), 'cidade': self.cidade_selector.get(), 'only_candidates': self.only_candidates_var.get()}
                total_items = repo.count_pessoas(**filters)
                paginated_data = repo.get_paginated_pessoas(page=self.person_current_page, items_per_page=self.person_items_per_page, sort_by=self.person_last_sort_column, sort_desc=self.person_last_sort_reverse, **filters)
                self.after(0, self._update_ui_with_person_data, paginated_data, total_items)
            
            elif self.current_view_mode == 'Organizacoes':
                repo = self.repos.get("organization")
                if not repo: return
                search_term = self.org_search_entry.get().strip()
                offset = (self.org_current_page - 1) * self.org_items_per_page
                total_items = repo.count_organizacoes(search_term)
                paginated_data = repo.get_all_organizacoes(search_term=search_term, limit=self.org_items_per_page, offset=offset)
                self.after(0, self._update_ui_with_org_data, paginated_data, total_items)
        finally: self._data_fetch_lock.release()

    def _update_ui_with_person_data(self, data: list[Pessoa], total_items: int):
        tree = self.person_tree
        if not tree.winfo_exists(): return

        for item in tree.get_children(): 
            if tree.winfo_exists():
                tree.delete(item)
            else:
                return

        if data:
            for pessoa in data:
                cidade_display = pessoa.cidade_candidatura_recente or ""
                values = (pessoa.id_pessoa, pessoa.nome, pessoa.apelido or "", pessoa.data_nascimento or "", pessoa.celular or "", pessoa.email or "", cidade_display)
                if tree.winfo_exists():
                    tree.insert("", "end", iid=pessoa.id_pessoa, values=values)
                else: return

        else:
            if tree.winfo_exists():
                tree.insert('', 'end', text="Nenhum contato encontrado para os filtros selecionados.")
            else: return

        self.person_total_pages = math.ceil(total_items / self.person_items_per_page) if self.person_items_per_page > 0 else 0
        if total_items == 0: self.person_current_page = 0
        self._update_pagination_controls('Pessoas')
        self._clear_right_panel()

    def _update_ui_with_org_data(self, data: list[Organizacao], total_items: int):
        tree = self.org_tree
        if not tree.winfo_exists(): return

        for item in tree.get_children(): 
            if tree.winfo_exists():
                tree.delete(item)
            else:
                return

        if data:
            for org in data:
                values = (org.id_organizacao, org.nome_fantasia, org.cnpj or "", org.telefone or "", org.cidade or "")
                if tree.winfo_exists():
                    tree.insert("", "end", iid=org.id_organizacao, values=values)
                else: return

        else:
            if tree.winfo_exists():
                tree.insert('', 'end', text="Nenhuma organização encontrada.")
            else: return

        self.org_total_pages = math.ceil(total_items / self.org_items_per_page) if self.org_items_per_page > 0 else 0
        if total_items == 0: self.org_current_page = 0
        self._update_pagination_controls('Organizacoes')
        self._clear_right_panel()

    def _sort_treeview_column(self, tipo: str, col: str):
        if tipo == 'Pessoas':
            if self.person_last_sort_column == col: self.person_last_sort_reverse = not self.person_last_sort_reverse
            else: self.person_last_sort_column = col; self.person_last_sort_reverse = False
            self.person_current_page = 1
            self._update_treeview_sort_indicator(self.person_tree, col, self.person_last_sort_reverse)
            self._trigger_data_fetch()
        elif tipo == 'Organizacoes':
            if self.org_last_sort_column == col: self.org_last_sort_reverse = not self.org_last_sort_reverse
            else: self.org_last_sort_column = col; self.org_last_sort_reverse = False
            self.org_current_page = 1
            self._update_treeview_sort_indicator(self.org_tree, col, self.org_last_sort_reverse)
            self._trigger_data_fetch()

    def on_data_updated(self):
        self.refresh_lists_panel()
        
    def _change_page(self, tipo: str, direction: str):
        prefix = 'person' if tipo == 'Pessoas' else 'org'
        page_attr = f"{prefix}_current_page"
        total_pages_attr = f"{prefix}_total_pages"
        current_page = getattr(self, page_attr)
        total_pages = getattr(self, total_pages_attr)
        new_page = current_page
        if direction == 'next' and current_page < total_pages: new_page += 1
        elif direction == 'prev' and current_page > 1: new_page -= 1
        elif direction == 'first' and current_page > 1: new_page = 1
        elif direction == 'last' and total_pages > 0 and current_page != total_pages: new_page = total_pages
        if new_page != current_page:
            setattr(self, page_attr, new_page)
            self._trigger_data_fetch()

    def _create_pagination_controls(self, parent, tipo):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="pag")
        btn_first = ctk.CTkButton(frame, text="<<", width=50, command=lambda t=tipo: self._change_page(t, 'first'))
        btn_prev = ctk.CTkButton(frame, text="<", width=50, command=lambda t=tipo: self._change_page(t, 'prev'))
        label = ctk.CTkLabel(frame, text=f"Página 0 de 0")
        btn_next = ctk.CTkButton(frame, text=">", width=50, command=lambda t=tipo: self._change_page(t, 'next'))
        btn_last = ctk.CTkButton(frame, text=">>", width=50, command=lambda t=tipo: self._change_page(t, 'last'))
        btn_first.grid(row=0, column=0); btn_prev.grid(row=0, column=1); label.grid(row=0, column=2)
        btn_next.grid(row=0, column=3); btn_last.grid(row=0, column=4)
        widgets_attr = ('person_pagination_widgets' if tipo == 'Pessoas' else 'org_pagination_widgets')
        setattr(self, widgets_attr, (btn_first, btn_prev, label, btn_next, btn_last))
        return frame

    def _update_pagination_controls(self, tipo: str):
        prefix = 'person' if tipo == 'Pessoas' else 'org'
        page_attr = f"{prefix}_current_page"
        total_pages_attr = f"{prefix}_total_pages"
        widgets_attr = f"{prefix}_pagination_widgets"
        current_page = getattr(self, page_attr)
        total_pages = getattr(self, total_pages_attr)
        widgets = getattr(self, widgets_attr, None)
        if widgets:
            btn_first, btn_prev, label, btn_next, btn_last = widgets
            label.configure(text=f"Página {current_page} de {total_pages}")
            btn_first.configure(state="normal" if current_page > 1 else "disabled")
            btn_prev.configure(state="normal" if current_page > 1 else "disabled")
            btn_next.configure(state="normal" if current_page < total_pages else "disabled")
            btn_last.configure(state="normal" if current_page < total_pages else "disabled")

    def _update_treeview_sort_indicator(self, tree, col_name, reverse):
        sort_arrow = '▾' if not reverse else '▴'
        for col in tree["columns"]:
            tree.heading(col, text=col)
        tree.heading(col_name, text=f"{col_name} {sort_arrow}")

    def on_tree_select(self, event):
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            self._clear_right_panel()
            return
            
        selected_id_str = selected_items[0]
        
        if not selected_id_str.isdigit():
            self._clear_right_panel()
            return
        
        # --- LÓGICA DE ATUALIZAÇÃO ASSÍNCRONA ---
        # 1. Limpa o painel imediatamente e mostra "Carregando..." para dar feedback instantâneo.
        self._clear_right_panel(clear_selection=False)
        self.details_title.configure(text="Carregando detalhes...")
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")

        # 2. Define uma função alvo para ser executada em uma thread separada.
        def fetch_details_thread():
            details = None
            if tree == self.person_tree:
                self.selected_contact_id = int(selected_id_str)
                self.selected_org_id = None
                person_repo = self.repos.get("person")
                if person_repo:
                    details = person_repo.get_person_details(self.selected_contact_id)
            elif tree == self.org_tree:
                self.selected_org_id = int(selected_id_str)
                self.selected_contact_id = None
                org_repo = self.repos.get("organization")
                if org_repo:
                    details = org_repo.get_organization_details(self.selected_org_id)
            
            # 3. Agenda a atualização da UI de volta na thread principal.
            # É CRUCIAL usar `self.after` para interagir com widgets Tkinter de uma thread.
            if details:
                if isinstance(details, Pessoa):
                    self.after(0, self._populate_right_panel_person, details)
                elif isinstance(details, Organizacao):
                    self.after(0, self._populate_right_panel_org, details)
            else:
                self.after(0, self._clear_right_panel)

        # 4. Inicia a thread. A função on_tree_select termina aqui, liberando a UI.
        threading.Thread(target=fetch_details_thread, daemon=True).start()

    def on_tree_double_click(self, event):
        self.edit_selected()

    def edit_selected(self):
        if self.current_view_mode == 'Pessoas' and self.selected_contact_id:
            self.app.dispatch("open_form", form_name="person", person_id=self.selected_contact_id)
        elif self.current_view_mode == 'Organizacoes' and self.selected_org_id:
            org_repo = self.repos.get("organization")
            if org_repo:
                dto = org_repo.get_organization_details(self.selected_org_id)
                self.open_organization_form(dto)
                
    def delete_selected(self):
        if self.current_view_mode == 'Pessoas' and self.selected_contact_id:
            person_repo = self.repos.get("person")
            if person_repo and messagebox.askyesno("Confirmar", f"Apagar o contato ID {self.selected_contact_id}?"):
                if person_repo.delete_pessoa(self.selected_contact_id):
                    self._trigger_data_fetch()
                else: messagebox.showerror("Erro", "Não foi possível apagar o contato.")
        elif self.current_view_mode == 'Organizacoes' and self.selected_org_id:
            org_repo = self.repos.get("organization")
            if org_repo and messagebox.askyesno("Confirmar", f"Apagar a organização ID {self.selected_org_id}?"):
                if org_repo.delete_organizacao(self.selected_org_id):
                    self._trigger_data_fetch()
                else: messagebox.showerror("Erro", "Não foi possível apagar a organização.")

    def open_organization_form(self, org_dto=None):
        form = OrganizationFormWindow(self, self.repos, self.app, org_dto)

    def open_new_list_form(self):
        form = NewListWindow(self, self.repos)
        self.wait_window(form)
        self.refresh_lists_panel()

    def delete_list(self, list_id: int, list_name: str):
        misc_repo = self.repos.get("misc")
        if misc_repo and messagebox.askyesno("Confirmar", f"Apagar a lista '{list_name}'?"):
            if misc_repo.delete_lista(list_id):
                self.refresh_lists_panel()
    
    def refresh_lists_panel(self):
        for widget in self.lists_scrollable_frame.winfo_children(): widget.destroy()
        self.active_list_button = None
        
        misc_repo = self.repos.get("misc")
        if not misc_repo: return
        
        all_lists = misc_repo.get_all_lists()
        
        def create_list_group(title, lists_data, list_type):
            ctk.CTkLabel(self.lists_scrollable_frame, text=title, font=ctk.CTkFont(weight="bold", underline=True)).pack(fill="x", pady=(10,2), padx=5)
            frame = ctk.CTkFrame(self.lists_scrollable_frame, fg_color="transparent")
            frame.pack(fill="x", expand=True)
            for item in lists_data:
                btn = ctk.CTkButton(frame, text=item['nome'], anchor="w", fg_color="transparent")
                btn.configure(command=lambda lt=list_type, b=btn: self.on_list_button_click(lt, b))
                btn.pack(fill="x", pady=2, padx=5)
        
        create_list_group("Pessoas", [l for l in all_lists if l['tipo'] == 'Pessoas'], 'Pessoas')
        create_list_group("Organizações", [l for l in all_lists if l['tipo'] == 'Organizacoes'], 'Organizacoes')
        
        self.after(50, self._initial_load)