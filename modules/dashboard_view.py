import customtkinter as ctk
from datetime import datetime
import threading
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np # Importa o numpy para o novo gráfico

# Importa as janelas e funções necessárias
from modules.evento_form_window import EventoFormWindow
from modules.atendimento_form_window import AtendimentoFormWindow
from popups.birthday_windows import UpcomingBirthdaysWindow
from popups.helpers import format_date_with_weekday_robust


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app, initial_filters=None):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        self.accent_color = "#00A9E0"

        # Configuração da grelha principal
        self.grid_rowconfigure(2, weight=1) # Linha 2 (conteúdo principal) expande
        self.grid_columnconfigure(0, weight=3) # Coluna principal (esquerda) é mais larga
        self.grid_columnconfigure(1, weight=1) # Coluna lateral (direita) é mais estreita
        
        self.fig = None # Para a limpeza de recursos
        
        self._create_layout()
        self.after(50, self.refresh_all_data)

    def _create_layout(self):
        # --- LINHA 0: Painel de Boas-Vindas ---
        self._create_welcome_card(row=0, col=0, colspan=2)
        
        # --- LINHA 1: KPIs e Acesso Rápido (alinhados) ---
        self._create_top_row_frame(row=1, col=0, colspan=2)

        # --- LINHA 2: Conteúdo Principal ---
        # Frame para a coluna principal (esquerda)
        main_column_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_column_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        main_column_frame.grid_rowconfigure(0, weight=1) # Gráfico
        main_column_frame.grid_rowconfigure(1, weight=1) # Aniversariantes
        main_column_frame.grid_columnconfigure(0, weight=1)
        
        self._create_chart_card("Candidatos por Cargo e Ano", main_column_frame, row=0, col=0)
        self.birthday_card = self._create_birthday_card(main_column_frame, "Aniversariantes da Semana", row=1, col=0)
        
        # Frame para a coluna lateral (direita)
        right_column_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_column_frame.grid(row=2, column=1, sticky="nsew", padx=(0, 10), pady=10)
        right_column_frame.grid_rowconfigure((0, 1), weight=1)
        right_column_frame.grid_columnconfigure(0, weight=1)
        
        self.agenda_card = self._create_list_card(right_column_frame, "Agenda do Dia", row=0, col=0)
        self.atendimentos_card = self._create_list_card(right_column_frame, "Atendimentos Urgentes", row=1, col=0)
        
    # --- MÉTODOS DE CRIAÇÃO DE WIDGETS ---

    def _create_welcome_card(self, row, col, colspan):
        card = ctk.CTkFrame(self, fg_color="transparent")
        card.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=10, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        user_name = self.app.logged_in_user.nome_completo or self.app.logged_in_user.nome_usuario
        ctk.CTkLabel(card, text=f"Bem-vindo, {user_name.split(' ')[0]}!", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w")
        self.time_label = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14))
        self.time_label.grid(row=0, column=1, sticky="e")
        self._update_time()

    def _update_time(self):
        dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        now = datetime.now()
        dia_semana = dias[now.weekday()]
        mes_ano = meses[now.month - 1]
        time_str = now.strftime(f"{dia_semana}, %d de {mes_ano} de %Y | %H:%M:%S")
        self.time_label.configure(text=time_str)
        self.after(1000, self._update_time)

    def _create_top_row_frame(self, row, col, colspan):
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=10, pady=10)
        top_frame.grid_columnconfigure(0, weight=1)

        # KPIs
        kpi_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        kpi_frame.pack(fill="x", expand=True)
        kpi_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.card_pessoas = self._create_kpi_card(kpi_frame, "Total de Pessoas", "...", 0)
        self.card_proposicoes = self._create_kpi_card(kpi_frame, "Proposições no Ano", "...", 1)
        self.card_votos_sim = self._create_kpi_card(kpi_frame, "Votos 'Sim'", "...", 2)
        
        # Acesso Rápido
        actions_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        actions_frame.pack(fill="x", expand=True, pady=(10,0))
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(actions_frame, text="Novo Contato", height=40, command=lambda: self.app.dispatch("open_form", form_name="person")).grid(row=0, column=0, padx=(0,5), sticky="ew")
        ctk.CTkButton(actions_frame, text="Novo Atendimento", height=40, command=lambda: self.app.dispatch("navigate", module_name="Atendimentos")).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(actions_frame, text="Acessar Mapa Geo", height=40, command=lambda: self.app.dispatch("navigate", module_name="Geolocalização")).grid(row=0, column=2, padx=(5,0), sticky="ew")

    def _create_kpi_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=10, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13)).pack(pady=(10, 2), padx=10)
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=self.accent_color)
        value_label.pack(pady=(0, 10), padx=10)
        card.value_label = value_label
        return card

    def _create_list_card(self, parent, title, row, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, sticky="nsew", pady=10)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        content_frame = ctk.CTkScrollableFrame(card, label_text="", fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        card.content_frame = content_frame
        return card
        
    def _create_birthday_card(self, parent, title, row, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, sticky="nsew", pady=10)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(title_frame, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(title_frame, text="Ver todos", height=25, width=80, 
                      command=lambda: UpcomingBirthdaysWindow(self.app, self.repos)).pack(side="right")
                      
        content_frame = ctk.CTkScrollableFrame(card, label_text="", fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        card.content_frame = content_frame
        return card

    def _create_chart_card(self, title, parent, row, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, sticky="nsew", pady=(0,10))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.chart_frame = ctk.CTkFrame(card, fg_color=("gray85", "gray18"))
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))

    # --- MÉTODOS DE ATUALIZAÇÃO DE DADOS ---
    
    def on_data_updated(self):
        self.refresh_all_data()

    def refresh_all_data(self):
        threading.Thread(target=self._fetch_and_populate_data, daemon=True).start()

    def _fetch_and_populate_data(self):
        report_service = self.repos.get("report")
        if not report_service: return
        stats = report_service.get_dashboard_stats()
        def update_ui():
            if not self.winfo_exists(): return
            self.card_pessoas.value_label.configure(text=str(stats.get('total_pessoas', 0)))
            self.card_proposicoes.value_label.configure(text=str(stats.get('total_proposicoes_ano', 0)))
            self.card_votos_sim.value_label.configure(text=str(stats.get('votos_sim', 0)))
            self._populate_agenda_card()
            self._populate_atendimentos_card()
            self._populate_birthday_card()
            self._populate_chart_card()
        self.after(0, update_ui)

    def _populate_atendimentos_card(self):
        content_frame = self.atendimentos_card.content_frame
        for widget in content_frame.winfo_children(): widget.destroy()
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        urgent_atendimentos = crm_repo.get_urgent_atendimentos(limit=5)
        if not urgent_atendimentos:
            ctk.CTkLabel(content_frame, text="Nenhum atendimento urgente.").pack(expand=True, padx=5, pady=10)
            return
        priority_colors = {"Urgente": "#D32F2F", "Alta": "#F57C00"}
        for atendimento in urgent_atendimentos:
            atendimento_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            atendimento_frame.pack(fill="x", pady=3, padx=5)
            atendimento_frame.grid_columnconfigure(1, weight=1)
            prioridade = atendimento.get('prioridade', 'Normal')
            color = priority_colors.get(prioridade, ctk.ThemeManager.theme["CTkLabel"]["text_color"])
            prio_label = ctk.CTkLabel(atendimento_frame, text=prioridade.upper(), font=ctk.CTkFont(size=10, weight="bold"), width=10, text_color=color)
            prio_label.grid(row=0, column=0, padx=(0,10), sticky="n")
            display_text = f"{atendimento['titulo']}\n(Solicitante: {atendimento['nome_solicitante'] or 'N/A'})"
            btn = ctk.CTkButton(atendimento_frame, text=display_text, anchor="w", fg_color="transparent",
                                command=lambda a_id=atendimento['id_atendimento']: AtendimentoFormWindow(self, self.repos, self.app, atendimento_id=a_id))
            btn.grid(row=0, column=1, sticky="ew")

    def _populate_birthday_card(self):
        content_frame = self.birthday_card.content_frame
        for widget in content_frame.winfo_children(): widget.destroy()

        report_service = self.repos.get("report")
        if not report_service: return

        # Busca aniversariantes (prefeitos e vereadores) da próxima semana
        upcoming_birthdays = report_service.get_upcoming_birthdays(days=7, roles=['PREFEITO'])

        if not upcoming_birthdays:
            ctk.CTkLabel(content_frame, text="Nenhum aniversariante na próxima semana.").pack(expand=True, padx=5, pady=10)
            return

        last_date_header = None
        for bday_date, candidatura in upcoming_birthdays:
            # Formata a data para "DD de Mês (DiaDaSemana)"
            date_str_display = format_date_with_weekday_robust(bday_date)
                            
            # Se a data mudou, cria um novo cabeçalho
            if date_str_display != last_date_header:
                last_date_header = date_str_display
                ctk.CTkLabel(content_frame, text=date_str_display, font=ctk.CTkFont(weight="bold", underline=True)).pack(anchor="w", pady=(8,2), padx=5)

            pessoa = candidatura.pessoa

            # Cria um frame para cada aniversariante para melhor alinhamento
            person_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            person_frame.pack(fill="x", pady=0, padx=15)
            person_frame.grid_columnconfigure(1, weight=1)

            bday_str_ddmm = bday_date.strftime("%d/%m")
            ctk.CTkLabel(person_frame, text=bday_str_ddmm, font=ctk.CTkFont(size=12, weight="bold"), width=50).grid(row=0, column=0, padx=(0,10))

            btn = ctk.CTkButton(person_frame, text=pessoa.nome, anchor="w", fg_color="transparent",
                                command=lambda p_id=pessoa.id_pessoa: self.app.dispatch("open_form", form_name="person", person_id=p_id, parent_view=self))
            btn.grid(row=0, column=1, sticky="ew")  

    def _populate_agenda_card(self):
        # Implementação similar aos outros...
        content_frame = self.agenda_card.content_frame
        for widget in content_frame.winfo_children(): widget.destroy()
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        today_events = crm_repo.get_events_for_day(datetime.now().date())
        if not today_events:
            ctk.CTkLabel(content_frame, text="Nenhum compromisso para hoje.").pack(expand=True, padx=5, pady=10)
            return
        for evento in today_events:
            btn = ctk.CTkButton(content_frame, text=f"• {evento['titulo']}", anchor="w", fg_color="transparent",
                                command=lambda e_id=evento['id_evento']: EventoFormWindow(self, self.repos, self.app, evento_id=e_id))
            btn.pack(fill="x", padx=5)

    def _populate_chart_card(self):
        report_service = self.repos.get("report")
        if not report_service or not hasattr(self, 'chart_frame') or not self.chart_frame.winfo_exists(): return
        for widget in self.chart_frame.winfo_children(): widget.destroy()
        
        data = report_service.get_candidate_count_by_role_year()
        if not data:
            ctk.CTkLabel(self.chart_frame, text="Não há dados de candidaturas.").pack(expand=True)
            return

        self.anos = sorted(list(set(d['ano_eleicao'] for d in data)), reverse=True)
        self.cargos = sorted(list(set(d['cargo'] for d in data)))
        
        counts = {cargo: [next((item['contagem'] for item in data if item['ano_eleicao'] == ano and item['cargo'] == cargo), 0) for ano in self.anos] for cargo in self.cargos}

        x = np.arange(len(self.anos))
        width = 0.15
        
        self.update_idletasks()
        is_dark = ctk.get_appearance_mode() == "Dark"
        theme_index = 1 if is_dark else 0
        bg_rgb_16bit = self.winfo_rgb(self.chart_frame.cget("fg_color")[theme_index])
        bg_color_hex = f'#{(bg_rgb_16bit[0]>>8):02x}{(bg_rgb_16bit[1]>>8):02x}{(bg_rgb_16bit[2]>>8):02x}'
        text_rgb_16bit = self.winfo_rgb(ctk.ThemeManager.theme["CTkLabel"]["text_color"][theme_index])
        text_color_hex = f'#{(text_rgb_16bit[0]>>8):02x}{(text_rgb_16bit[1]>>8):02x}{(text_rgb_16bit[2]>>8):02x}'
        
        plt.style.use('dark_background' if is_dark else 'seaborn-v0_8-whitegrid')
        self.fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor(bg_color_hex)
        ax.set_facecolor(bg_color_hex)

        self.bars_map = {} # Dicionário para mapear barras a dados
        for i, cargo in enumerate(self.cargos):
            offset = (i - (len(self.cargos) - 1) / 2) * width
            rects = ax.bar(x + offset, counts[cargo], width, label=cargo)
            
            # --- MUDANÇA PARA INTERATIVIDADE ---
            # Ativa a "seleção" para cada barra e guarda os seus dados
            for rect_index, rect in enumerate(rects):
                rect.set_picker(5) # 5 é a tolerância do clique em pixels
                self.bars_map[rect] = {"ano": self.anos[rect_index], "cargo": cargo}
        
        ax.set_ylabel('Nº de Candidatos', color=text_color_hex, fontsize=9)
        ax.set_xticks(x, self.anos)
        ax.legend(fontsize=8)
        ax.tick_params(axis='y', colors=text_color_hex, labelsize=8)
        ax.tick_params(axis='x', colors=text_color_hex, labelsize=8)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(text_color_hex); ax.spines['bottom'].set_color(text_color_hex)

        self.fig.tight_layout(pad=0.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        
        # --- MUDANÇA PARA INTERATIVIDADE ---
        # Conecta o evento de clique no gráfico à nossa nova função
        self.canvas.mpl_connect('pick_event', self._on_chart_pick)

        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _on_chart_pick(self, event):
        """Esta função é chamada quando uma barra do gráfico é clicada."""
        # O 'artist' é o objeto que foi clicado (a nossa barra)
        bar = event.artist
        
        # Procura os dados associados a esta barra no nosso mapa
        bar_data = self.bars_map.get(bar)
        
        if bar_data:
            ano = bar_data['ano']
            cargo = bar_data['cargo']
            logging.info(f"Clique no gráfico detectado. Navegando para Contatos com filtro: Ano={ano}, Cargo={cargo}")
            
            # Prepara os filtros para enviar para a tela de contatos
            filtros = {
                "ano_eleicao": ano,
                "cargo": cargo
            }
            
            # Usa o sistema de eventos para navegar e passar os filtros
            # (Isto ainda vai precisar que a tela de Contatos seja ajustada para receber os filtros)
            self.app.dispatch("navigate_with_filter", module_name="Contatos", initial_filters=filtros)
            
            # Mostra uma mensagem temporária na barra de status
            self.app.update_status_bar(f"Filtrando por: {cargo} de {ano}...")
        else:
            logging.warning("Clique no gráfico não mapeado para dados.")

    # def _populate_chart_card(self):
    #     # --- MÉTODO COMPLETAMENTE NOVO PARA O GRÁFICO DE CANDIDATOS ---
    #     report_service = self.repos.get("report")
    #     if not report_service or not hasattr(self, 'chart_frame') or not self.chart_frame.winfo_exists(): return
    #     for widget in self.chart_frame.winfo_children(): widget.destroy()
        
    #     data = report_service.get_candidate_count_by_role_year()
    #     if not data:
    #         ctk.CTkLabel(self.chart_frame, text="Não há dados de candidaturas.").pack(expand=True)
    #         return

    #     # Processa os dados para o formato do gráfico
    #     anos = sorted(list(set(d['ano_eleicao'] for d in data)), reverse=True)
    #     cargos = sorted(list(set(d['cargo'] for d in data)))
        
    #     counts = {cargo: [next((item['contagem'] for item in data if item['ano_eleicao'] == ano and item['cargo'] == cargo), 0) for ano in anos] for cargo in cargos}

    #     x = np.arange(len(anos))
    #     width = 0.15 # Largura de cada barra
        
    #     self.update_idletasks()
    #     is_dark = ctk.get_appearance_mode() == "Dark"
    #     theme_index = 1 if is_dark else 0
    #     bg_rgb_16bit = self.winfo_rgb(self.chart_frame.cget("fg_color")[theme_index])
    #     bg_color_hex = f'#{(bg_rgb_16bit[0]>>8):02x}{(bg_rgb_16bit[1]>>8):02x}{(bg_rgb_16bit[2]>>8):02x}'
    #     text_rgb_16bit = self.winfo_rgb(ctk.ThemeManager.theme["CTkLabel"]["text_color"][theme_index])
    #     text_color_hex = f'#{(text_rgb_16bit[0]>>8):02x}{(text_rgb_16bit[1]>>8):02x}{(text_rgb_16bit[2]>>8):02x}'
        
    #     plt.style.use('dark_background' if is_dark else 'seaborn-v0_8-whitegrid')
    #     self.fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
    #     self.fig.patch.set_facecolor(bg_color_hex)
    #     ax.set_facecolor(bg_color_hex)

    #     # Cria as barras agrupadas
    #     for i, cargo in enumerate(cargos):
    #         offset = (i - (len(cargos) - 1) / 2) * width
    #         rects = ax.bar(x + offset, counts[cargo], width, label=cargo)
    #         ax.bar_label(rects, padding=3, fontsize=7, color=text_color_hex)

    #     ax.set_ylabel('Nº de Candidatos', color=text_color_hex, fontsize=9)
    #     ax.set_xticks(x, anos)
    #     ax.legend(fontsize=8)
    #     ax.tick_params(axis='y', colors=text_color_hex, labelsize=8)
    #     ax.tick_params(axis='x', colors=text_color_hex, labelsize=8)
    #     ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    #     ax.spines['left'].set_color(text_color_hex); ax.spines['bottom'].set_color(text_color_hex)

    #     self.fig.tight_layout(pad=0.5)
    #     self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
    #     self.canvas.draw()
    #     self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
    
    def cleanup(self):
        if hasattr(self, 'fig') and self.fig:
            plt.close(self.fig)
        if hasattr(self, 'canvas') and self.canvas and self.canvas.get_tk_widget().winfo_exists():
            self.canvas.get_tk_widget().destroy()