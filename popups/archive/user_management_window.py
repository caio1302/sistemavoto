# --- START OF FILE popups/user_management_window.py ---

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from pathlib import Path
import os
import shutil
import hashlib
import logging

import config
from functions import ui_helpers, data_helpers
from dto.user import User

from functions import formatters
from .datepicker import DatePicker
import re

class UserManagementWindow(tk.Toplevel):
    def __init__(self, parent, loader_instance):
        super().__init__(parent)
        self.parent_app = parent
        self.loader = loader_instance

        self.title("Gerenciamento de Usuários")
        self.geometry("800x600")
        self.resizable(False, False)
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()

        self.selected_user_id = None
        self.photo_tk = None
        self.new_photo_path = None

        self._create_widgets()
        self._load_users_to_list()
        ui_helpers.center_window(self)
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())

    def _create_widgets(self):
        # --- Layout Principal ---
        main_frame = ttk.Frame(self, style="TFrame", padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # --- Painel Esquerdo: Lista de Usuários ---
        left_panel = ttk.Frame(main_frame, style="TFrame", padding=10)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        
        ttk.Label(left_panel, text="Usuários Cadastrados", font=(config.FONT_FAMILY, 11, "bold"), background="white").pack(pady=(0, 5))
        
        self.user_tree = ttk.Treeview(left_panel, columns=('Nível',), show='tree headings', height=20)
        self.user_tree.heading('#0', text='Nome de Usuário')
        self.user_tree.heading('Nível', text='Nível')
        self.user_tree.column('#0', width=150, anchor='w')
        self.user_tree.column('Nível', width=80, anchor='center')
        self.user_tree.pack(fill=tk.BOTH, expand=True)
        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        # --- Painel Direito: Formulário de Cadastro/Edição ---
        right_panel = ttk.Frame(main_frame, style="TFrame", padding=10)
        right_panel.grid(row=0, column=1, sticky="nsew")

        # --- Seção da Foto ---
        photo_frame = ttk.Frame(right_panel, style="TFrame")
        photo_frame.pack(pady=10)
        self.photo_label = tk.Label(photo_frame, bg='lightgrey', relief="solid", borderwidth=1, width=150, height=180)
        self.photo_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(photo_frame, text="Alterar Foto", command=self._select_photo).pack(side=tk.LEFT, anchor="s")

        # --- Formulário ---
        form_frame = ttk.Frame(right_panel, style="TFrame")
        form_frame.pack(fill=tk.X, padx=20, pady=10)
        
        form_fields = {
            "Nome Completo:": "nome_completo",
            "Data de Nascimento (DD/MM/AAAA):": "data_nascimento",
            "Telefone:": "telefone",
            "E-mail:": "email",
            "Nome de Usuário:": "nome_usuario",
            "Nível de Acesso:": "nivel_acesso"
        }
        
        self.form_widgets = {}
        row_count = 0
        vcmd = (self.register(formatters.validate_numeric_input), '%P')

        # Funções auxiliares para formatação (iguais às da outra janela)
        def apply_formatting(widget, formatter_func):
            unformatted_value = re.sub(r'\D', '', widget.get())
            formatted_value = formatter_func(unformatted_value)
            widget.delete(0, tk.END)
            widget.insert(0, formatted_value)

        def remove_formatting(widget):
            unformatted_value = re.sub(r'\D', '', widget.get())
            widget.delete(0, tk.END)
            widget.insert(0, unformatted_value)
            
        for label, key in form_fields.items():
            ttk.Label(form_frame, text=label, background="white").grid(row=row_count, column=0, sticky="e", pady=4, padx=5)
            
            if key == "nivel_acesso":
                widget = ttk.Combobox(form_frame, values=["admin", "coordenador", "assessor"], state="readonly")
            else:
                widget = ttk.Entry(form_frame)
            
            widget.grid(row=row_count, column=1, sticky="ew", pady=4)
            self.form_widgets[key] = widget

            if "Data" in label:
                widget.config(state="readonly")
                widget.bind("<Button-1>", lambda event, w=widget: DatePicker(self, w))
            
            if key == "telefone":
                # Label modificado para maior clareza
                form_frame.grid_slaves(row=row_count, column=0)[0].config(text="Telefone (só números):")
                widget.config(validate='key', validatecommand=vcmd)
                widget.bind("<FocusOut>", lambda e, w=widget: apply_formatting(w, formatters.format_celular))
                widget.bind("<FocusIn>", lambda e, w=widget: remove_formatting(w))

            row_count += 1
        form_frame.columnconfigure(1, weight=1)

        # --- Campos de Senha ---
        pass_frame = ttk.LabelFrame(right_panel, text="Alterar Senha (opcional)", style="TLabelframe")
        pass_frame.pack(fill=tk.X, padx=20, pady=10)
        pass_frame.columnconfigure(1, weight=1)
        
        ttk.Label(pass_frame, text="Nova Senha:", background="white").grid(row=0, column=0, sticky="e", pady=4, padx=5)
        self.pass1_entry = ttk.Entry(pass_frame, show="*")
        self.pass1_entry.grid(row=0, column=1, sticky="ew", pady=4)
        
        ttk.Label(pass_frame, text="Confirmar Nova Senha:", background="white").grid(row=1, column=0, sticky="e", pady=4, padx=5)
        self.pass2_entry = ttk.Entry(pass_frame, show="*")
        self.pass2_entry.grid(row=1, column=1, sticky="ew", pady=4)

        # --- Botões de Ação ---
        button_container = ttk.Frame(right_panel, style="TFrame", padding=(0, 20, 0, 0))
        button_container.pack(fill=tk.X, padx=20)
        button_container.columnconfigure((0,1,2,3), weight=1)
        
        ttk.Button(button_container, text="Novo Usuário", command=self._clear_form).grid(row=0, column=0, padx=5)
        ttk.Button(button_container, text="Salvar Alterações", command=self._save_user).grid(row=0, column=1, padx=5)
        ttk.Button(button_container, text="Apagar Usuário", command=self._delete_user).grid(row=0, column=2, padx=5)
        ttk.Button(button_container, text="Fechar", command=self.destroy).grid(row=0, column=3, padx=5)

    def _load_users_to_list(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        
        # Categorias
        admins = self.user_tree.insert("", "end", text="Administradores", open=True)
        coords = self.user_tree.insert("", "end", text="Coordenadores", open=True)
        assessores = self.user_tree.insert("", "end", text="Assessores", open=True)
        outros = self.user_tree.insert("", "end", text="Outros", open=True)
        
        users = self.loader.get_all_users()
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
        # Ignora cliques nos nós de categoria
        if not self.selected_user_id.isdigit():
            self._clear_form()
            return

        user = self.loader.get_user_by_id(self.selected_user_id)
        if user:
            self._populate_form(user)

    def _populate_form(self, user: User):
        self._clear_form() # Limpa antes de preencher
        self.selected_user_id = user.id_usuario

        for key, widget in self.form_widgets.items():
            value = getattr(user, key, "")
            if isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, tk.END)
                widget.insert(0, value)
        
        self.new_photo_path = None # Reseta o caminho da nova foto
        self._load_photo(user.caminho_foto)
    
    def _clear_form(self):
        self.selected_user_id = None
        for widget in self.form_widgets.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.pass1_entry.delete(0, tk.END)
        self.pass2_entry.delete(0, tk.END)
        self.new_photo_path = None
        self._load_photo(None) # Carrega placeholder
        self.user_tree.selection_remove(self.user_tree.selection())

    def _select_photo(self):
        filepath = filedialog.askopenfilename(
            title="Selecione a foto do usuário",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png"), ("Todos os arquivos", "*.*")]
        )
        if filepath:
            self.new_photo_path = filepath
            self._load_photo(filepath)

    def _load_photo(self, photo_path):
        try:
            if not photo_path or not os.path.exists(photo_path):
                img_path = config.PLACEHOLDER_PHOTO_PATH
            else:
                img_path = photo_path
            
            img_obj = Image.open(img_path)
            img_obj.thumbnail((150, 180), Image.LANCZOS)
            self.photo_tk = ImageTk.PhotoImage(img_obj)
            self.photo_label.config(image=self.photo_tk)
        except Exception as e:
            logging.warning(f"Erro ao carregar foto do usuário: {e}")
            self.photo_label.config(image=None, text="Erro Foto")

    def _save_user(self):
        # Coleta dados do formulário
        user_data = {key: widget.get() for key, widget in self.form_widgets.items()}
        
        if not user_data.get("nome_usuario") or not user_data.get("nome_completo"):
            messagebox.showerror("Erro de Validação", "Nome de Usuário e Nome Completo são obrigatórios.", parent=self)
            return

        # Lógica de Senha
        new_pass1 = self.pass1_entry.get()
        new_pass2 = self.pass2_entry.get()
        final_hash_senha = None

        if self.selected_user_id:  # Editando usuário existente
            if new_pass1:  # A senha só será alterada se o campo for preenchido
                if new_pass1 != new_pass2:
                    messagebox.showerror("Erro de Senha", "As senhas não coincidem.", parent=self)
                    return
                final_hash_senha = hashlib.sha256(new_pass1.encode('utf-8')).hexdigest()
        else:  # Criando um novo usuário
            if not new_pass1 or new_pass1 != new_pass2:
                messagebox.showerror("Erro de Senha", "Para um novo usuário, a senha é obrigatória e as senhas devem coincidir.", parent=self)
                return
            final_hash_senha = hashlib.sha256(new_pass1.encode('utf-8')).hexdigest()

        # Prepara o objeto User para salvar
        user_to_save = User.from_dict(user_data)
        user_to_save.id_usuario = int(self.selected_user_id) if self.selected_user_id else 0
        user_to_save.hash_senha = final_hash_senha

        # Se for um usuário existente, pega o caminho da foto atual para não perdê-lo
        if user_to_save.id_usuario != 0:
            current_user = self.loader.get_user_by_id(user_to_save.id_usuario)
            if current_user:
                user_to_save.caminho_foto = current_user.caminho_foto
        
        # Salva ou atualiza o usuário no banco de dados
        saved_user = self.loader.save_user(user_to_save)
        if not saved_user:
            messagebox.showerror("Erro de Banco de Dados", "Não foi possível salvar os dados do usuário.", parent=self)
            return
            
        # Se uma nova foto foi selecionada, agora que temos um ID garantido,
        # podemos copiá-la e atualizar o registro no banco.
        if self.new_photo_path:
            try:
                dest_folder = Path(config.FOTOS_ATUALIZADAS_PATH)
                dest_folder.mkdir(exist_ok=True)
                dest_filename = f"user_{saved_user.id_usuario}{Path(self.new_photo_path).suffix}"
                dest_path = dest_folder / dest_filename
                
                shutil.copy(self.new_photo_path, dest_path)
                
                # Atualiza o objeto salvo com o novo caminho e salva novamente
                saved_user.caminho_foto = str(dest_path.relative_to(config.BASE_PATH)).replace('\\', '/')
                self.loader.save_user(saved_user) # Atualiza apenas o caminho da foto
                
            except Exception as e:
                messagebox.showwarning("Aviso de Foto", f"Usuário salvo com sucesso, mas ocorreu um erro ao salvar a nova foto: {e}", parent=self)
                logging.error(f"Erro ao copiar/atualizar foto para usuário ID {saved_user.id_usuario}: {e}", exc_info=True)

        messagebox.showinfo("Sucesso", "Usuário salvo com sucesso!", parent=self)
        self._load_users_to_list()
        self._clear_form()

    def _delete_user(self):
        if not self.selected_user_id:
            messagebox.showwarning("Nenhuma Seleção", "Selecione um usuário para apagar.", parent=self)
            return
        
        user_to_delete = self.loader.get_user_by_id(self.selected_user_id)
        if not user_to_delete: return

        if user_to_delete.nome_usuario == 'admin':
            messagebox.showerror("Ação Proibida", "O usuário 'admin' não pode ser apagado.", parent=self)
            return

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja apagar o usuário '{user_to_delete.nome_usuario}' permanentemente?", icon='warning', parent=self):
            if self.loader.delete_user(self.selected_user_id):
                messagebox.showinfo("Sucesso", "Usuário apagado.", parent=self)
                # Apaga a foto do usuário se existir
                if user_to_delete.caminho_foto:
                    try:
                        photo_to_delete = Path(config.BASE_PATH) / user_to_delete.caminho_foto
                        if photo_to_delete.exists():
                            os.remove(photo_to_delete)
                            logging.info(f"Foto do usuário {self.selected_user_id} apagada.")
                    except Exception as e:
                        logging.warning(f"Não foi possível apagar a foto do usuário: {e}")
                self._load_users_to_list()
                self._clear_form()
            else:
                messagebox.showerror("Erro", "Não foi possível apagar o usuário do banco de dados.", parent=self)