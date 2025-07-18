import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import datetime, timedelta
import calendar
import logging

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

class DatePicker(ctk.CTkToplevel):
    def __init__(self, parent, entry_widget):
        super().__init__(parent)
        self.entry = entry_widget
        self.title("Selecione a Data")

        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        try:
            self._selected_date = datetime.strptime(self.entry.get(), "%d/%m/%Y")
        except (ValueError, TypeError):
            self._selected_date = datetime.now()
        
        self._view_date = self._selected_date
        self._view_mode = 'day'

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")

        self._create_header()
        self._create_views()
        self._show_view()
        
        self._position_window(parent, entry_widget)

    def _position_window(self, parent, entry_widget):
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        widget_x = entry_widget.winfo_x()
        widget_y = entry_widget.winfo_y()
        widget_h = entry_widget.winfo_height()
        
        self.geometry(f"+{parent_x + widget_x}+{parent_y + widget_y + widget_h + 2}")

    def _create_header(self):
        self.prev_button = ctk.CTkButton(self.header_frame, text="<", width=30, command=self._prev_view)
        self.prev_button.pack(side="left")

        self.view_button = ctk.CTkButton(self.header_frame, text="", command=self._change_view, fg_color="transparent", hover_color=("gray70", "gray30"))
        self.view_button.pack(side="left", expand=True, fill="x")

        self.next_button = ctk.CTkButton(self.header_frame, text=">", width=30, command=self._next_view)
        self.next_button.pack(side="right")
        
    def _create_views(self):
        self.day_view_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.day_view_frame.grid_columnconfigure(0, weight=1)
        self.day_view_frame.grid_rowconfigure(1, weight=1)

        days_header = ctk.CTkFrame(self.day_view_frame, fg_color="transparent")
        days_header.grid(row=0, column=0, sticky="ew", pady=(5,2))
        dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for i, dia in enumerate(dias_semana):
            days_header.grid_columnconfigure(i, weight=1)
            lbl = ctk.CTkLabel(days_header, text=dia, font=ctk.CTkFont(size=11, weight="bold"), width=38)
            lbl.grid(row=0, column=i)

        self.day_grid_frame = ctk.CTkFrame(self.day_view_frame, fg_color="transparent")
        self.day_grid_frame.grid(row=1, column=0, sticky="nsew")
        
        self.day_footer_frame = ctk.CTkFrame(self.day_view_frame, fg_color="transparent")
        self.day_footer_frame.grid(row=2, column=0, sticky="ew", pady=(8,0))
        self.day_footer_frame.grid_columnconfigure(0, weight=1)
        today_btn = ctk.CTkButton(self.day_footer_frame, text="Hoje", command=self._select_today, height=30)
        today_btn.grid(row=0, column=0, sticky='ew')

        self.month_view_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        for i in range(3):
            self.month_view_frame.grid_rowconfigure(i, weight=1)
            for j in range(4):
                self.month_view_frame.grid_columnconfigure(j, weight=1)

        self.year_view_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        for i in range(4):
            self.year_view_frame.grid_rowconfigure(i, weight=1)
            for j in range(4):
                self.year_view_frame.grid_columnconfigure(j, weight=1)

    def _show_view(self):
        for frame in [self.day_view_frame, self.month_view_frame, self.year_view_frame]:
            frame.grid_remove()
        
        if self._view_mode == 'day':
            self.view_button.configure(text=f"{MESES_PT[self._view_date.month - 1]} {self._view_date.year}")
            self._populate_day_grid()
            self.day_view_frame.grid(row=0, column=0, sticky="nsew")
        elif self._view_mode == 'month':
            self.view_button.configure(text=str(self._view_date.year))
            self._populate_month_grid()
            self.month_view_frame.grid(row=0, column=0, sticky="nsew")
        elif self._view_mode == 'year':
            start_year = self._view_date.year - 7
            end_year = self._view_date.year + 8
            self.view_button.configure(text=f"{start_year} - {end_year-1}")
            self._populate_year_grid()
            self.year_view_frame.grid(row=0, column=0, sticky="nsew")

    def _populate_day_grid(self):
        for widget in self.day_grid_frame.winfo_children():
            widget.destroy()

        cal = calendar.monthcalendar(self._view_date.year, self._view_date.month)
        today = datetime.now()

        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                
                day_date = datetime(self._view_date.year, self._view_date.month, day)
                
                btn = ctk.CTkButton(self.day_grid_frame, text=str(day), width=38, height=38, corner_radius=38,
                                    command=lambda d=day_date: self._select_date(d))
                
                if day_date.date() == self._selected_date.date():
                    btn.configure(fg_color=("#3a7ebf", "#1f538d"))
                elif day_date.date() == today.date():
                    btn.configure(fg_color="transparent", border_width=1, border_color=("#3a7ebf", "#1f538d"))
                else:
                    btn.configure(fg_color="transparent", hover_color=("gray70", "gray30"))

                btn.grid(row=r, column=c, padx=1, pady=1)

    def _populate_month_grid(self):
        for widget in self.month_view_frame.winfo_children():
            widget.destroy()

        for i, month_name in enumerate(MESES_PT):
            month_num = i + 1
            row, col = divmod(i, 4)
            btn = ctk.CTkButton(self.month_view_frame, text=month_name[:3], width=65, height=50,
                                command=lambda m=month_num: self._select_month(m))
            
            if month_num == self._view_date.month and self._view_date.year == self._selected_date.year:
                btn.configure(fg_color=("#3a7ebf", "#1f538d"))
            else:
                 btn.configure(fg_color="transparent", hover_color=("gray70", "gray30"))
            btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)

    def _populate_year_grid(self):
        for widget in self.year_view_frame.winfo_children():
            widget.destroy()

        start_year = self._view_date.year - 7
        for i in range(16):
            year = start_year + i
            row, col = divmod(i, 4)
            btn = ctk.CTkButton(self.year_view_frame, text=str(year), width=65, height=50,
                                command=lambda y=year: self._select_year(y))
            
            if year == self._selected_date.year:
                 btn.configure(fg_color=("#3a7ebf", "#1f538d"))
            else:
                 btn.configure(fg_color="transparent", hover_color=("gray70", "gray30"))
            btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)

    def _change_view(self):
        if self._view_mode == 'day':
            self._view_mode = 'month'
        elif self._view_mode == 'month':
            self._view_mode = 'year'
        self._show_view()

    def _prev_view(self):
        if self._view_mode == 'day':
            first_day = self._view_date.replace(day=1)
            self._view_date = first_day - timedelta(days=1)
        elif self._view_mode == 'month':
            self._view_date = self._view_date.replace(year=self._view_date.year - 1)
        elif self._view_mode == 'year':
            self._view_date = self._view_date.replace(year=self._view_date.year - 16)
        self._show_view()

    def _next_view(self):
        if self._view_mode == 'day':
            _, last_day = calendar.monthrange(self._view_date.year, self._view_date.month)
            first_day_next_month = self._view_date.replace(day=last_day) + timedelta(days=1)
            self._view_date = first_day_next_month
        elif self._view_mode == 'month':
            self._view_date = self._view_date.replace(year=self._view_date.year + 1)
        elif self._view_mode == 'year':
            self._view_date = self._view_date.replace(year=self._view_date.year + 16)
        self._show_view()

    def _select_date(self, date):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, date.strftime("%d/%m/%Y"))
        self.destroy()
        
    def _select_today(self):
        self._select_date(datetime.now())

    def _select_month(self, month):
        self._view_date = self._view_date.replace(month=month)
        self._view_mode = 'day'
        self._show_view()

    def _select_year(self, year):
        self._view_date = self._view_date.replace(year=year)
        self._view_mode = 'month'
        self._show_view()