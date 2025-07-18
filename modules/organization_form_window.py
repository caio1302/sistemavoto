import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import re

import config
from functions import ui_helpers
from dto.organizacao import Organizacao
import functions.formatters as formatters
# --- ALTERAÇÃO: Importa a classe correta 'CTkAutocompleteComboBox' ---
from .custom_widgets import CTkAutocompleteComboBox

class OrganizationFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, repos: dict, app, org_dto=None):
        super().__init__(parent)
        self.repos = repos
        self.app = app
        self.org = org_dto or Organizacao()

        self.title("Nova Organização" if not self.org.id_organizacao else f"Editar: {self.org.nome_fantasia}")
        self.geometry("800x650") 

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.form_widgets = {}

        self._create_widgets()
        
        if self.org.id_organizacao:
            self._populate_form_for_edit()
            
        self.after(100, lambda: ui_helpers.center_window(self))
        if 'nome_fantasia' in self.form_widgets:
            self.form_widgets['nome_fantasia'].focus_set()

    def _create_widgets(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame, text="Nome Fantasia / Nome Comum:").pack(anchor="w")
        self.form_widgets['nome_fantasia'] = ctk.CTkEntry(header_frame, placeholder_text="Nome principal da organização")
        self.form_widgets['nome_fantasia'].pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(header_frame, text="Razão Social (Opcional):").pack(anchor="w")
        self.form_widgets['razao_social'] = ctk.CTkEntry(header_frame, placeholder_text="Nome legal/oficial da organização")
        self.form_widgets['razao_social'].pack(fill="x")
        
        scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Dados Gerais e Contato")
        scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        scrollable_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(scrollable_frame, text="Tipo de Organização:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        # --- ALTERAÇÃO: Usando a classe correta 'CTkAutocompleteComboBox' ---
        tipos = ["", "Empresa Privada", "Prefeitura", "Câmara Municipal", "Secretaria", "Associação", "Sindicato", "Outro"]
        self.form_widgets['tipo_organizacao'] = CTkAutocompleteComboBox(scrollable_frame, values=tipos)
        self.form_widgets['tipo_organizacao'].grid(row=0, column=1, columnspan=3, sticky="ew", padx=10)
        
        ctk.CTkLabel(scrollable_frame, text="CNPJ:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        cnpj_entry = ctk.CTkEntry(scrollable_frame, placeholder_text="##.###.###/####-##")
        cnpj_entry.bind("<KeyRelease>", lambda e, w=cnpj_entry: self._apply_mask(w, formatters.format_cnpj))
        self.form_widgets['cnpj'] = cnpj_entry
        self.form_widgets['cnpj'].grid(row=1, column=1, sticky="ew", padx=10)

        ctk.CTkLabel(scrollable_frame, text="Telefone:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        tel_entry = ctk.CTkEntry(scrollable_frame, placeholder_text="(__) #####-####")
        tel_entry.bind("<KeyRelease>", lambda e, w=tel_entry: self._apply_mask(w, formatters.format_celular))
        self.form_widgets['telefone'] = tel_entry
        self.form_widgets['telefone'].grid(row=2, column=1, sticky="ew", padx=10)
        
        ctk.CTkLabel(scrollable_frame, text="E-mail:").grid(row=2, column=2, sticky="w", padx=10, pady=10)
        self.form_widgets['email'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['email'].grid(row=2, column=3, sticky="ew", padx=10)
        
        ctk.CTkLabel(scrollable_frame, text="Website:").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        self.form_widgets['website'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['website'].grid(row=3, column=1, columnspan=3, sticky="ew", padx=10)
        
        ctk.CTkLabel(scrollable_frame, text="Endereço", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, columnspan=4, sticky="w", padx=10, pady=(20,5))
        
        ctk.CTkLabel(scrollable_frame, text="CEP:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['cep'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['cep'].grid(row=5, column=1, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Logradouro:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['endereco'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['endereco'].grid(row=6, column=1, columnspan=3, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Número:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['numero'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['numero'].grid(row=7, column=1, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Complemento:").grid(row=7, column=2, sticky="w", padx=10, pady=5)
        self.form_widgets['complemento'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['complemento'].grid(row=7, column=3, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Bairro:").grid(row=8, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['bairro'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['bairro'].grid(row=8, column=1, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Cidade:").grid(row=9, column=0, sticky="w", padx=10, pady=5)
        self.form_widgets['cidade'] = ctk.CTkEntry(scrollable_frame)
        self.form_widgets['cidade'].grid(row=9, column=1, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="UF:").grid(row=9, column=2, sticky="w", padx=10, pady=5)
        self.form_widgets['uf'] = ctk.CTkEntry(scrollable_frame, width=80)
        self.form_widgets['uf'].grid(row=9, column=3, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(scrollable_frame, text="Visibilidade no Mapa:").grid(row=10, column=0, sticky="w", padx=10, pady=(20,10))
        self.form_widgets['geo_visivel'] = ctk.CTkSwitch(scrollable_frame, text="Exibir na Geolocalização")
        self.form_widgets['geo_visivel'].grid(row=10, column=1, sticky="w", padx=10, pady=(20,10))
        self.form_widgets['geo_visivel'].configure(command=self._on_visibility_toggled)

        # Botões
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="e", padx=20, pady=10)
        ctk.CTkButton(button_frame, text="Salvar Organização", command=self._save_organization).pack(side="right", padx=(10,0))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self.destroy).pack(side="right")
        
    def _apply_mask(self, widget, formatter_func):
        current_val = widget.get()
        formatted_val = formatter_func(current_val)
        if current_val != formatted_val:
            cursor_pos = widget.index(ctk.INSERT)
            widget.delete(0, ctk.END)
            widget.insert(0, formatted_val)
            try: widget.icursor(cursor_pos)
            except tk.TclError: pass
            
    def _populate_form_for_edit(self):
        for field_name, widget in self.form_widgets.items():
            value = getattr(self.org, field_name, None)
            
            if isinstance(widget, ctk.CTkSwitch):
                if value == 1: widget.select()
                else: widget.deselect()
            # --- ALTERAÇÃO: Usa a classe correta na verificação de tipo ---
            elif isinstance(widget, ctk.CTkEntry) or isinstance(widget, CTkAutocompleteComboBox):
                if isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, ctk.END)
                    widget.insert(0, str(value) if value is not None else "")
                elif isinstance(widget, CTkAutocompleteComboBox):
                    widget.set(str(value) if value is not None else "")
            
            if field_name == 'cnpj': self._apply_mask(widget, formatters.format_cnpj)
            if field_name == 'telefone': self._apply_mask(widget, formatters.format_celular)

    def _on_visibility_toggled(self):
        if self.form_widgets['geo_visivel'].get() == 1 and not (self.org.latitude and self.org.longitude):
            messagebox.showinfo("Geocodificação", "Para geocodificar, preencha o endereço completo e salve o cadastro.", parent=self)

    def _save_organization(self):
        nome_fantasia = self.form_widgets['nome_fantasia'].get().strip()
        if not nome_fantasia:
            messagebox.showerror("Erro de Validação", "O campo 'Nome Fantasia' é obrigatório.", parent=self)
            return

        for field_name, widget in self.form_widgets.items():
            if hasattr(self.org, field_name):
                value = None
                if field_name in ['cnpj', 'telefone', 'cep']:
                    value = re.sub(r'\D', '', widget.get())
                elif isinstance(widget, ctk.CTkSwitch):
                    value = widget.get()
                # --- ALTERAÇÃO: Usa a classe correta na verificação de tipo ---
                elif isinstance(widget, ctk.CTkEntry) or isinstance(widget, CTkAutocompleteComboBox):
                    value = widget.get().strip()
                elif isinstance(widget, ctk.CTkTextbox):
                    value = widget.get("1.0", "end-1c").strip()
                
                setattr(self.org, field_name, value)
        
        contact_service = self.repos.get("contact")
        if not contact_service: return

        saved_org = contact_service.save_organization(self.org)
        
        if saved_org:
            messagebox.showinfo("Sucesso", f"Organização '{saved_org.nome_fantasia}' salva com sucesso!", parent=self)
            self.app.dispatch("data_changed", source="organization_form")
            self.destroy()