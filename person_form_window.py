import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import os
import re
import shutil
from pathlib import Path
import logging
import json
import unicodedata
from datetime import datetime

import config
from functions import ui_helpers, formatters, data_helpers
from popups.datepicker import DatePicker
from dto.pessoa import Pessoa
from .organization_search_window import OrganizationSearchWindow
from .add_relation_window import AddRelationWindow
# --- ALTERAÇÃO: Importa a classe correta 'CTkAutocompleteComboBox' ---
from .custom_widgets import CTkScrollableComboBox, CTkAutocompleteComboBox

def normalize_text(text):
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFD', str(text))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()

class PersonFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app_instance, pessoa_dto=None):
        super().__init__(parent)
        self.repos = repos
        self.app = app_instance
        self.pessoa = pessoa_dto or Pessoa()
        self.new_photo_path_temp = None

        self.states_data = []
        self.cities_data = {}
        self.state_list = []
        self._load_location_data()
        self._load_icons()

        self.title("Nova Pessoa" if not self.pessoa.id_pessoa else f"Editar: {self.pessoa.nome}")
        self.geometry("1150x750")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.form_widgets = {}
        self.list_checkbox_vars = {}

        self._create_widgets()
        
        if self.pessoa.id_pessoa:
            self._populate_form_for_edit()
            
        self.after(100, lambda: ui_helpers.center_window(self))
        if 'nome' in self.form_widgets:
            self.form_widgets['nome'].focus_set()

    def _load_icons(self):
        try:
            self.vote_yes_icon = ctk.CTkImage(Image.open(os.path.join(config.BASE_PATH, "assets", "vote_yes.png")), size=(20, 20))
            self.vote_no_icon = ctk.CTkImage(Image.open(os.path.join(config.BASE_PATH, "assets", "vote_no.png")), size=(20, 20))
            self.vote_neutral_icon = ctk.CTkImage(Image.open(os.path.join(config.BASE_PATH, "assets", "vote_neutral.png")), size=(20, 20))
            self.calendar_icon = ctk.CTkImage(Image.open(os.path.join(config.BASE_PATH, "assets", "calendar_icon.png")), size=(16, 16))
        except Exception as e:
            logging.error(f"Erro ao carregar ícones da interface: {e}", exc_info=True)
            self.vote_yes_icon = self.vote_no_icon = self.vote_neutral_icon = self.calendar_icon = None

    def _load_location_data(self):
        try:
            json_path = Path(config.BASE_PATH) / "data" / "estados_cidades.json"
            with open(json_path, 'r', encoding='utf-8') as f:
                location_data = json.load(f)
            self.states_data = location_data.get('estados', [])
            self.cities_data = location_data.get('cidades', {})
            self.state_list = sorted([s['sigla'] for s in self.states_data])
        except Exception as e:
            logging.error(f"Erro ao carregar dados de localização: {e}")
            messagebox.showerror("Erro Crítico", "Não foi possível carregar o arquivo 'data/estados_cidades.json'.")

    def _capitalize_entry_text(self, entry_widget):
        current_text = entry_widget.get()
        new_text = current_text.upper() 
        if current_text != new_text:
            cursor_pos = entry_widget.index(ctk.INSERT)
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, new_text)
            entry_widget.icursor(cursor_pos)
    
    def _apply_realtime_mask(self, entry_widget, formatter_func, event=None):
        current_text = entry_widget.get()
        cursor_pos = entry_widget.index(ctk.INSERT)
        digits_before_cursor = len(re.sub(r'\D', '', current_text[:cursor_pos]))
        unformatted_text = re.sub(r'\D', '', current_text)
        formatted_text = formatter_func(unformatted_text)
        if current_text != formatted_text:
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, formatted_text)
            new_cursor_pos = len(formatted_text)
            digits_counted = 0
            for i, char in enumerate(formatted_text):
                if char.isdigit(): digits_counted += 1
                if digits_counted >= digits_before_cursor:
                    new_cursor_pos = i + 1
                    break
            try: entry_widget.icursor(new_cursor_pos)
            except tk.TclError: pass

    def _format_and_set_widget_value(self, widget, value, formatter_func):
        if value is None: value = ""
        unformatted_value = re.sub(r'\D', '', str(value))
        if not unformatted_value: widget.delete(0, ctk.END); return
        formatted_value = formatter_func(unformatted_value)
        widget.delete(0, ctk.END)
        widget.insert(0, formatted_value)

    def _validate_and_style_email(self, entry_widget):
        email = entry_widget.get().strip()
        if not email: self._reset_entry_style(entry_widget); return
        if formatters.validate_email(email): self._reset_entry_style(entry_widget)
        else: self._set_error_style(entry_widget)
    
    def _validate_and_style_cpf(self, entry_widget):
        cpf = re.sub(r'\D', '', entry_widget.get())
        if not cpf: self._reset_entry_style(entry_widget); return
        if formatters.validate_cpf(cpf): self._reset_entry_style(entry_widget)
        else: self._set_error_style(entry_widget)
            
    def _set_error_style(self, entry_widget):
        if isinstance(entry_widget, ctk.CTkEntry): entry_widget.configure(border_color="red", border_width=2)
    
    def _reset_entry_style(self, entry_widget):
        if isinstance(entry_widget, ctk.CTkEntry): entry_widget.configure(border_color=entry_widget.cget("fg_color"), border_width=1)
    
    def _on_state_select(self, selected_state):
        city_widget = self.form_widgets.get('cidade')
        if not city_widget: return
        city_widget.set("") 
        cities = self.cities_data.get(selected_state, [])
        if cities:
            normalized_cities = sorted([normalize_text(city) for city in cities])
            city_widget.configure(values=normalized_cities, state="normal")
        else:
            city_widget.configure(values=[], state="disabled")
            
    def _on_visibility_toggled(self):
        if self.form_widgets['geo_visivel'].get() == 1: 
            if self.pessoa.id_pessoa and (self.pessoa.latitude is not None and self.pessoa.longitude is not None):
                messagebox.showinfo("Geolocalização Ativa", "Este contato já possui coordenadas de geolocalização. Elas serão salvas ao salvar o contato.", parent=self)
                return
            
            geo_service = self.repos.get("geo")
            if not geo_service:
                messagebox.showerror("Erro", "Serviço de geolocalização não disponível.", parent=self)
                self.form_widgets['geo_visivel'].deselect() 
                return
            
            endereco = self.form_widgets['endereco'].get().strip()
            cidade = self.form_widgets['cidade'].get().strip()
            uf = self.form_widgets['uf'].get().strip()
            
            if not (cidade and uf):
                messagebox.showwarning("Endereço Incompleto", "Para geocodificar, preencha pelo menos a Cidade e o UF.", parent=self)
                self.form_widgets['geo_visivel'].deselect() 
                return
            
            messagebox.showinfo("Geocodificação em Andamento", "Buscando coordenadas para o endereço informado...\nOs campos serão preenchidos se encontrado.", parent=self)
            
            temp_pessoa_for_geocode = Pessoa(
                id_pessoa=self.pessoa.id_pessoa, 
                endereco=endereco,
                numero=self.form_widgets['numero'].get().strip(),
                complemento=self.form_widgets['complemento'].get().strip(),
                bairro=self.form_widgets['bairro'].get().strip(),
                cep=self.form_widgets['cep'].get().strip(),
                cidade=cidade,
                uf=uf
            )
            
            geo_service.geocode_and_save_entity_threaded(
                temp_pessoa_for_geocode,
                ui_callback=self._update_geocode_fields_from_callback 
            )
        else: 
            logging.info("Switch 'Exibir na Geolocalização' desativado. Limpando campos de Lat/Lon.")
            self.form_widgets['latitude'].delete(0, tk.END)
            self.form_widgets['longitude'].delete(0, tk.END)
            self.pessoa.latitude = None
            self.pessoa.longitude = None
            self.form_widgets['latitude'].insert(0, "")
            self.form_widgets['longitude'].insert(0, "")
            
            
    def _update_geocode_fields_from_callback(self, latitude: float | None, longitude: float | None):
        if not self.winfo_exists(): return 
        
        def perform_update():
            self.form_widgets['latitude'].configure(state='normal') 
            self.form_widgets['longitude'].configure(state='normal')
            self.form_widgets['latitude'].delete(0, tk.END)
            self.form_widgets['longitude'].delete(0, tk.END)

            if latitude is not None and longitude is not None:
                self.form_widgets['latitude'].insert(0, f"{latitude:.6f}") 
                self.form_widgets['longitude'].insert(0, f"{longitude:.6f}")
                messagebox.showinfo("Coordenadas Encontradas", "Coordenadas de geolocalização preenchidas na tela. Salve o contato para persistir.", parent=self)
            else:
                self.form_widgets['geo_visivel'].deselect() 
                messagebox.showwarning("Coordenadas Não Encontradas", "Não foi possível localizar as coordenadas para o endereço fornecido.", parent=self)
            
            self.form_widgets['latitude'].configure(state='readonly') 
            self.form_widgets['longitude'].configure(state='readonly')
            
        self.after(0, perform_update)


    def _create_widgets(self):        
        # Left Panel (Foto e botões gerais)
        left_panel = ctk.CTkFrame(self, width=200)
        left_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(10, 5), pady=10)
        left_panel.grid_propagate(False)
        left_panel.grid_columnconfigure(0, weight=1)

        self.photo_label = ctk.CTkLabel(left_panel, text="", width=150, height=180, fg_color="gray80", corner_radius=6)
        self.photo_label.pack(pady=10, padx=10)

        photo_buttons_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        photo_buttons_frame.pack(fill="x", padx=10, pady=(0,5))
        photo_buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(photo_buttons_frame, text="Alterar", command=self._select_photo).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.remove_photo_button = ctk.CTkButton(photo_buttons_frame, text="Remover", command=self._remove_photo, fg_color="#D32F2F", hover_color="#B71C1C")
        self.remove_photo_button.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        ctk.CTkButton(left_panel, text="Registrar Atendimento", command=self._open_new_atendimento).pack(fill="x", padx=10, pady=10)

        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10, padx=10)
        ctk.CTkLabel(left_panel, text="Apoiador:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10)
        
        vote_main_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        vote_main_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.vote_var = ctk.StringVar(value="indeciso")
        
        options = {
            "sim": {"text": "Sim", "icon": self.vote_yes_icon},
            "nao": {"text": "Não", "icon": self.vote_no_icon},
            "indeciso": {"text": "Indeciso", "icon": self.vote_neutral_icon},
        }

        for value, config in options.items():
            option_frame = ctk.CTkFrame(vote_main_frame, fg_color="transparent")
            option_frame.pack(anchor="w", pady=3)
            
            icon_label = ctk.CTkLabel(option_frame, text="", image=config["icon"])
            icon_label.pack(side="left")
            
            radio_btn = ctk.CTkRadioButton(option_frame, text=config["text"], variable=self.vote_var, value=value, border_width_checked=2)
            radio_btn.pack(side="left", padx=(5,0))

        self.form_widgets['voto'] = self.vote_var

        # Right Panel (Dados do formulário)
        right_panel = ctk.CTkFrame(self, fg_color="transparent")
        right_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.grid_rowconfigure(1, weight=1) 
        right_panel.grid_columnconfigure(0, weight=1) 

        # Header de nome/apelido
        header_name_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        header_name_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        header_name_frame.grid_columnconfigure((0, 1), weight=1) 
        
        ctk.CTkLabel(header_name_frame, text="Nome Completo:").grid(row=0, column=0, sticky="sw", padx=(0,5))
        self.form_widgets['nome'] = ctk.CTkEntry(header_name_frame, placeholder_text="Nome completo do contato")
        self.form_widgets['nome'].grid(row=1, column=0, sticky="ew", padx=(0,5))
        self.form_widgets['nome'].bind("<KeyRelease>", lambda e, w=self.form_widgets['nome']: self._capitalize_entry_text(w))
        
        ctk.CTkLabel(header_name_frame, text="Apelido:").grid(row=0, column=1, sticky="sw", padx=(5,0))
        self.form_widgets['apelido'] = ctk.CTkEntry(header_name_frame, placeholder_text="Como a pessoa é conhecida")
        self.form_widgets['apelido'].grid(row=1, column=1, sticky="ew", padx=(5,0))
        self.form_widgets['apelido'].bind("<KeyRelease>", lambda e, w=self.form_widgets['apelido']: self._capitalize_entry_text(w))

        # Tabview
        self.tab_view = ctk.CTkTabview(right_panel)
        self.tab_view.grid(row=1, column=0, sticky="nsew")
        self.tab_view.add("Pessoais"); self.tab_view.add("Contato"); self.tab_view.add("Profissional")
        self.tab_view.add("Listas e Tags"); self.tab_view.add("Candidaturas"); self.tab_view.add("Atendimentos")
        self.tab_view.add("Relacionamentos")
        
        self._create_tab_pessoais(self.tab_view.tab("Pessoais"))
        self._create_tab_contato(self.tab_view.tab("Contato"))
        self._create_tab_profissionais(self.tab_view.tab("Profissional"))
        self._create_tab_listas(self.tab_view.tab("Listas e Tags"))
        self._create_tab_candidaturas(self.tab_view.tab("Candidaturas"))
        self._create_tab_atendimentos(self.tab_view.tab("Atendimentos"))
        self._create_tab_relacionamentos(self.tab_view.tab("Relacionamentos"))

        # Footer (Botões Salvar/Cancelar)
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=1, sticky="e", padx=10, pady=(0,10)) 
        ctk.CTkButton(button_frame, text="Salvar Contato", command=self._save_contact).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")
        
    def _create_tab_pessoais(self, tab):
        tab.columnconfigure((0, 2), weight=0)
        tab.columnconfigure((1, 3), weight=1)
        tab.rowconfigure((0,1), weight=0)
        
        row_counter = 0

        ctk.CTkLabel(tab, text="Data de Nascimento:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        date_frame = ctk.CTkFrame(tab, fg_color="transparent")
        date_frame.grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        date_frame.columnconfigure(0, weight=1)
        self.form_widgets['data_nascimento'] = ctk.CTkEntry(date_frame, placeholder_text="DD/MM/AAAA")
        self.form_widgets['data_nascimento'].grid(row=0, column=0, sticky="ew")
        self.form_widgets['data_nascimento'].bind("<KeyRelease>", lambda e, w=self.form_widgets['data_nascimento']: self._apply_realtime_mask(w, formatters.format_date_input, e))
        ctk.CTkButton(date_frame, text="", image=self.calendar_icon, width=30, height=28, command=lambda w=self.form_widgets['data_nascimento']: DatePicker(self, w)).grid(row=0, column=1, padx=(5,0))
        
        ctk.CTkLabel(tab, text="Gênero:").grid(row=row_counter, column=2, sticky="w", padx=10, pady=10)
        self.form_widgets['genero'] = ctk.CTkSegmentedButton(tab, values=["Masculino", "Feminino"])
        self.form_widgets['genero'].grid(row=row_counter, column=3, sticky="w", padx=10, pady=10)
        row_counter += 1
        
        ctk.CTkLabel(tab, text="CPF:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        self.form_widgets['cpf'] = ctk.CTkEntry(tab, placeholder_text="___.___.___-__")
        self.form_widgets['cpf'].grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        self.form_widgets['cpf'].bind("<KeyRelease>", lambda e, w=self.form_widgets['cpf']: self._apply_realtime_mask(w, formatters.format_cpf, e))
        self.form_widgets['cpf'].bind("<FocusOut>", lambda e, w=self.form_widgets['cpf']: self._validate_and_style_cpf(w))
        
        ctk.CTkLabel(tab, text="RG:").grid(row=row_counter, column=2, sticky="w", padx=10, pady=10)
        self.form_widgets['rg'] = ctk.CTkEntry(tab, placeholder_text="Somente números")
        self.form_widgets['rg'].grid(row=row_counter, column=3, sticky="ew", padx=10, pady=10)
        vcmd_numeric_only = (self.register(lambda P: P.isdigit() or P == ""), '%P')
        self.form_widgets['rg'].configure(validate='key', validatecommand=vcmd_numeric_only)
        row_counter += 1
        
        addr_geo_frame = ctk.CTkFrame(tab, fg_color="transparent")
        addr_geo_frame.grid(row=row_counter, column=0, columnspan=4, sticky="nsew", padx=0, pady=(20,10))
        addr_geo_frame.columnconfigure((0, 2), weight=0)
        addr_geo_frame.columnconfigure((1, 3), weight=1)
        
        addr_row_counter_internal = 0
        ctk.CTkLabel(addr_geo_frame, text="Endereço:", font=ctk.CTkFont(weight="bold")).grid(row=addr_row_counter_internal, column=0, columnspan=4, sticky="w", padx=10, pady=(0,10))
        addr_row_counter_internal += 1
        
        ctk.CTkLabel(addr_geo_frame, text="CEP:").grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['cep'] = ctk.CTkEntry(addr_geo_frame, placeholder_text="_____-___")
        self.form_widgets['cep'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=5)
        self.form_widgets['cep'].bind("<KeyRelease>", lambda e, w=self.form_widgets['cep']: self._apply_realtime_mask(w, formatters.format_cep, e))
        addr_row_counter_internal += 1
        
        ctk.CTkLabel(addr_geo_frame, text="Logradouro:").grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['endereco'] = ctk.CTkEntry(addr_geo_frame)
        self.form_widgets['endereco'].grid(row=addr_row_counter_internal, column=1, columnspan=3, sticky="ew", padx=10, pady=5)
        self.form_widgets['endereco'].bind("<KeyRelease>", lambda e, w=self.form_widgets['endereco']: self._capitalize_entry_text(w))
        addr_row_counter_internal += 1
        
        ctk.CTkLabel(addr_geo_frame, text="Número:").grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['numero'] = ctk.CTkEntry(addr_geo_frame, placeholder_text="Somente números")
        self.form_widgets['numero'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=5)
        self.form_widgets['numero'].configure(validate='key', validatecommand=vcmd_numeric_only)
        
        ctk.CTkLabel(addr_geo_frame, text="Compl.:").grid(row=addr_row_counter_internal, column=2, sticky="w", padx=10, pady=5)
        self.form_widgets['complemento'] = ctk.CTkEntry(addr_geo_frame)
        self.form_widgets['complemento'].grid(row=addr_row_counter_internal, column=3, sticky="ew", padx=10, pady=5)
        self.form_widgets['complemento'].bind("<KeyRelease>", lambda e, w=self.form_widgets['complemento']: self._capitalize_entry_text(w))
        addr_row_counter_internal += 1
        
        ctk.CTkLabel(addr_geo_frame, text="Bairro:").grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['bairro'] = ctk.CTkEntry(addr_geo_frame)
        self.form_widgets['bairro'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=5)
        self.form_widgets['bairro'].bind("<KeyRelease>", lambda e, w=self.form_widgets['bairro']: self._capitalize_entry_text(w))
        addr_row_counter_internal += 1

        ctk.CTkLabel(addr_geo_frame, text="UF:").grid(row=addr_row_counter_internal, column=2, sticky="w", padx=10, pady=5)
        self.form_widgets['uf'] = CTkAutocompleteComboBox(addr_geo_frame, values=self.state_list, command=self._on_state_select)
        self.form_widgets['uf'].grid(row=addr_row_counter_internal, column=3, sticky="ew", padx=10, pady=5) 
        self.form_widgets['uf'].set("")
        
        ctk.CTkLabel(addr_geo_frame, text="Cidade:").grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        self.form_widgets['cidade'] = CTkAutocompleteComboBox(addr_geo_frame, values=[], state="disabled")
        self.form_widgets['cidade'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=5)
        self.form_widgets['cidade'].entry.bind("<KeyRelease>", lambda e, w=self.form_widgets['cidade'].entry: self._capitalize_entry_text(w))
        self.form_widgets['cidade'].set("")
        addr_row_counter_internal += 1

        ctk.CTkLabel(addr_geo_frame, text="Latitude:", font=ctk.CTkFont(weight="bold")).grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=(20, 5))
        self.form_widgets['latitude'] = ctk.CTkEntry(addr_geo_frame, placeholder_text="Coordenada Latitude", state='readonly') 
        self.form_widgets['latitude'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=(20, 5), columnspan=3)
        addr_row_counter_internal += 1 
        
        ctk.CTkLabel(addr_geo_frame, text="Longitude:", font=ctk.CTkFont(weight="bold")).grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['longitude'] = ctk.CTkEntry(addr_geo_frame, placeholder_text="Coordenada Longitude", state='readonly')
        self.form_widgets['longitude'].grid(row=addr_row_counter_internal, column=1, sticky="ew", padx=10, pady=5, columnspan=3)
        addr_row_counter_internal += 1

        ctk.CTkLabel(addr_geo_frame, text="Visibilidade no Mapa:", font=ctk.CTkFont(weight="bold")).grid(row=addr_row_counter_internal, column=0, sticky="w", padx=10, pady=(20, 10))
        self.form_widgets['geo_visivel'] = ctk.CTkSwitch(addr_geo_frame, text="Exibir na Geolocalização", command=self._on_visibility_toggled)
        self.form_widgets['geo_visivel'].grid(row=addr_row_counter_internal, column=1, sticky="w", padx=10, pady=(20, 10))
        
        addr_geo_frame.rowconfigure(addr_row_counter_internal + 1, weight=1)
        tab.rowconfigure(row_counter, weight=1)

    def _create_tab_contato(self, tab):
        tab.columnconfigure((0,2), weight=0)
        tab.columnconfigure((1,3), weight=1)
        
        row_counter = 0

        ctk.CTkLabel(tab, text="E-mail:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        self.form_widgets['email'] = ctk.CTkEntry(tab)
        self.form_widgets['email'].grid(row=row_counter, column=1, columnspan=3, sticky="ew", padx=10, pady=10)
        self.form_widgets['email'].bind("<FocusOut>", lambda e, w=self.form_widgets['email']: self._validate_and_style_email(w))
        row_counter += 1

        ctk.CTkLabel(tab, text="Celular:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        self.form_widgets['celular'] = ctk.CTkEntry(tab, placeholder_text="(__) _ ____-____")
        self.form_widgets['celular'].grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        self.form_widgets['celular'].bind("<KeyRelease>", lambda e, w=self.form_widgets['celular']: self._apply_realtime_mask(w, formatters.format_celular, e))
        
        ctk.CTkLabel(tab, text="Tel. Residencial:").grid(row=row_counter, column=2, sticky="w", padx=10, pady=10)
        self.form_widgets['telefone_residencial'] = ctk.CTkEntry(tab, placeholder_text="(__) ____-____")
        self.form_widgets['telefone_residencial'].grid(row=row_counter, column=3, sticky="ew", padx=10, pady=10)
        self.form_widgets['telefone_residencial'].bind("<KeyRelease>", lambda e, w=self.form_widgets['telefone_residencial']: self._apply_realtime_mask(w, formatters.format_telefone, e))
        row_counter += 1
        
        ttk.Separator(tab).grid(row=row_counter, column=0, columnspan=4, sticky="ew", padx=10, pady=15)
        row_counter += 1
        
        tab.rowconfigure(row_counter, weight=1) 

    def _create_tab_profissionais(self, tab):
        tab.columnconfigure(0, weight=0) 
        tab.columnconfigure(1, weight=1) 
        tab.rowconfigure((0,1,2), weight=0) 
        tab.rowconfigure(3, weight=1) 

        row_counter = 0

        ctk.CTkLabel(tab, text="Tratamento:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        misc_repo = self.repos.get("misc") 
        tratamentos = [""] + ([t['nome'] for t in misc_repo.get_lookup_table_data("tratamentos")] if misc_repo else [])
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        self.form_widgets['id_tratamento'] = CTkAutocompleteComboBox(tab, values=tratamentos)
        self.form_widgets['id_tratamento'].grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        row_counter += 1

        ctk.CTkLabel(tab, text="Profissão:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        profissoes = [""] + ([p['nome'] for p in misc_repo.get_lookup_table_data("profissoes")] if misc_repo else [])
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        self.form_widgets['id_profissao'] = CTkAutocompleteComboBox(tab, values=profissoes)
        self.form_widgets['id_profissao'].grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        row_counter += 1

        ctk.CTkLabel(tab, text="Escolaridade:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=10)
        escolaridades = [""] + ([e['nome'] for e in misc_repo.get_lookup_table_data("escolaridades")] if misc_repo else [])
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        self.form_widgets['id_escolaridade'] = CTkAutocompleteComboBox(tab, values=escolaridades)
        self.form_widgets['id_escolaridade'].grid(row=row_counter, column=1, sticky="ew", padx=10, pady=10)
        row_counter += 1

    def _create_tab_listas(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        lists_frame = ctk.CTkScrollableFrame(tab, label_text="Participação em Listas")
        lists_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        lists_frame.columnconfigure(0, weight=1)
        
        misc_repo = self.repos.get("misc")
        all_lists_data = misc_repo.get_all_lists() if misc_repo else []
        person_lists = [l for l in all_lists_data if l['tipo'] == 'Pessoas' and l['nome'] != "Todas as Pessoas"]
        for list_item in person_lists:
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(lists_frame, text=list_item['nome'], variable=var)
            cb.pack(anchor="w", padx=10, pady=5)
            self.list_checkbox_vars[list_item['id_lista']] = var

    def _create_tab_candidaturas(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        cols = ("Ano", "Cargo", "Cidade", "Votos", "Situação")
        self.candidaturas_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for col in cols: self.candidaturas_tree.heading(col, text=col); self.candidaturas_tree.column(col, anchor="w")
        self.candidaturas_tree.column("Ano", width=80, anchor="center")
        self.candidaturas_tree.column("Votos", width=100, anchor="e")
        self.candidaturas_tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.candidaturas_tree.yview)
        self.candidaturas_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10))

    def _create_tab_atendimentos(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        cols = ("ID", "Data", "Título", "Status")
        self.atendimentos_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for col in cols: self.atendimentos_tree.heading(col, text=col); self.atendimentos_tree.column(col, anchor="w")
        self.atendimentos_tree.column("ID", width=60, anchor="center")
        self.atendimentos_tree.column("Data", width=120, anchor="center")
        self.atendimentos_tree.column("Status", width=120, anchor="w")
        self.atendimentos_tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.atendimentos_tree.bind("<Double-1>", self._on_atendimento_double_click)

        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.atendimentos_tree.yview)
        self.atendimentos_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10))

    def _create_tab_relacionamentos(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(button_frame, text="Adicionar Relação", command=self._open_add_relation_form).pack(side="left")
        ctk.CTkButton(button_frame, text="Remover Selecionada", fg_color="#D32F2F", hover_color="#B71C1C", command=self._delete_selected_relation).pack(side="left", padx=10)
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        cols = ("Tipo de Relação", "Nome")
        self.relacionamentos_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.relacionamentos_tree.heading("Tipo de Relação", text="Tipo de Relação")
        self.relacionamentos_tree.column("Tipo de Relação", width=150, anchor="w")
        self.relacionamentos_tree.heading("Nome", text="Nome")
        self.relacionamentos_tree.column("Nome", width=400, anchor="w")
        self.relacionamentos_tree.bind("<Double-1>", self._on_relation_double_click)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.relacionamentos_tree.yview)
        self.relacionamentos_tree.configure(yscrollcommand=scrollbar.set)
        self.relacionamentos_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
    
    def _populate_form_for_edit(self):
        person_repo = self.repos.get("person")
        if not person_repo: return
        pessoa_completa = person_repo.get_person_details(self.pessoa.id_pessoa)
        if pessoa_completa: self.pessoa = pessoa_completa

        self._load_photo(self.pessoa)
        
        misc_repo = self.repos.get("misc")
        if not misc_repo: return

        tratamento_map = {item['id']: item['nome'] for item in misc_repo.get_lookup_table_data("tratamentos")}
        profissao_map = {item['id']: item['nome'] for item in misc_repo.get_lookup_table_data("profissoes")}
        escolaridade_map = {item['id']: item['nome'] for item in misc_repo.get_lookup_table_data("escolaridades")}

        for field_name, widget in self.form_widgets.items():
            # --- CORREÇÃO AQUI: Remove 'latitude' e 'longitude' da lista de exclusão do loop principal ---
            if field_name in ['uf', 'cidade']: continue
            
            value = getattr(self.pessoa, field_name, None)
            
            if isinstance(widget, ctk.CTkEntry): self._reset_entry_style(widget) 
            
            if isinstance(widget, ctk.CTkSwitch):
                if value == 1: widget.select() 
                else: widget.deselect()
            elif isinstance(widget, ctk.CTkEntry):
                formatters_map = {'data_nascimento': formatters.format_date_input, 'cpf': formatters.format_cpf, 'celular': formatters.format_celular, 'telefone_residencial': formatters.format_telefone, 'cep': formatters.format_cep}
                if field_name in formatters_map: 
                    self._format_and_set_widget_value(widget, value, formatters_map[field_name])
                else: 
                    widget.delete(0, ctk.END)
                    widget.insert(0, str(value) if value is not None else "")
            elif isinstance(widget, tk.StringVar): 
                widget.set(value if value in ['sim', 'nao', 'indeciso'] else 'indeciso')
            elif isinstance(widget, (CTkScrollableComboBox, CTkAutocompleteComboBox)):
                text_to_set = ""
                if value: 
                    if field_name == 'id_tratamento': text_to_set = tratamento_map.get(value)
                    elif field_name == 'id_profissao': text_to_set = profissao_map.get(value)
                    elif field_name == 'id_escolaridade': text_to_set = escolaridade_map.get(value)
                widget.set(text_to_set or "")
            elif isinstance(widget, ctk.CTkSegmentedButton) and field_name == 'genero':
                widget.set(str(value).title() if value else "")

        uf_value = getattr(self.pessoa, 'uf', None)
        if uf_value and uf_value in self.state_list:
            self.form_widgets['uf'].set(uf_value)
            self._on_state_select(uf_value)
            
            cidade_value = getattr(self.pessoa, 'cidade', None)
            if cidade_value:
                self.form_widgets['cidade'].set(normalize_text(cidade_value))
        else: 
            self.form_widgets['uf'].set("")
            self.form_widgets['cidade'].set("")
            self.form_widgets['cidade'].configure(values=[], state="disabled")
            
        # --- CORREÇÃO AQUI: Bloco dedicado para preencher latitude e longitude ---
        lat_widget = self.form_widgets['latitude']
        lon_widget = self.form_widgets['longitude']

        lat_widget.configure(state='normal')
        lon_widget.configure(state='normal')
        lat_widget.delete(0, tk.END)
        lon_widget.delete(0, tk.END)
        
        if self.pessoa.latitude is not None:
            lat_widget.insert(0, str(self.pessoa.latitude))
        if self.pessoa.longitude is not None:
            lon_widget.insert(0, str(self.pessoa.longitude))

        lat_widget.configure(state='readonly')
        lon_widget.configure(state='readonly')
        # --- FIM DA CORREÇÃO ---
        
        list_ids = person_repo.get_list_ids_for_pessoa(self.pessoa.id_pessoa)
        for list_id, var in self.list_checkbox_vars.items():
            if list_id in list_ids: var.set(True)

        self._populate_candidaturas_tree()
        self._populate_atendimentos_tree()
        self._populate_relacionamentos_tree()
        self._update_photo_button_state()
    
    def _populate_candidaturas_tree(self):
        for item in self.candidaturas_tree.get_children(): self.candidaturas_tree.delete(item)
        if hasattr(self.pessoa, 'historico_candidaturas'):
            for cand in self.pessoa.historico_candidaturas:
                # --- CORREÇÃO AQUI: Trata o valor de 'votos' como 0 se for None antes de formatar ---
                votos_formatados = f"{(cand.get('votos') or 0):,}".replace(",", ".")
                values = (cand.get('ano_eleicao'), cand.get('cargo'), cand.get('cidade'), votos_formatados, cand.get('situacao'))
                self.candidaturas_tree.insert("", "end", values=values, iid=cand['id_candidatura'])
            
    def _populate_atendimentos_tree(self):
        for item in self.atendimentos_tree.get_children(): self.atendimentos_tree.delete(item)
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        atendimentos = crm_repo.get_atendimentos_for_pessoa(self.pessoa.id_pessoa)
        for atend in atendimentos:
            data_formatada = ""
            try: data_formatada = datetime.strptime(atend['data_abertura'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            except (ValueError, TypeError): data_formatada = atend.get('data_abertura', '').split(" ")[0]
            values = (atend['id_atendimento'], data_formatada, atend['titulo'], atend['status'])
            self.atendimentos_tree.insert("", "end", values=values, iid=atend['id_atendimento'])
    
    def _populate_relacionamentos_tree(self):
        for item in self.relacionamentos_tree.get_children(): self.relacionamentos_tree.delete(item)
        if hasattr(self.pessoa, 'relacionamentos') and self.pessoa.relacionamentos:
            for rel in self.pessoa.relacionamentos:
                self.relacionamentos_tree.insert("", "end", iid=rel['id_relacionamento'], values=(rel['tipo_relacao'], rel['nome_pessoa_destino']))
    
    def _on_atendimento_double_click(self, event=None):
        selected_item = self.atendimentos_tree.focus()
        if not selected_item: return
        atendimento_id = int(selected_item)
        self.app.dispatch("navigate", module_name="Atendimentos")
        self.after(100, lambda: self.app._current_module_frame.open_atendimento_form(atendimento_id=atendimento_id))
    
    def _on_relation_double_click(self, event=None):
        selected_item_iid = self.relacionamentos_tree.focus()
        if not selected_item_iid: return
        rel_id = int(selected_item_iid)
        target_relation = next((r for r in self.pessoa.relacionamentos if r['id_relacionamento'] == rel_id), None)
        if target_relation and 'id_pessoa_destino' in target_relation:
            self.app.dispatch("open_form", form_name="person", person_id=target_relation['id_pessoa_destino'], parent_view=self.app)
            
    def _open_new_atendimento(self):
        if not self.pessoa.id_pessoa: messagebox.showinfo("Aviso", "Salve o contato primeiro para registrar um atendimento.", parent=self); return
        self.app.dispatch("navigate", module_name="Atendimentos")
        self.after(100, lambda: self.app._current_module_frame.open_atendimento_form(pessoa_pre_selecionada=self.pessoa))

    def _open_add_relation_form(self):
        if not self.pessoa.id_pessoa: messagebox.showinfo("Aviso", "Você precisa salvar o contato principal antes de adicionar relações.", parent=self); return
        add_win = AddRelationWindow(self, self.repos, person_id_origem=self.pessoa.id_pessoa)
        self.wait_window(add_win)
        self.refresh_relationships_list()
        
    def _delete_selected_relation(self):
        selected_item = self.relacionamentos_tree.focus()
        if not selected_item: return
        person_repo = self.repos.get("person")
        if not person_repo: return
        rel_id_to_delete = int(selected_item)
        values = self.relacionamentos_tree.item(selected_item, "values")
        if messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover a relação:\n\n'{values[0]}: {values[1]}'?", parent=self, icon="warning"):
            if person_repo.delete_relacionamento(rel_id_to_delete): self.refresh_relationships_list()
            else: messagebox.showerror("Erro", "Não foi possível remover o relacionamento.", parent=self)
            
    def refresh_relationships_list(self):
        person_repo = self.repos.get("person")
        if not person_repo: return
        updated_pessoa = person_repo.get_person_details(self.pessoa.id_pessoa)
        if updated_pessoa: self.pessoa.relacionamentos = updated_pessoa.relacionamentos
        self._populate_relacionamentos_tree()
        
    def _select_photo(self):
        filepath = filedialog.askopenfilename(title="Selecione a foto", filetypes=[("Imagens", "*.jpg *.jpeg *.png")])
        if filepath:
            self.new_photo_path_temp = filepath
            self._load_photo(filepath)
            self._update_photo_button_state()
            
    def _remove_photo(self):
        if messagebox.askyesno("Remover Foto", "Tem certeza que deseja remover a foto customizada deste contato?\nA foto padrão do TSE será usada.", parent=self):
            self.new_photo_path_temp = "DELETE" 
            self.pessoa.caminho_foto = None
            self._load_photo(self.pessoa)
            self._update_photo_button_state()
            
    def _load_photo(self, pessoa_ou_caminho):
        photo_path = None
        if isinstance(pessoa_ou_caminho, str) and os.path.exists(pessoa_ou_caminho):
            photo_path = pessoa_ou_caminho
        elif isinstance(pessoa_ou_caminho, Pessoa):
            photo_path = data_helpers.get_candidate_photo_path(pessoa_ou_caminho, self.repos)
        path_to_open = photo_path if (photo_path and os.path.exists(photo_path)) else config.PLACEHOLDER_PHOTO_PATH
        try:
            pil_image = Image.open(path_to_open)
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(150, 180))
            self.photo_label.configure(image=ctk_image, text="")
        except Exception as e:
            self.photo_label.configure(image=None, text="Erro Foto")
            logging.warning(f"Erro ao carregar foto do caminho '{path_to_open}': {e}")
            
    def _update_photo_button_state(self):
        can_remove = self.pessoa.caminho_foto and self.new_photo_path_temp != "DELETE"
        self.remove_photo_button.configure(state="normal" if can_remove else "disabled")

    def _save_contact(self):
        if not self.form_widgets['nome'].get().strip():
            messagebox.showerror("Erro de Validação", "O campo 'Nome Completo' é obrigatório.", parent=self); return
        
        contact_service = self.repos.get("contact")
        if not contact_service:
            messagebox.showerror("Erro Crítico", "Componentes internos (serviços) não foram encontrados.")
            return

        raw_form_data = {'pessoa_obj': self.pessoa}
        for field_name, widget in self.form_widgets.items():
            if hasattr(self.pessoa, field_name):
                value = None
                if field_name == 'latitude' or field_name == 'longitude':
                    try:
                        val_str = widget.get().strip()
                        value = float(val_str) if val_str else None
                    except ValueError:
                        value = None 
                elif isinstance(widget, ctk.CTkSwitch):
                    value = widget.get()
                # --- ALTERAÇÃO: Usando a classe correta na verificação de tipo ---
                elif isinstance(widget, (ctk.CTkEntry, CTkScrollableComboBox, CTkAutocompleteComboBox, ctk.CTkComboBox, ctk.CTkSegmentedButton, tk.StringVar)):
                    value = widget.get()
                
                if isinstance(value, str): value = value.strip()
                
                if field_name == 'genero' and isinstance(value, str): 
                    value = value.lower() if value else None
                
                raw_form_data[field_name] = value

        selected_list_ids = [list_id for list_id, var in self.list_checkbox_vars.items() if var.get()]
        
        saved_pessoa = contact_service.process_and_save_person(
            raw_data=raw_form_data,
            list_ids=selected_list_ids,
            new_photo_path=self.new_photo_path_temp
        )
        
        if saved_pessoa:
            messagebox.showinfo("Sucesso", "Contato salvo com sucesso!", parent=self)
            self.app.dispatch("data_changed", source="person_form")
            self.destroy()