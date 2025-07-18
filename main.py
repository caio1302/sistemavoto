import sys
import os
import logging
from tkinter import messagebox
import sqlite3
from dotenv import load_dotenv # <-- Importa a biblioteca para ler o arquivo .env

# --- Repositórios ---
from data_access.user_repository import UserRepository
from data_access.person_repository import PersonRepository
from data_access.organization_repository import OrganizationRepository
from data_access.crm_repository import CrmRepository
from data_access.misc_repository import MiscRepository

# --- Serviços ---
from data_access.report_service import ReportService
from data_access.import_service import ImportService
from data_access.geo_service import GeoService
from data_access.contact_service import ContactService

# --- Carregamento Seguro da Chave de API ---
load_dotenv() # Carrega as variáveis do arquivo .env para o ambiente
# Pega a chave do ambiente. Retorna None se não for encontrada.
MINHA_CHAVE_API_GOOGLE = os.getenv("GOOGLE_API_KEY")

import config
import database_setup
from popups.login_window import LoginWindow, read_token_from_file
from app_ui import MainApplication

def setup_logging():
    log_file = config.LOG_FILE_PATH
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

if __name__ == "__main__":
    setup_logging()
    logging.info("\n" + "="*40 + "\nAplicação e-Votos iniciada.\n" + "="*40)

    # Verifica se a chave de API foi carregada antes de continuar
    if not MINHA_CHAVE_API_GOOGLE:
        error_msg = "Chave de API do Google não encontrada. Verifique se o arquivo .env existe e contém a variável GOOGLE_API_KEY."
        logging.critical(error_msg)
        messagebox.showerror("Erro de Configuração", error_msg)
        sys.exit(1)

    try:
        database_setup.setup_database()
    except Exception as e:
        logging.critical("Falha CRÍTICA durante o setup do DB.", exc_info=True)
        messagebox.showerror("Erro Crítico de Inicialização", "Não foi possível configurar o banco de dados.")
        sys.exit(1)

    conn = None
    try:
        conn = sqlite3.connect(config.DB_PATH_CONFIG, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        logging.info("Conexão com o banco de dados estabelecida.")

        # --- Etapa 1: Instanciação dos Repositórios ---
        user_repo = UserRepository(conn)
        person_repo = PersonRepository(conn)
        org_repo = OrganizationRepository(conn)
        crm_repo = CrmRepository(conn)
        misc_repo = MiscRepository(conn)
        
        base_repos = {
            "user": user_repo,
            "person": person_repo,
            "organization": org_repo,
            "crm": crm_repo,
            "misc": misc_repo
        }
        
        # --- Etapa 2: Instanciação dos Serviços ---
        # A chave de API agora é lida de forma segura do ambiente
        geo_service = GeoService(conn, api_key=MINHA_CHAVE_API_GOOGLE)
        
        contact_service = ContactService(base_repos)
        report_service = ReportService(conn, person_repo, misc_repo)
        import_service = ImportService(conn, person_repo, misc_repo)

        # --- Etapa 3: Monta o dicionário final para a Aplicação ---
        repos = {
            **base_repos,
            "report": report_service,
            "import": import_service,
            "geo": geo_service,
            "contact": contact_service
        }

        saved_token = read_token_from_file()
        user = user_repo.verify_login_token(saved_token) if saved_token else None

        if user:
            logging.info(f"Login automático para {user.nome_usuario} bem-sucedido.")
            app = MainApplication(user=user, repos=repos)
            app.mainloop()
        else:
            logging.info("Nenhum token válido. Abrindo janela de login.")
            login_app = LoginWindow(user_repo=user_repo)
            login_app.mainloop()
        
    except Exception as e:
        logging.critical(f"Erro fatal na aplicação: {e}", exc_info=True)
        messagebox.showerror("Erro Fatal", f"Ocorreu um erro inesperado. Verifique 'app.log'.\n\nDetalhes: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Conexão com o banco de dados fechada no final do main.")