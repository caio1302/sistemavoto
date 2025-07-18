import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
import calendar
from collections import defaultdict
from .evento_form_window import EventoFormWindow
from popups.helpers import format_date_with_weekday_robust

class AgendaView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app, initial_filters=None):
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app
        self.current_date = datetime.now()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, minsize=200)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)

        self._create_widgets()
        self.draw_calendar()
        self.populate_week_list()

    # MUDANÇA: Novo método para reagir ao evento global
    def on_data_updated(self):
        """
        Este método é chamado pelo sistema de eventos da MainApplication
        sempre que dados relevantes para esta view são alterados.
        """
        self.draw_calendar()
        self.populate_week_list()

    def _create_widgets(self):
        left_main_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_main_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        left_main_frame.grid_rowconfigure(1, weight=1)
        left_main_frame.grid_rowconfigure(3, weight=0)
        left_main_frame.grid_columnconfigure(0, weight=1)
        
        header_frame = ctk.CTkFrame(left_main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(0,10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(header_frame, text="< Mês Anterior", command=self.prev_month).grid(row=0, column=0, sticky="w")
        self.month_year_label = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.month_year_label.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(header_frame, text="Próximo Mês >", command=self.next_month).grid(row=0, column=2, sticky="e")
        ctk.CTkButton(header_frame, text="Novo Evento", command=self.open_evento_form).grid(row=0, column=3, padx=(20,0), sticky="e")
        
        self.calendar_frame = ctk.CTkFrame(left_main_frame)
        self.calendar_frame.grid(row=1, column=0, padx=10, sticky="nsew")

        ctk.CTkLabel(left_main_frame, text="Próximos 7 Dias", font=ctk.CTkFont(size=16, weight="bold")).grid(row=2, column=0, padx=10, pady=(15,5), sticky="w")
        self.week_list_frame = ctk.CTkScrollableFrame(left_main_frame, label_text="")
        self.week_list_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew", ipady=10)
        
        self.details_panel = ctk.CTkFrame(self, width=320)
        self.details_panel.grid(row=0, column=1, rowspan=2, padx=(0,10), pady=10, sticky="nsew")
        self.details_panel.grid_propagate(False)
        self.details_panel.grid_rowconfigure(1, weight=1)
        self.details_title = ctk.CTkLabel(self.details_panel, text="Selecione um dia", font=ctk.CTkFont(size=16, weight="bold"))
        self.details_title.pack(pady=10, padx=10)
        self.details_scrollframe = ctk.CTkScrollableFrame(self.details_panel, label_text="")
        self.details_scrollframe.pack(fill="both", expand=True, padx=5, pady=5)

    def draw_calendar(self):
        for widget in self.calendar_frame.winfo_children(): widget.destroy()
        self._clear_details_panel()
        
        year, month = self.current_date.year, self.current_date.month
        month_name = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][month]
        self.month_year_label.configure(text=f"{month_name} de {year}")

        crm_repo = self.repos.get("crm")
        if not crm_repo: return

        eventos_no_mes = crm_repo.get_eventos_for_month(year, month)
        self.eventos_por_dia = defaultdict(list)
        for evento in eventos_no_mes:
            try:
                dia = datetime.strptime(evento['data_evento'], "%Y-%m-%d").day
                self.eventos_por_dia[dia].append(evento)
            except (ValueError, TypeError):
                continue
            
        days_of_week = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for i, day_name in enumerate(days_of_week):
            self.calendar_frame.grid_columnconfigure(i, weight=1, uniform="calendar_col")
            ctk.CTkLabel(self.calendar_frame, text=day_name, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=1, pady=1, sticky="nsew")
        
        month_calendar = calendar.monthcalendar(year, month)
        for week_index, week in enumerate(month_calendar):
            self.calendar_frame.grid_rowconfigure(week_index + 1, weight=1, uniform="calendar_row")
            for day_index, day_num in enumerate(week):
                if day_num == 0:
                    ctk.CTkFrame(self.calendar_frame, fg_color=("gray85", "gray18"), border_width=0).grid(row=week_index + 1, column=day_index, padx=1, pady=1, sticky="nsew")
                else:
                    day_button = ctk.CTkButton(self.calendar_frame, text=str(day_num), corner_radius=3, border_width=1,
                                               command=lambda d=day_num: self.show_day_details(d))
                    day_button.grid(row=week_index + 1, column=day_index, padx=1, pady=1, sticky="nsew")
                    if day_num in self.eventos_por_dia:
                        day_button.configure(fg_color="green", text_color="white", font=ctk.CTkFont(weight="bold"))

    def populate_week_list(self):
        for widget in self.week_list_frame.winfo_children(): widget.destroy()
        
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        
        upcoming_events = crm_repo.get_upcoming_events()
        if not upcoming_events:
            ctk.CTkLabel(self.week_list_frame, text="Nenhum evento agendado.").pack(pady=10)
            return

        last_date_str = ""
        for evento in upcoming_events:
            data_obj = datetime.strptime(evento['data_evento'], "%Y-%m-%d")
            date_str_display = format_date_with_weekday_robust(data_obj)

            if date_str_display != last_date_str:
                ctk.CTkLabel(self.week_list_frame, text=date_str_display, font=ctk.CTkFont(weight="bold", underline=True)).pack(anchor="w", padx=5, pady=(8, 2))
                last_date_str = date_str_display

            evento_btn = ctk.CTkButton(self.week_list_frame, text=f"  • {evento['titulo']}", anchor="w", 
                fg_color="transparent", hover=False, text_color=("#1f6aa5", "#60a5fa"),
                command=lambda e_id=evento['id_evento']: self.open_evento_form(e_id))
            evento_btn.pack(fill="x", padx=15, pady=1)

    def show_day_details(self, day_num):
        self._clear_details_panel()
        date_obj = datetime(self.current_date.year, self.current_date.month, day_num)
        self.details_title.configure(text=f"Eventos para {date_obj.strftime('%d/%m/%Y')}")
        eventos_do_dia = self.eventos_por_dia.get(day_num, [])
        if not eventos_do_dia:
            ctk.CTkLabel(self.details_scrollframe, text="Nenhum evento neste dia.").pack(pady=10)
            return
        for evento in eventos_do_dia:
            evento_frame = ctk.CTkFrame(self.details_scrollframe, border_width=1)
            evento_frame.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(evento_frame, text=evento['titulo'], font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(5,0))
            if evento['local']: ctk.CTkLabel(evento_frame, text=f"Local: {evento['local']}").pack(anchor="w", padx=5)
            btn_frame = ctk.CTkFrame(evento_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=5, pady=5)
            ctk.CTkButton(btn_frame, text="Editar", width=70, command=lambda e=evento['id_evento']: self.open_evento_form(e)).pack(side="left")
            ctk.CTkButton(btn_frame, text="Apagar", width=70, fg_color="#D32F2F", hover_color="#B71C1C", command=lambda e=evento: self._delete_evento(e)).pack(side="left", padx=5)

    def _clear_details_panel(self):
        for widget in self.details_scrollframe.winfo_children():
            widget.destroy()
        self.details_title.configure(text="Selecione um dia")

    def _delete_evento(self, evento):
        crm_repo = self.repos.get("crm")
        if not crm_repo: return
        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja apagar o evento '{evento['titulo']}'?", icon="warning"):
            if crm_repo.delete_evento(evento['id_evento']):
                self.on_data_updated() # Chama o método de atualização após deletar

    def prev_month(self):
        self.current_date = self.current_date.replace(day=1) - timedelta(days=1)
        self.draw_calendar()
        self.populate_week_list()

    def next_month(self):
        days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
        self.current_date = self.current_date.replace(day=days_in_month) + timedelta(days=1)
        self.draw_calendar()
        self.populate_week_list()

    def open_evento_form(self, evento_id=None):
        if hasattr(self, 'evento_form') and self.evento_form.winfo_exists():
            self.evento_form.focus()
            return
        pre_selected = self.current_date if evento_id is None else None
        self.evento_form = EventoFormWindow(self, self.repos, self.app, evento_id, pre_selected_date=pre_selected)