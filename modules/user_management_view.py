import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from pathlib import Path
import os
import shutil
import hashlib
import logging
import re

import config
from functions import ui_helpers, data_helpers
from dto.user import User

from functions import formatters
from popups.datepicker import DatePicker
# --- ALTERAÇÃO: Importa a classe correta 'CTkAutocompleteComboBox' ---
from .custom_widgets import CTkAutocompleteComboBox

class UserManagementView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app

        self.selected_user_id = None
        self.new_photo_path_temp = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()
        self._load_users_to_list()

    def _create_widgets(self):
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left_panel, text="Usuários Cadastrados", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        
        self._style_treeview()
        
        self.user_tree = ttk.Treeview(left_panel, columns=('Nível',), show='tree headings', height=20, style="Custom.Treeview")
        self.user_tree.heading('#0', text='Nome de Usuário'); self.user_tree.column('#0', width=150)
        self.user_tree.heading('Nível', text='Nível'); self.user_tree.column('Nível', width=80, anchor="center")
        self.user_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        right_panel = ctk.CTkScrollableFrame(self, label_text="Detalhes do Usuário")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        
        photo_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        photo_frame.pack(pady=10)
        self.photo_label = ctk.CTkLabel(photo_frame, text="", width=120, height=150, fg_color="gray80", corner_radius=6)
        self.photo_label.pack()
        ctk.CTkButton(photo_frame, text="Alterar Foto", height=20, command=self._select_photo).pack(pady=(5,0))
        
        form_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=10, expand=True)
        form_frame.columnconfigure(1, weight=1)
        
        self.form_widgets = {}
        fields = {"Nome Completo:": "nome_completo", "Data de Nascimento:": "data_nascimento", "Telefone:": "telefone", "E-mail:": "email", "Nome de Usuário:": "nome_usuario", "Nível de Acesso:": "nivel_acesso"}
        
        for i, (label, key) in enumerate(fields.items()):
            ctk.CTkLabel(form_frame, text=label).grid(row=i, column=0, sticky="e", pady=4, padx=5)
            if key == "nivel_acesso":
                # --- ALTERAÇÃO: Usando a classe correta e removendo state='readonly' ---
                user_levels = ["admin", "coordenador", "assessor"]
                widget = CTkAutocompleteComboBox(form_frame, values=user_levels, height=28)
            else:
                widget = ctk.CTkEntry(form_frame)
            
            widget.grid(row=i, column=1, sticky="ew", pady=4)
            self.form_widgets[key] = widget

            if key == "data_nascimento": 
                widget.configure(state="readonly")
                widget.bind("<Button-1>", lambda event, w=widget: DatePicker(self, w))
            
            if key == "telefone":
                widget.bind("<KeyRelease>", lambda e, w=widget: self._apply_mask(w, formatters.format_celular, e))
                widget.bind("<FocusOut>", lambda e, w=widget: self._apply_mask(w, formatters.format_celular, focus_out=True))
            elif key == "email":
                widget.bind("<FocusOut>", lambda e, w=widget: self._validate_email_entry(w))

        pass_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        pass_frame.pack(fill="x", padx=20, pady=10, expand=True)
        pass_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(pass_frame, text="Nova Senha:").grid(row=0, column=0, sticky="e", pady=4, padx=5)
        self.pass1_entry = ctk.CTkEntry(pass_frame, show="*")
        self.pass1_entry.grid(row=0, column=1, sticky="ew", pady=4)
        
        ctk.CTkLabel(pass_frame, text="Confirmar Senha:").grid(row=1, column=0, sticky="e", pady=4, padx=5)
        self.pass2_entry = ctk.CTkEntry(pass_frame, show="*")
        self.pass2_entry.grid(row=1, column=1, sticky="ew", pady=4)

        button_container = ctk.CTkFrame(right_panel, fg_color="transparent")
        button_container.pack(pady=20, expand=True)
        button_container.columnconfigure((0,1,2), weight=1)
        
        ctk.CTkButton(button_container, text="Novo Usuário", command=self._clear_form).grid(row=0, column=0, padx=5)
        ctk.CTkButton(button_container, text="Salvar Alterações", command=self._save_user).grid(row=0, column=1, padx=5)
        ctk.CTkButton(button_container, text="Apagar Usuário", fg_color="#D32F2F", hover_color="#B71C1C", command=self._delete_user).grid(row=0, column=2, padx=5)
        
        ctk.CTkButton(right_panel, text="Fechar", command=lambda: self.master.destroy()).pack(side='right', padx=20, pady=(0,20))

    def _validate_email_entry(self, entry_widget):
        email = entry_widget.get().strip()
        if not email:
            entry_widget.configure(border_color=entry_widget.cget("fg_color"), border_width=1, text_color=entry_widget.cget("text_color"))
            return

        if not formatters.validate_email(email):
            entry_widget.configure(border_color="red", border_width=2, text_color="red")
        else:
            entry_widget.configure(border_color=entry_widget.cget("fg_color"), border_width=1, text_color=entry_widget.cget("text_color"))
            
    def _apply_mask(self, entry_widget, formatter_func, event=None, focus_out=False):
        current_text = entry_widget.get()
        unformatted_text = "".join(filter(str.isdigit, current_text))
        
        if not focus_out and len(unformatted_text) < 2:
             return
             
        formatted_text = formatter_func(unformatted_text)

        if event and event.type == ctk.StringVar._tkbind['<<ComboboxSelected>>'] or event is None:
             entry_widget.delete(0, tk.END)
             entry_widget.insert(0, formatted_text)
             return

        cursor_pos_before = entry_widget.index(ctk.INSERT)
        digits_before_cursor = len(re.sub(r'\D', '', current_text[:cursor_pos_before]))
        
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, formatted_text)

        new_cursor_pos = 0
        current_digits = 0
        for i, char in enumerate(formatted_text):
            if current_digits == digits_before_cursor:
                new_cursor_pos = i
                break
            if char.isdigit():
                current_digits += 1
        
        entry_widget.icursor(new_cursor_pos if new_cursor_pos > 0 else len(formatted_text))


    def _load_users_to_list(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        
        user_repo = self.repos.get("user")
        if not user_repo: return

        admins = self.user_tree.insert("", "end", text="Administradores", open=True, iid="cat_admin")
        coords = self.user_tree.insert("", "end", text="Coordenadores", open=True, iid="cat_coord")
        assessores = self.user_tree.insert("", "end", text="Assessores", open=True, iid="cat_assessor")
        outros = self.user_tree.insert("", "end", text="Outros", open=True, iid="cat_outros")
        
        users = user_repo.get_all_users()
        for user in users:
            parent_node = outros
            if user.nivel_acesso == 'admin': parent_node = admins
            elif user.nivel_acesso == 'coordenador': parent_node = coords
            elif user.nivel_acesso == 'assessor': parent_node = assessores
            self.user_tree.insert(parent_node, "end", text=user.nome_usuario, values=(user.nivel_acesso,), iid=user.id_usuario)

    def _on_user_select(self, event=None):
        selected_items = self.user_tree.selection()
        if not selected_items: return
        
        self.selected_user_id = selected_items[0]
        if not str(self.selected_user_id).isdigit():
            self._clear_form()
            return

        user = self.repos.get("user").get_user_by_id(self.selected_user_id)
        if user:
            self._populate_form(user)

    def _populate_form(self, user: User):
        self._clear_form()
        self.selected_user_id = user.id_usuario

        for key, widget in self.form_widgets.items():
            value = getattr(user, key, "") or ""
            # --- ALTERAÇÃO: Usa a classe correta na verificação de tipo ---
            if isinstance(widget, CTkAutocompleteComboBox):
                widget.set(value)
            else:
                widget.delete(0, ctk.END)
                widget.insert(0, value)
                
                if key == "telefone": 
                    self._apply_mask(widget, formatters.format_celular, focus_out=True)
                elif key == "email":
                    self._validate_email_entry(widget)
        
        self.pass1_entry.delete(0, ctk.END)
        self.pass2_entry.delete(0, ctk.END)
        
        self.new_photo_path_temp = None
        self._load_photo(user.caminho_foto)
    
    def _clear_form(self):
        self.selected_user_id = None
        for widget in self.form_widgets.values():
            # --- ALTERAÇÃO: Usa a classe correta na verificação de tipo ---
            if isinstance(widget, CTkAutocompleteComboBox):
                widget.set("")
            else:
                widget.delete(0, ctk.END)
        
        if "email" in self.form_widgets and isinstance(self.form_widgets["email"], ctk.CTkEntry):
            self.form_widgets["email"].configure(border_color=self.form_widgets["email"].cget("fg_color"), border_width=1, text_color=self.form_widgets["email"].cget("text_color"))

        self.pass1_entry.delete(0, ctk.END)
        self.pass2_entry.delete(0, ctk.END)
        self.new_photo_path_temp = None
        self._load_photo(None)
        if self.user_tree.selection(): self.user_tree.selection_remove(self.user_tree.selection())

    def _select_photo(self):
        filepath = filedialog.askopenfilename(title="Selecione a foto do usuário", filetypes=[("Imagens", "*.jpg *.jpeg *.png"), ("Todos os arquivos", "*.*")])
        if filepath:
            self.new_photo_path_temp = filepath
            self._load_photo(filepath)

    def _load_photo(self, photo_path_rel):
        try:
            image_path_to_load = os.path.join(config.BASE_PATH, photo_path_rel) if photo_path_rel and os.path.exists(os.path.join(config.BASE_PATH, photo_path_rel)) else config.PLACEHOLDER_PHOTO_PATH
            pil_image = Image.open(image_path_to_load)
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(120, 150))
            self.photo_label.configure(image=ctk_image, text="")
        except Exception as e:
            logging.warning(f"Erro ao carregar foto do usuário: {e}", exc_info=True)
            self.photo_label.configure(image=None, text="Erro Foto")

    def _save_user(self):
        user_repo = self.repos.get("user")
        if not user_repo:
            messagebox.showerror("Erro", "Repositório de Usuário não encontrado.")
            return

        user_data = {key: widget.get() for key, widget in self.form_widgets.items()}
        
        if not user_data.get("nome_usuario") or not user_data.get("nome_completo"):
            messagebox.showerror("Erro de Validação", "Nome de Usuário e Nome Completo são obrigatórios.", parent=self)
            return

        if "email" in self.form_widgets and user_data["email"] and not formatters.validate_email(user_data["email"]):
            messagebox.showerror("Erro de Validação", "Formato de e-mail inválido.", parent=self)
            self._validate_email_entry(self.form_widgets["email"])
            return

        new_pass1 = self.pass1_entry.get(); new_pass2 = self.pass2_entry.get()
        final_hash_senha = None

        if self.selected_user_id:
            if new_pass1:
                if new_pass1 != new_pass2: messagebox.showerror("Erro", "As senhas não coincidem."); return
                final_hash_senha = hashlib.sha256(new_pass1.encode('utf-8')).hexdigest()
        else:
            if not new_pass1 or new_pass1 != new_pass2: messagebox.showerror("Erro", "Para um novo usuário, a senha é obrigatória e deve coincidir."); return
            final_hash_senha = hashlib.sha256(new_pass1.encode('utf-8')).hexdigest()
        
        user_to_save = User.from_dict(user_data)
        user_to_save.id_usuario = int(self.selected_user_id) if self.selected_user_id else 0
        if final_hash_senha: user_to_save.hash_senha = final_hash_senha
        
        if not self.new_photo_path_temp and user_to_save.id_usuario:
            existing_user = user_repo.get_user_by_id(user_to_save.id_usuario)
            if existing_user: user_to_save.caminho_foto = existing_user.caminho_foto

        saved_user = user_repo.save_user(user_to_save)
        if not saved_user: messagebox.showerror("Erro", "Não foi possível salvar o usuário."); return

        if self.new_photo_path_temp:
            try:
                dest_folder = Path(config.FOTOS_ATUALIZADAS_PATH); dest_folder.mkdir(exist_ok=True)
                file_extension = Path(self.new_photo_path_temp).suffix
                dest_filename = f"user_{saved_user.id_usuario}{file_extension}"
                dest_path_abs = dest_folder / dest_filename
                
                shutil.copy(self.new_photo_path_temp, dest_path_abs)
                
                saved_user.caminho_foto = str(dest_path_abs.relative_to(config.BASE_PATH)).replace('\\', '/')
                user_repo.save_user(saved_user)
            except Exception as e:
                messagebox.showwarning("Aviso", f"Usuário salvo, mas erro ao salvar foto: {e}")
                logging.error(f"Erro ao copiar/salvar foto para usuário ID {saved_user.id_usuario}: {e}", exc_info=True)
        
        messagebox.showinfo("Sucesso", "Usuário salvo com sucesso!")
        self._load_users_to_list()
        self._clear_form()

    def _delete_user(self):
        user_repo = self.repos.get("user")
        if not user_repo: return

        if not self.selected_user_id: messagebox.showwarning("Aviso", "Selecione um usuário para apagar."); return
        
        user_to_delete = user_repo.get_user_by_id(self.selected_user_id)
        if not user_to_delete: return
        if user_to_delete.nome_usuario == 'admin': messagebox.showerror("Erro", "O usuário 'admin' não pode ser apagado."); return
        if self.app.logged_in_user and str(self.app.logged_in_user.id_usuario) == str(self.selected_user_id):
            messagebox.showerror("Erro", "Você não pode apagar o seu próprio usuário enquanto logado.")
            return

        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja apagar o usuário '{user_to_delete.nome_usuario}' permanentemente?"):
            if user_repo.delete_user(self.selected_user_id):
                if user_to_delete.caminho_foto:
                    try: 
                        photo_file_path = Path(config.BASE_PATH) / user_to_delete.caminho_foto
                        if photo_file_path.exists(): os.remove(photo_file_path)
                    except OSError as e: 
                        logging.warning(f"Não foi possível apagar o arquivo de foto do usuário: {e}", exc_info=True)

                messagebox.showinfo("Sucesso", "Usuário apagado.")
                self._load_users_to_list()
                self._clear_form()
            else:
                messagebox.showerror("Erro", "Não foi possível apagar o usuário.")

    def _style_treeview(self):
        style = ttk.Style()
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        header_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"])
        selected_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        
        style.theme_use("clam")
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, 
                        fieldbackground=bg_color, borderwidth=0, rowheight=28)
        style.map("Custom.Treeview", background=[('selected', selected_color)])
        style.configure("Custom.Treeview.Heading", background=header_bg, foreground=text_color, 
                        relief="flat", font=ctk.CTkFont(family="Calibri", size=11, weight="bold"))

    def _apply_appearance_mode(self, color_tuple):
        return color_tuple[1] if ctk.get_appearance_mode() == "Dark" else color_tuple[0]