import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
import webbrowser
import tempfile
import os
import logging
import threading

from canvas_report import CanvasReport
from report_generator import ReportGenerator
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura
from functions import data_helpers
import config

class CerimonialView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        
        self.report_html_generator = ReportGenerator(self.repos)

        self.anos_disponiveis = []
        self.cidades_disponiveis = []
        self.selected_ano = "2024"
        self.selected_cidade = None
        self.current_cerimonial_data = None
        self.is_loading = False
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._create_widgets()
        self._populate_anos()

    def _create_widgets(self):
        self.left_panel = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.left_panel.grid_propagate(False)       
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        
        self.left_panel.grid_rowconfigure(4, weight=1) 
        self.left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_panel, text="Filtros do Cerimonial", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.left_panel, text="Ano da Eleição:").grid(row=1, column=0, padx=10, pady=(10,0), sticky="w")
        self.ano_selector = ctk.CTkOptionMenu(self.left_panel, values=["Carregando..."], command=self.on_ano_selected)
        self.ano_selector.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.city_search_entry = ctk.CTkEntry(self.left_panel, placeholder_text="Buscar cidade...")
        self.city_search_entry.grid(row=3, column=0, padx=10, pady=(5, 0), sticky="ew")
        self.city_search_entry.bind("<KeyRelease>", self._filter_city_list)

        listbox_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        listbox_fg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        listbox_select_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        
        self.city_listbox = tk.Listbox(
            self.left_panel, font=('Calibri', 12), borderwidth=0, highlightthickness=0,
            bg=listbox_bg, fg=listbox_fg, selectbackground=listbox_select_bg,
            selectforeground=listbox_fg, activestyle='none'
        )
        self.city_listbox.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        self.city_listbox.bind("<<ListboxSelect>>", self.on_cidade_selected)
        
        self.print_button = ctk.CTkButton(self.left_panel, text="Imprimir relatório", command=self.generate_html_report, state="disabled")
        self.print_button.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        self.photo_loading_label = ctk.CTkLabel(self.left_panel, text="", text_color="gray")
        self.photo_loading_label.grid(row=6, column=0, padx=10, pady=(0,10), sticky="ew")

        self.right_panel = ctk.CTkFrame(self, fg_color=("gray85", "gray18"))
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=5)
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        report_canvas_container = ctk.CTkScrollableFrame(self.right_panel, label_text="", fg_color="transparent")
        report_canvas_container.pack(fill="both", expand=True)
        
        self.report_renderer = CanvasReport(report_canvas_container, self.repos, self.app)

    def _apply_appearance_mode(self, color_tuple):
        return color_tuple[1] if ctk.get_appearance_mode() == "Dark" else color_tuple[0]
        
    def _filter_city_list(self, event=None):
        search_term = self.city_search_entry.get().lower()
        self.city_listbox.delete(0, tk.END)
        filtered_cities = [city for city in self.cidades_disponiveis if search_term in city.lower()]
        for city in filtered_cities:
            self.city_listbox.insert(tk.END, city)

    def _populate_anos(self):
        misc_repo = self.repos.get("misc")
        if not misc_repo: return
        self.anos_disponiveis = misc_repo.get_anos_de_eleicao()
        if self.anos_disponiveis:
            self.ano_selector.configure(values=self.anos_disponiveis)
            self.ano_selector.set(self.anos_disponiveis[0])
            self.on_ano_selected(self.anos_disponiveis[0])
        else:
            self.ano_selector.configure(values=["Nenhum dado"], state="disabled")

    def on_ano_selected(self, selected_ano):
        self.selected_ano = int(selected_ano)
        misc_repo = self.repos.get("misc")
        if not misc_repo: return
        self.cidades_disponiveis = misc_repo.get_cidades_por_ano(self.selected_ano)
        self.print_button.configure(state="disabled")
        self._filter_city_list()
        self._load_last_city()
    
    def on_cidade_selected(self, event=None):
        if self.is_loading: return
        selection_indices = self.city_listbox.curselection()
        if not selection_indices: return
        
        self.is_loading = True
        self.selected_cidade = self.city_listbox.get(selection_indices[0])
        
        try:
            with open(config.LAST_CITY_PATH, 'w') as f: f.write(self.selected_cidade)
        except Exception as e: logging.warning(f"Não foi possível salvar a última cidade: {e}")

        self.photo_loading_label.configure(text="Carregando dados...")
        self.update_idletasks()
        
        report_service = self.repos.get("report")
        if not report_service: self.is_loading = False; return

        self.current_cerimonial_data = report_service.get_cerimonial_data(self.selected_cidade, self.selected_ano)
        
        if not self.current_cerimonial_data:
            messagebox.showerror("Erro", "Não foi possível carregar os dados para este cerimonial.")
            self.photo_loading_label.configure(text="")
            self.is_loading = False
            return
            
        # +++ ADIÇÃO DE LOG PARA DEBUG +++
        logging.debug(f"Dados do cerimonial para {self.selected_cidade}: {self.current_cerimonial_data}")
        destaque = self.current_cerimonial_data.get('candidato_destaque')
        if destaque:
            logging.debug(f"Objeto Candidato Destaque: {destaque}")

        self.report_renderer.display(
            cidade=self.selected_cidade, ano_eleicao=self.selected_ano,
            prefeito=self.current_cerimonial_data.get("prefeito"),
            vice=self.current_cerimonial_data.get("vice"),
            vereadores=self.current_cerimonial_data.get("vereadores", []),
            ranking_2022=self.current_cerimonial_data.get("ranking_2022", {}),
            candidato_destaque=destaque,
            city_data_completo=self.current_cerimonial_data
        )
        self.print_button.configure(state="normal")
        
        pessoas_para_cache = []
        candidaturas_completas = []
        if self.current_cerimonial_data.get("prefeito"): candidaturas_completas.append(self.current_cerimonial_data.get("prefeito"))
        if self.current_cerimonial_data.get("vice"): candidaturas_completas.append(self.current_cerimonial_data.get("vice"))
        if self.current_cerimonial_data.get("vereadores"): candidaturas_completas.extend(self.current_cerimonial_data.get("vereadores"))
        for ranking in self.current_cerimonial_data.get("ranking_2022", {}).values():
            candidaturas_completas.extend(ranking)
        
        for cand in candidaturas_completas:
            if cand and isinstance(cand, Candidatura) and cand.pessoa:
                pessoas_para_cache.append(cand.pessoa)

        if destaque and isinstance(destaque, Pessoa):
            pessoas_para_cache.append(destaque)
        
        if pessoas_para_cache:
            threading.Thread(target=self._precache_photos, args=(pessoas_para_cache,), daemon=True).start()
        else:
            self.photo_loading_label.configure(text="")
            self.is_loading = False

    def _precache_photos(self, pessoas: list[Pessoa]):
        self.photo_loading_label.configure(text="Atualizando fotos...")
        for p in pessoas:
            data_helpers.get_candidate_photo_path(p, self.repos)
        self.after(100, self._on_precache_finished)
        
    def _on_precache_finished(self):
        if self.current_cerimonial_data and self.winfo_exists():
            self.report_renderer.display(
                cidade=self.selected_cidade, ano_eleicao=self.selected_ano,
                prefeito=self.current_cerimonial_data.get("prefeito"), 
                vice=self.current_cerimonial_data.get("vice"),
                vereadores=self.current_cerimonial_data.get("vereadores", []), 
                ranking_2022=self.current_cerimonial_data.get("ranking_2022", {}),
                candidato_destaque=self.current_cerimonial_data.get("candidato_destaque"),
                city_data_completo=self.current_cerimonial_data
            )
        self.photo_loading_label.configure(text="")
        self.is_loading = False

    def _load_last_city(self):
        try:
            if os.path.exists(config.LAST_CITY_PATH):
                with open(config.LAST_CITY_PATH, 'r') as f:
                    last_city = f.read().strip()
                if last_city in self.cidades_disponiveis:
                    idx = self.cidades_disponiveis.index(last_city)
                    self.city_listbox.selection_set(idx)
                    self.city_listbox.see(idx)
                    self.on_cidade_selected()
        except Exception as e:
            # +++ MUDANÇA NO LOG: EXIBIR O ERRO COMPLETO +++
            logging.error(f"Erro detalhado ao carregar última cidade:", exc_info=True)

    def generate_html_report(self):
        if not self.selected_cidade or not self.selected_ano: return
        report_service = self.repos.get("report")
        if not report_service: return

        self.print_button.configure(state="disabled", text="Gerando...")
        self.update_idletasks()
        
        report_data = self.current_cerimonial_data
        report_data_for_html = {
            "cidade": self.selected_cidade, "ano_eleicao": self.selected_ano, "ano_eleicao_municipal": self.selected_ano,
            "prefeito": report_data.get("prefeito"), "vice_prefeito": report_data.get("vice"),
            "vereadores": report_data.get("vereadores", []), "prefeitura_data": report_data.get("prefeitura", {}),
            "candidato_destaque": report_data.get("candidato_destaque"),
            "rankings": report_data.get("ranking_2022")
        }
        
        html_content = self.report_html_generator.generate_html(report_data_for_html)
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding='utf-8') as f:
                f.write(html_content)
                filepath = f.name
            webbrowser.open(f"file://{os.path.realpath(filepath)}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar ou abrir o arquivo HTML.\n\nDetalhe: {e}")
        
        self.print_button.configure(state="normal", text="Imprimir relatório")