import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import threading
import logging

from modules.evento_form_window import EventoFormWindow
from modules.atendimento_form_window import AtendimentoFormWindow
from popups.birthday_windows import UpcomingBirthdaysWindow
from popups.helpers import format_date_with_weekday_robust
# MUDANÇA: Precisamos importar os DTOs para checagem de tipo e acesso correto
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")
        
        self._create_layout()
        self.refresh_all_data()

    def on_data_updated(self):
        logging.info("DashboardView: Atualizando dados devido ao evento 'data_changed'.")
        self.refresh_all_data()

    def refresh_all_data(self):
        self._load_stats()
        self._populate_feed_card()
        self._populate_agenda_card()
        self.refresh_atendimentos_list()
        self._populate_birthday_card()

    def _create_layout(self):
        period_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        period_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkLabel(period_frame, text="Período:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        period_selector = ctk.CTkSegmentedButton(period_frame, values=["Hoje", "Últimos 7 Dias", "Este Mês", "Este Ano"])
        period_selector.set("Este Mês")
        period_selector.pack(side="left", padx=10)

        self._create_and_populate_kpi_cards(self.scrollable_frame, row=1)
        self._create_chart_card(self.scrollable_frame, "Novos Contatos por Mês", row=2, col=0, colspan=2)
        
        self.feed_card, self.feed_content_frame = self._create_feed_card(self.scrollable_frame, "Feed de Atividades Recentes", row=2, col=2, rowspan=2)
        self.agenda_card = self._create_list_card(self.scrollable_frame, "Minha Agenda do Dia", row=3, col=0)
        self.atendimentos_card = self._create_list_card(self.scrollable_frame, "Atendimentos Urgentes", row=3, col=1)
        self.birthday_card = self._create_birthday_card(self.scrollable_frame, "Aniversariantes da Semana", row=4, col=0)
        
        self._create_quick_actions_card(self.scrollable_frame, "Acesso Rápido", row=4, col=1)
        self._create_map_card(self.scrollable_frame, "Mapa de Contatos", row=4, col=2, colspan=1)

    def _create_card_base(self, parent, title, row, col, rowspan=1, colspan=1):
        card = ctk.CTkFrame(parent, border_width=1)
        card.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, padx=10, pady=10, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        ctk.CTkLabel(title_frame, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        return card, title_frame

    def _create_kpi_card(self, parent, title, value, col):
        card, _ = self._create_card_base(parent, title, row=0, col=col)
        card.grid_rowconfigure(1, weight=1)
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=36, weight="bold"))
        value_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 15))
        card.value_label = value_label
        return card

    def _create_and_populate_kpi_cards(self, parent, row):
        kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.card_pessoas = self._create_kpi_card(kpi_frame, "Total de Pessoas", "...", 0)
        self.card_atendimentos = self._create_kpi_card(kpi_frame, "Atendimentos Pendentes", "...", 1)
        self.card_proposicoes = self._create_kpi_card(kpi_frame, "Proposições no Ano", "...", 2)
        self.card_votos_sim = self._create_kpi_card(kpi_frame, "Votos 'Sim'", "...", 3)
        
    def _create_chart_card(self, parent, title, row, col, colspan):
        card, _ = self._create_card_base(parent, title, row, col, colspan=colspan)
        card.grid_rowconfigure(1, weight=1)
        chart_placeholder = ctk.CTkFrame(card, fg_color=("gray75", "gray25"))
        chart_placeholder.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))
        ctk.CTkLabel(chart_placeholder, text="Gráfico em desenvolvimento...").pack(expand=True)
        return card

    def _create_feed_card(self, parent, title, row, col, rowspan):
        card, _ = self._create_card_base(parent, title, row, col, rowspan=rowspan)
        card.grid_rowconfigure(1, weight=1)
        feed_content = ctk.CTkScrollableFrame(card, label_text="")
        feed_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))
        return card, feed_content

    def _create_list_card(self, parent, title, row, col):
        card, _ = self._create_card_base(parent, title, row, col)
        card.grid_rowconfigure(1, weight=1)
        content_frame = ctk.CTkScrollableFrame(card, label_text="", fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        card.content_frame = content_frame 
        return card
        
    def _create_birthday_card(self, parent, title, row, col):
        card, title_frame = self._create_card_base(parent, title, row, col)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkButton(title_frame, text="Ver todos", height=25, width=80, 
                      command=self._open_all_birthdays_window).pack(side="right")
        content_frame = ctk.CTkScrollableFrame(card, label_text="", fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        card.content_frame = content_frame
        return card
        
    def _create_quick_actions_card(self, parent, title, row, col):
        card, _ = self._create_card_base(parent, title, row, col)
        button_frame = ctk.CTkFrame(card, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(button_frame, text="Novo Contato", command=lambda: self.app.dispatch("open_form", form_name="person")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(button_frame, text="Novo Atendimento", command=lambda: self.app.dispatch("navigate", module_name="Atendimentos")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(button_frame, text="Novo Evento", command=lambda: self.app.dispatch("navigate", module_name="Agenda")).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        return card

    def _create_map_card(self, parent, title, row, col, colspan):
        card, _ = self._create_card_base(parent, title, row, col, colspan=colspan)
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)
        open_map_button = ctk.CTkButton(card, text="Abrir Mapa Interativo", height=40, font=ctk.CTkFont(size=14, weight="bold"),
                                        command=lambda: self.app.dispatch("navigate", module_name="Geolocalização"))
        open_map_button.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        return card

    def _load_stats(self):
        report_service = self.repos.get("report")
        if not report_service: return
        stats = report_service.get_dashboard_stats()
        self.card_pessoas.value_label.configure(text=str(stats.get('total_pessoas', 0)))
        self.card_atendimentos.value_label.configure(text=str(stats.get('total_atendimentos_pendentes', 0)))
        self.card_proposicoes.value_label.configure(text=str(stats.get('total_proposicoes_ano', 0)))
        self.card_votos_sim.value_label.configure(text=str(stats.get('votos_sim', 0)))

    def _populate_agenda_card(self):
        content_frame = self.agenda_card.content_frame
        for widget in content_frame.winfo_children(): widget.destroy()

        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        today_events = crm_repo.get_events_for_day(datetime.now().date())
        if not today_events:
            ctk.CTkLabel(content_frame, text="Nenhum compromisso para hoje.").pack(expand=True, padx=5, pady=10)
            return

        for evento in today_events:
            evento_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            evento_frame.pack(fill="x", pady=2)
            evento_frame.grid_columnconfigure(1, weight=1)
            time_str = evento.get('hora_inicio') or "Dia todo"
            ctk.CTkLabel(evento_frame, text=time_str, font=ctk.CTkFont(size=12, weight="bold"), width=70).grid(row=0, column=0, padx=(0,10), sticky="n")
            btn = ctk.CTkButton(evento_frame, text=evento['titulo'], anchor="w", fg_color="transparent", command=lambda e_id=evento['id_evento']: EventoFormWindow(self, self.repos, self.app, evento_id=e_id))
            btn.grid(row=0, column=1, sticky="ew")

    def refresh_atendimentos_list(self):
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
            color = priority_colors.get(prioridade)
            prio_label = ctk.CTkLabel(atendimento_frame, text=prioridade.upper(), font=ctk.CTkFont(size=10, weight="bold"), width=10, text_color=color)
            prio_label.grid(row=0, column=0, padx=(0,10), sticky="n")
            
            title = atendimento['titulo']
            solicitante = atendimento['nome_solicitante'] or 'N/A'
            display_text = f"{title}\n(Solicitante: {solicitante})"
            
            btn = ctk.CTkButton(atendimento_frame, text=display_text, anchor="w", fg_color="transparent",
                                command=lambda a_id=atendimento['id_atendimento']: AtendimentoFormWindow(self, self.repos, self.app, atendimento_id=a_id))
            btn.grid(row=0, column=1, sticky="ew")

    def _populate_birthday_card(self):
        content_frame = self.birthday_card.content_frame
        for widget in content_frame.winfo_children(): widget.destroy()

        report_service = self.repos.get("report")
        if not report_service: return

        # A função agora retorna uma lista de tuplas: (data, Candidatura)
        upcoming_birthdays = report_service.get_upcoming_birthdays(days=7, roles=['PREFEITO'])
        
        if not upcoming_birthdays:
            ctk.CTkLabel(content_frame, text="Nenhum prefeito aniversariante na próxima semana.").pack(expand=True, padx=5, pady=10)
            return
        
        last_date_header = None
        for bday_date, candidatura in upcoming_birthdays: # MUDANÇA: a variável agora se chama 'candidatura'
            date_str = format_date_with_weekday_robust(bday_date)
            
            if date_str != last_date_header:
                last_date_header = date_str
                ctk.CTkLabel(content_frame, text=date_str, font=ctk.CTkFont(weight="bold", underline=True)).pack(anchor="w", pady=(8,2), padx=5)

            person_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            person_frame.pack(fill="x", pady=0, padx=20)
            person_frame.grid_columnconfigure(1, weight=1)

            bday_str_ddmm = bday_date.strftime("%d/%m")
            ctk.CTkLabel(person_frame, text=bday_str_ddmm, font=ctk.CTkFont(size=12, weight="bold"), width=50).grid(row=0, column=0, padx=(0,10))
            
            # --- MUDANÇA AQUI ---
            # O nome e o ID estão agora dentro do objeto 'pessoa' aninhado
            pessoa = candidatura.pessoa 
            btn = ctk.CTkButton(person_frame, text=pessoa.nome, anchor="w", fg_color="transparent",
                                command=lambda p_id=pessoa.id_pessoa: self.app.dispatch("open_form", form_name="person", person_id=p_id, parent_view=self))
            btn.grid(row=0, column=1, sticky="ew")

    def _open_all_birthdays_window(self):
        UpcomingBirthdaysWindow(self.app, self.repos)

    def _populate_feed_card(self):
        for widget in self.feed_content_frame.winfo_children(): widget.destroy()

        report_service = self.repos.get("report")
        if not report_service: return

        recent_activities = report_service.get_recent_activities(limit=15)

        if not recent_activities:
            ctk.CTkLabel(self.feed_content_frame, text="Nenhuma atividade recente encontrada.").pack(expand=True, padx=5, pady=10)
            return

        for activity in recent_activities:
            activity_frame = ctk.CTkFrame(self.feed_content_frame, fg_color="transparent")
            activity_frame.pack(fill="x", pady=2, padx=5)
            activity_frame.grid_columnconfigure(1, weight=1)

            date_to_display_str = activity.get('data_local', activity['data'])
            
            try:
                date_obj = datetime.strptime(date_to_display_str, '%Y-%m-%d %H:%M')
                date_time_str = date_obj.strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                date_time_str = date_to_display_str.split(" ")[0] if date_to_display_str else ""
            
            ctk.CTkLabel(activity_frame, text=f"{date_time_str} - {activity['tipo']}:", 
                         font=ctk.CTkFont(size=11, weight="bold"), width=120, anchor="w").grid(row=0, column=0, sticky="nw")
            
            ctk.CTkLabel(activity_frame, text=activity['descricao'], 
                         font=ctk.CTkFont(size=11), wraplength=180, justify="left", anchor="w").grid(row=0, column=1, sticky="ew")