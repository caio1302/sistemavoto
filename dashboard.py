import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dto.pessoa import Pessoa
import customtkinter as ctk

class CityDashboard(tk.Frame):
    def __init__(self, parent, party_data: list[dict], top_vereadores_data: list[Pessoa], *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        if is_dark:
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            grid_color = "#555555"
        else:
            bg_color = "#ebebeb"
            text_color = "#1a1a1a"
            grid_color = "#cccccc"

        self.configure(bg=bg_color)

        self.party_data = party_data
        self.top_vereadores_data = top_vereadores_data

        plt.style.use('dark_background' if is_dark else 'seaborn-v0_8-whitegrid')
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 5))
        self.fig.patch.set_facecolor(bg_color) 
        self.ax1.set_facecolor(bg_color)
        self.ax2.set_facecolor(bg_color)
        
        if not is_dark:
            self.ax2.grid(color=grid_color, linestyle='--', linewidth=0.5)

        for ax in [self.ax1, self.ax2]:
            ax.title.set_color(text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            for tick in ax.get_xticklabels() + ax.get_yticklabels():
                tick.set_color(text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)

        self._create_party_pie_chart()
        self._create_votes_bar_chart(text_color)
        
        self.fig.tight_layout(pad=3.0)

        canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.get_tk_widget().configure(bg=bg_color)

    def _create_party_pie_chart(self):
        text_color = self.ax1.title.get_color()
        if not self.party_data:
            self.ax1.text(0.5, 0.5, 'Sem dados de partidos.', ha='center', va='center', color=text_color)
            self.ax1.set_title('Composição Partidária da Câmara (Eleitos)')
            return

        partidos = [item['partido'] for item in self.party_data]
        contagem = [item['count'] for item in self.party_data]
        
        wedges, texts, autotexts = self.ax1.pie(contagem, labels=partidos, autopct='%1.1f%%', startangle=90,
                                                textprops={'color': text_color},
                                                wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        plt.setp(autotexts, color='white' if ctk.get_appearance_mode() == "Dark" else "black", weight="bold")
        self.ax1.set_title('Composição Partidária da Câmara (Eleitos)')
        self.ax1.axis('equal')

    def _create_votes_bar_chart(self, text_color):
        if not self.top_vereadores_data:
            self.ax2.text(0.5, 0.5, 'Sem dados de votos.', ha='center', va='center', color=text_color)
            self.ax2.set_title('Top 5 Vereadores Eleitos Mais Votados')
            return
            
        sorted_data = sorted(self.top_vereadores_data, key=lambda x: x.votos if x.votos is not None else 0, reverse=False) 
        nomes = [f"{c.nome_urna} ({c.partido})" for c in sorted_data]
        votos = [c.votos for c in sorted_data]
        y_pos = np.arange(len(nomes))
        
        bar_color = "#3a7ebf"
        bars = self.ax2.barh(y_pos, votos, align='center', color=bar_color, edgecolor=text_color, linewidth=0.7)
        self.ax2.set_yticks(y_pos)
        self.ax2.set_yticklabels(nomes, fontsize=9)
        self.ax2.invert_yaxis()
        self.ax2.set_xlabel('Quantidade de Votos')
        self.ax2.set_title(f'Top {len(nomes)} Vereadores Eleitos Mais Votados')

        for bar in bars:
            width = bar.get_width()
            self.ax2.text(width + (max(votos) * 0.01 if votos else 1),
                          bar.get_y() + bar.get_height()/2,
                          f'{width:,}'.replace(",", "."),
                          va='center', ha='left', fontsize=8, color=text_color)

        if votos:
            self.ax2.set_xlim(right=max(votos) * 1.18)
        else:
            self.ax2.set_xlim(right=10)

        self.ax2.spines['top'].set_visible(False)
        self.ax2.spines['right'].set_visible(False)