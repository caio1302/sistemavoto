import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import sys

import config
from .user_management_view import UserManagementView
from popups.backup_options_window import BackupOptionsWindow
from .progress_window import ProgressWindow
from popups.app_params_window import AppParamsWindow
from functions.backup_helpers import execute_backup_thread, execute_restore_thread

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app, initial_filters=None):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._create_widgets()

    def geocode_all_contacts(self):
        msg = ("Esta ação irá percorrer toda a sua base de contatos para obter coordenadas geográficas.\n\n"
               "O processo pode demorar dependendo do tamanho da sua base de dados e dos limites da sua chave de API do Google.\n\n"
               "Deseja iniciar o processo? Você pode interrompê-lo a qualquer momento.")
        if messagebox.askyesno("Confirmar Geocodificação em Massa", msg, icon="info"):
            geo_service = self.repos.get("geo")
            if not geo_service:
                messagebox.showerror("Erro", "Serviço de geolocalização não encontrado.")
                return
            
            progress_win = ProgressWindow(self, "Geocodificando Base de Contatos...")
            progress_win.start_operation(geo_service.geocode_all_contacts)

    def geocode_all_organizations(self):
        msg = ("Esta ação irá percorrer toda a sua base de organizações para obter coordenadas geográficas.\n\n"
               "O processo pode demorar dependendo do tamanho da sua base de dados e dos limites da sua chave de API do Google.\n\n"
               "Deseja iniciar o processo? Você pode interrompê-lo a qualquer momento.")
        if messagebox.askyesno("Confirmar Geocodificação em Massa", msg, icon="info"):
            geo_service = self.repos.get("geo")
            if not geo_service:
                messagebox.showerror("Erro", "Serviço de geolocalização não encontrado.")
                return
            
            progress_win = ProgressWindow(self, "Geocodificando Base de Organizações...")
            progress_win.start_operation(geo_service.geocode_all_organizations)
            
    def _create_widgets(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(header_frame, text="Configurações do Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        scrollable_frame = ctk.CTkScrollableFrame(self)
        scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(scrollable_frame, text="Administração", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,10), padx=20, anchor="w")
        if self.app.logged_in_user.is_admin:
            btn_user_mgmt = ctk.CTkButton(scrollable_frame, text="Gerenciar Usuários", command=self._open_user_management)
            btn_user_mgmt.pack(pady=5, padx=20, anchor="w")
        
        ctk.CTkLabel(scrollable_frame, text="Parâmetros Gerais", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        btn_app_params = ctk.CTkButton(scrollable_frame, text="Definir Proprietário, Logo e Mapa...", command=self._open_app_params_window)
        btn_app_params.pack(pady=5, padx=20, anchor="w")  

        ctk.CTkLabel(scrollable_frame, text="Manutenção de Dados", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        btn_fix_duplicates = ctk.CTkButton(scrollable_frame, text="Corrigir Contatos Duplicados...", command=self.corrigir_duplicatas)
        btn_fix_duplicates.pack(pady=5, padx=20, anchor="w")
        
        btn_sync_cities = ctk.CTkButton(scrollable_frame, text="Sincronizar Cidades dos Contatos...", command=self.sincronizar_cidades)
        btn_sync_cities.pack(pady=5, padx=20, anchor="w")
        
        btn_geocode = ctk.CTkButton(scrollable_frame, text="Geocodificar Base de Contatos...", command=self.geocode_all_contacts)
        btn_geocode.pack(pady=5, padx=20, anchor="w")
        btn_geocode_orgs = ctk.CTkButton(scrollable_frame, text="Geocodificar Base de Organizações...", command=self.geocode_all_organizations)
        btn_geocode_orgs.pack(pady=5, padx=20, anchor="w")
        
        btn_create_backup = ctk.CTkButton(scrollable_frame, text="Criar Backup Completo...", command=self.create_backup)
        btn_create_backup.pack(pady=5, padx=20, anchor="w")
        btn_restore_backup = ctk.CTkButton(scrollable_frame, text="Restaurar de um Backup...", command=self.restore_backup)
        btn_restore_backup.pack(pady=5, padx=20, anchor="w")
        
        ctk.CTkLabel(scrollable_frame, text="Importação de cidades, prefeituras e eleitorado", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        btn_import_orgs = ctk.CTkButton(scrollable_frame, text="Importar Órgãos Públicos (CSV)...", command=self.importar_orgaos_publicos_csv)
        btn_import_orgs.pack(pady=5, padx=20, anchor="w")
        btn_import_prefeituras = ctk.CTkButton(scrollable_frame, text="Importar Dados de Prefeituras e Eleitorado...", command=self.importar_prefeituras_eleitorado_csv)
        btn_import_prefeituras.pack(pady=5, padx=20, anchor="w")

        ctk.CTkLabel(scrollable_frame, text="Importação de Dados Cadastrais e Votação", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        btn_import_cadastrais = ctk.CTkButton(scrollable_frame, text="Importar Dados Cadastrais de Candidatos (CSV)...", command=self.importar_dados_cadastrais_csv)
        btn_import_cadastrais.pack(pady=5, padx=20, anchor="w")
        btn_import_votacao = ctk.CTkButton(scrollable_frame, text="Importar Votação por Seção (CSV)...", command=self.import_election_csv)      
        btn_import_votacao.pack(pady=5, padx=20, anchor="w")

    def _open_app_params_window(self):
        AppParamsWindow(self, self.repos, self.app)

    def _open_user_management(self):
        for widget in self.winfo_children(): widget.destroy()
        back_btn = ctk.CTkButton(self, text="< Voltar para Configurações", command=lambda: self.app.dispatch("navigate", module_name="Configurações"))
        back_btn.pack(pady=10, padx=10, anchor="w")
        user_view = UserManagementView(self, self.repos, self.app)
        user_view.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
    def create_backup(self):
        options_win = BackupOptionsWindow(self)
        self.wait_window(options_win) # Espera a janela de opções fechar
        options = options_win.get_selection()
        if not options or not any(options.values()): return
        progress_win = ProgressWindow(self, "Criando Backup...")
        progress_win.start_operation(execute_backup_thread, options)
        
    def sincronizar_cidades(self):
        if not messagebox.askyesno("Confirmar Sincronização", "Esta ação atualizará o campo 'cidade' de todos os contatos sem cidade definida, usando a cidade de sua última candidatura.\n\nDeseja continuar?", icon="info"):
            return
            
        import_service = self.repos.get("import")
        if not import_service:
            messagebox.showerror("Erro", "Serviço de importação não encontrado.")
            return
            
        progress_win = ProgressWindow(self, "Sincronizando Cidades dos Contatos...")
        progress_win.start_operation(import_service.sincronizar_cidades_contatos)

    def corrigir_duplicatas(self):
        if not messagebox.askyesno("Confirmar Correção", "ATENÇÃO!\n\nEsta ação irá buscar e fundir contatos duplicados. É recomendado criar um backup antes.\n\nDeseja iniciar a correção?", icon="warning"):
            return
            
        import_service = self.repos.get("import")
        if not import_service:
            messagebox.showerror("Erro", "Serviço de importação não encontrado.")
            return

        progress_win = ProgressWindow(self, "Corrigindo Duplicatas no Banco...")
        progress_win.start_operation(import_service.corrigir_duplicatas_de_pessoas)

    def restore_backup(self):
        backup_path = filedialog.askopenfilename(title="Selecione o arquivo de Backup (.zip)", filetypes=[("Arquivos de Backup", "*.zip")], initialdir=os.path.join(config.BASE_PATH, "backups"))
        if not backup_path: return
        if not messagebox.askyesno("Confirmar Restauração", "ATENÇÃO!\nIsto substituirá os dados e arquivos atuais. A aplicação será reiniciada.\nDeseja continuar?", icon="warning"):
            return
            
        progress_win = ProgressWindow(self, "Restaurando Backup...")
        progress_win.close_button.configure(text="Reiniciar Agora", command=self._restart_app)
        progress_win.start_operation(execute_restore_thread, backup_path)

    def _restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _execute_generic_import(self, method_name, title, file_dialog_title, file_dialog_types):
        import_service = self.repos.get("import")
        if not import_service:
            messagebox.showerror("Erro", "Serviço de importação não encontrado.")
            return
        
        method_to_call = getattr(import_service, method_name, None)
        if not method_to_call:
            messagebox.showerror("Erro", f"Método de importação '{method_name}' não encontrado.")
            return

        filepath = filedialog.askopenfilename(title=file_dialog_title, filetypes=file_dialog_types)
        if not filepath: return
        
        progress_win = ProgressWindow(self, title)
        progress_win.start_operation(method_to_call, filepath)

    def importar_orgaos_publicos_csv(self):
        self._execute_generic_import("importar_orgaos_publicos_csv", "Importando Órgãos Públicos...", "Selecione o CSV de Órgãos Públicos", [("Arquivos CSV", "*.csv")])

    def importar_dados_cadastrais_csv(self):
        self._execute_generic_import("importar_dados_cadastrais", "Importando Dados Cadastrais...", "Selecione o CSV de Dados Cadastrais", [("Arquivos CSV", "*.csv")])

    def import_election_csv(self):
        self._execute_generic_import("importar_csv_eleicao", "Importando Votação...", "Selecione o CSV de Votação por Seção", [("Arquivos CSV", "*.csv")])

    def importar_prefeituras_eleitorado_csv(self):
        import_service = self.repos.get("import")
        if not import_service:
            messagebox.showerror("Erro", "Serviço de importação não encontrado.")
            return

        messagebox.showinfo("Seleção de Arquivos", "Selecione primeiro o arquivo de PREFEITURAS (prefeituras_sp.csv).", parent=self)
        prefeituras_path = filedialog.askopenfilename(title="Selecione o arquivo de Prefeituras", filetypes=[("Arquivos CSV", "*.csv")])
        if not prefeituras_path: return

        messagebox.showinfo("Seleção de Arquivos", "Agora, selecione o arquivo de ELEITORADO (eleitorado_ANO.csv).", parent=self)
        eleitorado_path = filedialog.askopenfilename(title="Selecione o arquivo do Eleitorado", filetypes=[("Arquivos CSV", "*.csv")])
        if not eleitorado_path: return

        progress_win = ProgressWindow(self, "Importando Prefeituras e Eleitorado...")
        progress_win.start_operation(import_service.importar_prefeituras_eleitorado_csv, prefeituras_path, eleitorado_path)