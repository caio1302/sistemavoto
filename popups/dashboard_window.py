import customtkinter as ctk
from tkinter import ttk
import matplotlib.pyplot as plt

from functions import ui_helpers
from dashboard import CityDashboard
from dto.pessoa import Pessoa

class DashboardWindow(ctk.CTkToplevel):
    def __init__(self, parent_app, cidade: str, ano: int, dashboard_data: dict):
        super().__init__(parent_app)
        self.parent_app_ref = parent_app
        
        # MODIFICADO: Busca a tag de título usando o MiscRepository
        title_prefix = "Dashboard Municipal" # Valor padrão
        misc_repo = self.parent_app_ref.repos.get("misc")
        if misc_repo:
            title_prefix = misc_repo.get_ui_tags().get("dashboard_window_title_prefix", "Dashboard Municipal")

        self.title(f"{title_prefix} - {cidade.title()} ({ano})")
        
        self.geometry("1200x650") 
        self.transient(parent_app)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        top_vereadores: list[Pessoa] = dashboard_data.get("top_vereadores", [])

        # O widget CityDashboard não precisa de 'repos', pois já recebe os dados processados
        self.dashboard_widget = CityDashboard(
            self, 
            party_data=dashboard_data.get("party_composition", []), 
            top_vereadores_data=top_vereadores
        )
        self.dashboard_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.after(50, lambda: ui_helpers.center_window(self))
        self.after(100, self.focus_force)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Garante que os recursos do Matplotlib sejam liberados ao fechar."""
        if hasattr(self, 'dashboard_widget') and hasattr(self.dashboard_widget, 'fig'):
            plt.close(self.dashboard_widget.fig)
        
        self.destroy()