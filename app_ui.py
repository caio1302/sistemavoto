import tkinter as tk
from tkinter import messagebox
import webbrowser
import os
import sys
import logging
import customtkinter as ctk
from PIL import Image

import config
from popups.login_window import delete_token_file
from popups.info_windows import ChangelogWindow
from popups.dashboard_window import DashboardWindow
# --- MUDANÇAS DE IMPORT ---
from modules.person_form_window import PersonFormWindow
from modules.organization_form_window import OrganizationFormWindow # Adiciona a importação

from modules.contacts_view import ContactsView
from modules.dashboard_view import DashboardView
from modules.geolocalizacao_view import GeolocalizacaoView
from modules.cerimonial_view import CerimonialView
from modules.agenda_view import AgendaView
from modules.proposicoes_view import ProposicoesView
from modules.atendimentos_view import AtendimentosView
from modules.settings_view import SettingsView
from dto.pessoa import Pessoa

class StatusBarHandler(logging.Handler):
    # ... (código inalterado)
    def __init__(self, status_bar_label):
        super().__init__()
        self.status_bar_label = status_bar_label

    def emit(self, record):
        try:
            if self.status_bar_label and self.status_bar_label.winfo_exists():
                if record.levelno >= logging.INFO:
                    msg = record.getMessage()
                    self.status_bar_label.after(0, lambda: self.status_bar_label.configure(text=msg))
        except Exception:
            if self.status_bar_label:
                try:
                    logging.getLogger().removeHandler(self)
                except Exception:
                    pass
