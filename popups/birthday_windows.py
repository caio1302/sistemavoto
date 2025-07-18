import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
import threading

from functions import ui_helpers
# MUDANÇA: Importa os DTOs para checagem de tipo e acesso correto
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura
from .helpers import format_date_with_weekday_robust

class UpcomingBirthdaysWindow(ctk.CTkToplevel):
    def __init__(self, parent_app, repos: dict, days: int = 7):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.repos = repos
        self.days_to_show = days
        
        self.title("Próximos Aniversariantes (Eleitos)")
        self.geometry("1200x700") 
        self.transient(parent_app)
        self.grab_set()
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        ui_helpers.center_window(self)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self._create_filters()

        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._create_treeview(tree_frame)
        
        ctk.CTkButton(self, text="Fechar", command=self.destroy, width=150).grid(row=2, column=0, pady=(5, 10))
        
        self.loading_label = ctk.CTkLabel(self, text="Filtrando...", font=ctk.CTkFont(size=14))
        
        self.refresh_list()

    def _create_filters(self):
        ctk.CTkLabel(self.filter_frame, text="Filtrar por Cargo:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 15))
        
        self.filter_vars = {
            "PREFEITO": ctk.BooleanVar(value=True),
            "VEREADOR": ctk.BooleanVar(value=False),
            "DEPUTADO FEDERAL": ctk.BooleanVar(value=False),
            "DEPUTADO ESTADUAL": ctk.BooleanVar(value=False)
        }
        
        role_map = {
            "PREFEITO": "Prefeitos", "VEREADOR": "Vereadores",
            "DEPUTADO FEDERAL": "Dep. Federal", "DEPUTADO ESTADUAL": "Dep. Estadual"
        }
        
        for role_key, role_text in role_map.items():
            cb = ctk.CTkCheckBox(self.filter_frame, text=role_text, variable=self.filter_vars[role_key], 
                                 command=self.refresh_list)
            cb.pack(side="left", padx=10)

    def refresh_list(self):
        selected_roles = [role for role, var in self.filter_vars.items() if var.get()]
        
        if not selected_roles:
            self.populate_tree([])
            return

        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()

        def fetch_and_populate():
            report_service = self.repos.get("report")
            if not report_service:
                if self.winfo_exists(): self.after(0, self.populate_tree, [])
                return

            data = report_service.get_upcoming_birthdays(days=self.days_to_show, roles=selected_roles)
            if self.winfo_exists():
                self.after(0, self.populate_tree, data)

        threading.Thread(target=fetch_and_populate, daemon=True).start()

    def _create_treeview(self, parent):
        self.columns = ("Nome", "Apelido", "Cargo", "Partido", "Votos", "Cidade")
        self.tree = ttk.Treeview(parent, columns=self.columns, show="tree headings")
        
        self._style_treeview()
        
        self.tree.heading('#0', text='Data')
        self.tree.column('#0', width=180, stretch=False, anchor='w')

        col_configs = {
            "Nome":    {'width': 250, 'stretch': True},
            "Apelido": {'width': 180, 'stretch': True},
            "Cargo":   {'width': 160, 'stretch': False},
            "Partido": {'width': 80,  'stretch': False},
            "Votos":   {'width': 90,  'stretch': False},
            "Cidade":  {'width': 160, 'stretch': False}
        }
        
        for col in self.columns:
            config = col_configs.get(col, {})
            self.tree.heading(col, text=col)
            self.tree.column(col, width=config.get('width', 120), anchor='w', stretch=config.get('stretch', False))

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self._on_item_double_click)

    def populate_tree(self, birthdays_data_list):
        self.loading_label.place_forget()
        for item in self.tree.get_children(): self.tree.delete(item)

        if not birthdays_data_list:
            self.tree.insert("", "end", text="Nenhum aniversariante encontrado para os filtros selecionados.")
            return

        last_date_header = None
        # MUDANÇA: A lista agora contém tuplas (datetime, Candidatura)
        for date_obj, candidatura_obj in birthdays_data_list:
            date_str = format_date_with_weekday_robust(date_obj)
            
            # Extrai o objeto Pessoa para facilitar o acesso
            pessoa_obj = candidatura_obj.pessoa
            
            if date_str != last_date_header:
                self.tree.insert("", "end", iid=date_str, text=date_str, tags=('date_header',), open=True)
                last_date_header = date_str

            votos_str = f"{candidatura_obj.votos:,}".replace(",", ".") if candidatura_obj.votos else "0"
            
            # --- CORREÇÃO AQUI ---
            # Acessa os dados corretamente do objeto 'candidatura' e 'pessoa'
            values = (
                pessoa_obj.nome, 
                pessoa_obj.apelido or "",
                candidatura_obj.cargo or "Não se aplica", 
                candidatura_obj.partido or "S/P",
                votos_str, 
                candidatura_obj.cidade or "N/A"
            )
            # Usa o id da PESSOA para o IID, pois é o que o formulário espera
            self.tree.insert(date_str, "end", iid=pessoa_obj.id_pessoa, values=values, text="")

    def _on_item_double_click(self, event=None):
        selected_item_iid = self.tree.focus()
        if not selected_item_iid or not selected_item_iid.isdigit(): return
        person_id = int(selected_item_iid)
        
        self.parent_app.dispatch("open_form", form_name="person", person_id=person_id, parent_view=self)

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
                        relief="flat", font=ctk.CTkFont(size=13, weight="bold")) # Aumentei a fonte do header
        style.map("Custom.Treeview.Heading", relief=[('active','flat'), ('pressed','flat')])

        header_row_color = "gray80" if ctk.get_appearance_mode() == "Light" else "gray25"
        self.tree.tag_configure('date_header', background=header_row_color, font=ctk.CTkFont(size=13, weight="bold"))

    def _apply_appearance_mode(self, color_tuple):
        return color_tuple[1] if ctk.get_appearance_mode() == "Dark" else color_tuple[0]