class MainApplication(ctk.CTk):
    def __init__(self, user, repos: dict):
        super().__init__()
        # ... (código do __init__ inalterado)
        self.logged_in_user = user
        self.repos = repos
        self.base_path = config.BASE_PATH

        self.title("e-Votos - Sistema de Gestão Política")
        self.geometry("1400x900") 
        self.minsize(1000, 600)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.protocol("WM_DELETE_WINDOW", self._on_close_main_window)
        self.bind("<Escape>", lambda e: self._on_close_main_window())
        
        self._current_module_frame = None
        self.status_bar_handler = None
        
        self.event_callbacks = {}
        self._register_events()

        self._configure_global_styles()
        self._build_main_interface()
        self._setup_status_bar_logging()

        self.after(100, lambda: self.dispatch("navigate", module_name="Painel"))
        self.after(200, lambda: self.state('zoomed'))


    def _register_events(self):
        # ... (código inalterado)
        self.register_event("navigate", self._handle_navigation)
        self.register_event("open_form", self._handle_open_form)
        self.register_event("open_dashboard", self.open_dashboard_window)
        self.register_event("data_changed", self.on_data_changed)


    def register_event(self, event_name, callback):
        # ... (código inalterado)
        if event_name not in self.event_callbacks:
            self.event_callbacks[event_name] = []
        self.event_callbacks[event_name].append(callback)


    def dispatch(self, event_name, **kwargs):
        # ... (código inalterado)
        if event_name in self.event_callbacks:
            for callback in self.event_callbacks[event_name]:
                callback(**kwargs)
        else:
            logging.warning(f"Evento não registrado: {event_name}")

    def on_data_changed(self, source="unknown", **kwargs):
        # ... (código inalterado)
        logging.info(f"Evento 'data_changed' recebido de '{source}'. Atualizando view atual...")
        if self._current_module_frame and hasattr(self._current_module_frame, 'on_data_updated'):
            self._current_module_frame.on_data_updated()


    def _handle_navigation(self, module_name: str):
        self._load_module(module_name)

    def _handle_open_form(self, form_name: str, **kwargs):
        parent_view = kwargs.get('parent_view', self)
        
        if form_name == "person":
            person_repo = self.repos.get("person")
            if not person_repo:
                logging.error("PersonRepository não encontrado.")
                return

            pessoa_dto = kwargs.get('pessoa_dto') 
            if isinstance(pessoa_dto, Pessoa):
                 pass
            elif 'candidatura_dto' in kwargs:
                candidatura = kwargs.get('candidatura_dto')
                pessoa_dto = candidatura.pessoa if candidatura else None
            elif "person_id" in kwargs:
                pessoa_dto = person_repo.get_person_details(kwargs["person_id"])
            else:
                pessoa_dto = None
            
            PersonFormWindow(parent_view, self.repos, self, pessoa_dto)
        
        # --- MUDANÇA PRINCIPAL AQUI ---
        elif form_name == "organization":
            org_repo = self.repos.get("organization")
            if not org_repo:
                logging.error("OrganizationRepository não encontrado.")
                return

            org_dto = None
            if "org_id" in kwargs:
                org_dto = org_repo.get_organization_details(kwargs["org_id"])
            
            # Chama o formulário correto
            OrganizationFormWindow(parent_view, self.repos, self, org_dto)
        
        else:
            logging.warning(f"Tentativa de abrir formulário desconhecido: {form_name}")

    # --- RESTANTE DO ARQUIVO PERMANECE INALTERADO ---
    def _setup_status_bar_logging(self):
        self.status_bar_handler = StatusBarHandler(self.status_bar_label)
        formatter = logging.Formatter('%(message)s')
        self.status_bar_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.status_bar_handler)

    def _configure_global_styles(self):
        self.font_normal = ctk.CTkFont(family=config.FONT_FAMILY, size=config.FONT_SIZE_NORMAL)
        self.font_bold = ctk.CTkFont(family=config.FONT_FAMILY, size=config.FONT_SIZE_BOLD, weight="bold")
        self.font_header = ctk.CTkFont(family=config.FONT_FAMILY, size=config.FONT_SIZE_HEADER, weight="bold")

    def _build_main_interface(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        logo_path = config.CUSTOM_LOGO_PATH if os.path.exists(config.CUSTOM_LOGO_PATH) else config.LOGO_PATH
        try:
            pil_image = Image.open(logo_path)
            ctk_logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(180, 35))
            self.sidebar_logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=ctk_logo_image)
            self.sidebar_logo_label.pack(pady=(20, 30), padx=20)
        except Exception as e:
            logging.error(f"Não foi possível carregar o logo: {e}", exc_info=True)
            self.sidebar_logo_label = ctk.CTkLabel(self.sidebar_frame, text="e-Votos", font=self.font_header)
            self.sidebar_logo_label.pack(pady=(20, 30))
        
        menu_items = ["Painel", "Contatos", "Atendimentos", "Proposições", "Agenda", "Cerimonial", "Geolocalização"]
        for item in menu_items:
            btn = ctk.CTkButton(self.sidebar_frame, text=item, fg_color="transparent", anchor="w", font=self.font_bold,
                                          command=lambda m=item: self.dispatch("navigate", module_name=m))
            btn.pack(fill=tk.X, pady=4, padx=20)
        
        self.settings_button = ctk.CTkButton(self.sidebar_frame, text="Configurações", fg_color="transparent", anchor="w",
                                                      command=lambda: self.dispatch("navigate", module_name="Configurações"), font=self.font_normal)
        self.settings_button.pack(side="bottom", fill="x", pady=2, padx=20)

        self.help_button = ctk.CTkButton(self.sidebar_frame, text="Central de Ajuda", fg_color="transparent", anchor="w",
                                                     command=self._show_help_popup, font=self.font_normal)
        self.help_button.pack(side="bottom", fill="x", pady=2, padx=20)

        self.logout_button = ctk.CTkButton(self.sidebar_frame, text="Sair / Logoff", fg_color="#D32F2F", hover_color="#B71C1C",
                                                    command=self._action_logoff, font=self.font_bold)
        self.logout_button.pack(side="bottom", fill="x", padx=10, pady=10)

        self.main_content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray14"))
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        
        self.status_bar_frame = ctk.CTkFrame(self, height=30, corner_radius=0, border_width=0)
        self.status_bar_frame.grid(row=1, column=1, sticky="ew")
        self.status_bar_frame.grid_propagate(False)
        self.status_bar_label = ctk.CTkLabel(self.status_bar_frame, text="Pronto.", anchor="w", font=self.font_normal)
        self.status_bar_label.pack(side="left", padx=10, pady=5, fill="both", expand=True)

    def _load_module(self, module_name: str):
        if self._current_module_frame:
            self._current_module_frame.destroy()
        view_map = {
            "Painel": DashboardView, "Contatos": ContactsView, "Atendimentos": AtendimentosView,
            "Proposições": ProposicoesView, "Agenda": AgendaView, "Cerimonial": CerimonialView,
            "Geolocalização": GeolocalizacaoView, "Configurações": SettingsView
        }
        view_class = view_map.get(module_name)
        if view_class:
            self._current_module_frame = view_class(self.main_content_frame, self.repos, self)
            self._current_module_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        else:
            self._current_module_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
            ctk.CTkLabel(self._current_module_frame, text=f"{module_name}", font=self.font_header).pack(pady=20)
            self._current_module_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


    def open_dashboard_window(self, cidade: str, ano: int):
        report_service = self.repos.get("report")
        if not report_service: return
        dashboard_data = report_service.get_eleitoral_dashboard_data(cidade, ano)
        if not dashboard_data or not dashboard_data.get("party_composition"):
            messagebox.showinfo("Dados Insuficientes", f"Não há dados para gerar o dashboard de {cidade} em {ano}.", parent=self)
            return
        DashboardWindow(self, cidade, ano, dashboard_data)

    def _action_logoff(self):
        if messagebox.askyesno("Logoff", "Deseja encerrar a sessão?"):
            user_repo = self.repos.get("user")
            delete_token_file()
            if self.logged_in_user and user_repo:
                user_repo._clear_token_for_user(self.logged_in_user)
            self.destroy()
            python = sys.executable
            os.execl(python, python, *sys.argv)

    def _on_close_main_window(self):
        if messagebox.askyesno("Sair", "Tem certeza que deseja fechar o sistema?"):
            self.destroy()

    def destroy(self):
        if self.status_bar_handler:
            logging.getLogger().removeHandler(self.status_bar_handler)
            self.status_bar_handler = None
        logging.info("Aplicação finalizada pelo usuário.")
        super().destroy()
        
    def _show_help_popup(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Ajuda e Informações do Sistema")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.after(100, lambda: dialog.focus_force())

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="e-Votos - Sistema de Gestão Política", font=self.font_bold).pack(anchor="w")
        ctk.CTkLabel(main_frame, text="Gestão de contatos, dados eleitorais e relatórios.", justify="left", font=self.font_normal).pack(anchor="w", pady=(0, 15))

        features_frame = ctk.CTkFrame(main_frame)
        features_frame.pack(fill="x", expand=True, pady=5)
        ctk.CTkLabel(features_frame, text="Use os botões na barra lateral para navegar entre os módulos principais do sistema.", justify="left", wraplength=500).pack(anchor="w")

        dev_info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        dev_info_frame.pack(fill='x', pady=(15, 0))
        ctk.CTkFrame(dev_info_frame, fg_color="gray50", height=1).pack(fill='x', expand=True, pady=(0, 10))
        ctk.CTkLabel(dev_info_frame, text="Desenvolvido por: Caio Lúcio", font=self.font_normal).pack(side="left")

        footer_buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        footer_buttons_frame.pack(fill='x', pady=(20, 0))
        ctk.CTkButton(footer_buttons_frame, text="OK", command=dialog.destroy, width=120).pack(side="right")
        ctk.CTkButton(footer_buttons_frame, text="Histórico de Atualizações", command=lambda: ChangelogWindow(dialog)).pack(side="right", padx=(0, 10))

    def update_status_bar(self, text, **kwargs):
        if self.status_bar_label and self.status_bar_label.winfo_exists():
            self.status_bar_label.configure(text=text, **kwargs)

    def _bind_tooltip(self, widget, tooltip_key: str, **kwargs):
        misc_repo = self.repos.get("misc")
        if not misc_repo:
            final_text = "Dica não disponível"
        else:
            final_text = misc_repo.get_ui_tags().get(tooltip_key, "Dica...")

        pronto_text = misc_repo.get_ui_tags().get("tooltip_pronto", "Pronto.") if misc_repo else "Pronto."

        widget.bind("<Enter>", lambda event, t=final_text: self.update_status_bar(t))
        widget.bind("<Leave>", lambda event, t=pronto_text: self.update_status_bar(t))