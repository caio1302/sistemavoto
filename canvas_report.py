import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageTk
from pathlib import Path
import os 
import logging 
import datetime

import config
from functions import data_helpers
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura

class CanvasReport:
    def __init__(self, parent_frame, repos: dict, app_instance):
        self.parent = parent_frame
        self.repos = repos
        self.app = app_instance
        self.images = [] 

    def display(self, cidade: str, ano_eleicao: int, prefeito: Candidatura | None, vice: Candidatura | None, vereadores: list[Candidatura], ranking_2022: dict[str, list[Candidatura]], candidato_destaque: Pessoa | Candidatura | None, city_data_completo: dict):
        self.images.clear()
        for widget in self.parent.winfo_children(): 
            widget.destroy()
        self._exibir_relatorio(cidade, ano_eleicao, prefeito, vice, vereadores, ranking_2022, candidato_destaque, city_data_completo)

    def _get_tag(self, tag_id, default_text):
        misc_repo = self.repos.get("misc")
        if misc_repo:
            return misc_repo.get_ui_tags().get(tag_id, default_text)
        return default_text

    def _bind_card_to_edit(self, widget, pessoa: Pessoa):
        if not pessoa or not pessoa.id_pessoa: return
        
        def on_card_click(event, person_id=pessoa.id_pessoa):
            self.app.dispatch("open_form", form_name="person", person_id=person_id, parent_view=self.app)

        template_data = {
            'nome': (pessoa.apelido or pessoa.nome).title(),
            'id_pessoa': pessoa.id_pessoa
        }
        tooltip_template = self._get_tag("tooltip_card_candidato", "Clique para editar {nome}")
        try:
            tooltip_text = tooltip_template.format(**template_data)
        except KeyError as e:
            logging.warning(f"Chave não encontrada na tag de tooltip: {e}. Usando texto padrão.")
            tooltip_text = f"Clique para editar {template_data['nome']}"

        def on_mouse_enter(event):
            self.app.update_status_bar(tooltip_text)

        def on_mouse_leave(event):
            pronto_text = self._get_tag("tooltip_pronto", "Pronto.")
            self.app.update_status_bar(pronto_text)

        widget.bind("<Button-1>", on_card_click)
        widget.bind("<Enter>", on_mouse_enter)
        widget.bind("<Leave>", on_mouse_leave)
        widget.configure(cursor="hand2")
        
        for child in widget.winfo_children():
            child.bind("<Button-1>", on_card_click)
            child.bind("<Enter>", on_mouse_enter)
            child.bind("<Leave>", on_mouse_leave)
            if not isinstance(child, (ttk.Separator, tk.Frame)):
                child.configure(cursor="hand2")

    def _get_photo_for_card(self, pessoa: Pessoa | None) -> ImageTk.PhotoImage | None:
        if not pessoa: return None
        photo_path_str = data_helpers.get_candidate_photo_path(pessoa, self.repos)
        
        try:
            img = Image.open(photo_path_str)
            img.thumbnail((75, 90), Image.LANCZOS)
            photo_tk = ImageTk.PhotoImage(img)
            self.images.append(photo_tk)
            return photo_tk
        except Exception as e:
            logging.warning(f"Não foi possível carregar a imagem em '{photo_path_str}': {e}")
            try:
                img_placeholder = Image.open(config.PLACEHOLDER_PHOTO_PATH)
                img_placeholder.thumbnail((75, 90), Image.LANCZOS)
                photo_tk_placeholder = ImageTk.PhotoImage(img_placeholder)
                self.images.append(photo_tk_placeholder)
                return photo_tk_placeholder
            except Exception as e_ph:
                logging.error(f"Falha CRÍTICA ao carregar foto placeholder: {e_ph}")
                return None

    def _create_section_title(self, parent_widget, text: str):
        frame = tk.Frame(parent_widget, bg="#e0e0e0", bd=1, relief='solid')
        frame.pack(fill=tk.X, pady=(15, 8), padx=10)
        label = tk.Label(frame, text=text, bg="#e0e0e0", font=("Helvetica", 10, "bold"), anchor='w')
        label.pack(fill=tk.X, padx=10, pady=4)

    def _create_info_tables(self, parent_widget, prefeitura_data: dict | None):
        if not prefeitura_data:
            tk.Label(parent_widget, text="Dados da prefeitura não disponíveis.", bg='white', font=("Helvetica", 9)).pack(padx=10, pady=5)
            return

        populacao = prefeitura_data.get('populacao')
        area = prefeitura_data.get('area')
        densidade_formatada = ' - '
        if populacao and area and area > 0:
            densidade_calculada = populacao / area
            densidade_formatada = f"{densidade_calculada:,.2f} hab/km²".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            densidade_db = prefeitura_data.get('dens_demo')
            if densidade_db: densidade_formatada = f"{densidade_db} hab/km²"

        pop_formatada = f"{populacao:,}".replace(",", ".") if isinstance(populacao, int) else ' - '
        area_suffix = self._get_tag('label_area_suffix', "KM²")
        area_formatada = f"{area:,.2f} {area_suffix}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(area, (int, float)) else ' - '
        
        eleitorado_fem = prefeitura_data.get('eleitorado_feminino')
        eleitorado_mas = prefeitura_data.get('eleitorado_masculino')
        eleitorado_total = prefeitura_data.get('eleitorado_total')
        fem_formatado = f"{eleitorado_fem:,}".replace(",", ".") if eleitorado_fem is not None else '0'
        mas_formatado = f"{eleitorado_mas:,}".replace(",", ".") if eleitorado_mas is not None else '0'
        total_formatado = f"{eleitorado_total:,}".replace(",", ".") if eleitorado_total is not None else '0'
        
        table_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
        table_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        data1 = [
            [(self._get_tag('label_prefeitura', 'Prefeitura:'), prefeitura_data.get('endereco')), (self._get_tag('label_cep', 'CEP:'), prefeitura_data.get('cep')), (self._get_tag('label_cod_ibge', 'Cód. IBGE:'), prefeitura_data.get('cod_ibge')), (self._get_tag('label_aniversario_cidade', 'Aniversário:'), prefeitura_data.get('aniversario'))],
            [(self._get_tag('label_site', 'Site:'), prefeitura_data.get('url')), (self._get_tag('label_populacao', 'População:'), pop_formatada), (self._get_tag('label_dens_demografica', 'Dens. Demográfica:'), densidade_formatada), None],
            [(self._get_tag('label_email', 'Email:'), prefeitura_data.get('email')), (self._get_tag('label_tel', 'Tel:'), prefeitura_data.get('tel')), (self._get_tag('label_gentilico', 'Gentílico:'), prefeitura_data.get('gentilico')), (self._get_tag('label_area', 'Área:'), area_formatada)]
        ]
        for r_idx, row_data in enumerate(data1):
            for c_idx, cell_data in enumerate(row_data):
                if cell_data:
                    tk.Label(table_frame, text=cell_data[0], bg='white', font=("Helvetica", 9, 'bold')).grid(row=r_idx, column=c_idx*2, sticky='e', padx=(5,0), pady=2)
                    tk.Label(table_frame, text=(cell_data[1] or ' - '), bg='white', font=("Helvetica", 9)).grid(row=r_idx, column=c_idx*2+1, sticky='w', padx=(2,5), pady=2)
                      
        table2_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
        table2_frame.pack(fill=tk.X, padx=10)
        
        data2 = [
            [(self._get_tag('label_idhm_geral', 'IDHM Geral:'), prefeitura_data.get('idhm_geral')), (self._get_tag('label_idhm_longevidade', 'Longevidade:'), prefeitura_data.get('idhm_long')), (self._get_tag('label_mulheres', 'Mulheres:'), fem_formatado)],
            [(self._get_tag('label_idhm_renda', 'Renda:'), prefeitura_data.get('idhm_renda')), (self._get_tag('label_idhm_educacao', 'Educação:'), prefeitura_data.get('idhm_educ')), (self._get_tag('label_homens', 'Homens:'), mas_formatado)],
            [None, None, (self._get_tag('label_total', 'Total:'), total_formatado)]
        ]
        for r_idx, row_data in enumerate(data2):
            for c_idx, cell_data in enumerate(row_data):
                if cell_data:
                    tk.Label(table2_frame, text=cell_data[0], bg='white', font=("Helvetica", 9, 'bold')).grid(row=r_idx, column=c_idx*2, sticky='e', padx=(5,0), pady=2)
                    tk.Label(table2_frame, text=(str(cell_data[1]) if cell_data[1] is not None else ' - '), bg='white', font=("Helvetica", 9)).grid(row=r_idx, column=c_idx*2+1, sticky='w', padx=(2,5), pady=2)


    def _exibir_relatorio(self, cidade: str, ano_eleicao: int, prefeito: Candidatura | None, vice: Candidatura | None, vereadores: list[Candidatura], ranking_2022: dict[str, list[Candidatura]], candidato_destaque: Pessoa | Candidatura | None, city_data_completo: dict):
        header_frame = tk.Frame(self.parent, bg='white')
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        try:
            logo_to_use = config.CUSTOM_LOGO_PATH if os.path.exists(config.CUSTOM_LOGO_PATH) else config.LOGO_PATH
            logo_img_obj = Image.open(logo_to_use)
            logo_img_obj.thumbnail((300, 100), Image.LANCZOS)
            logo_photo_tk = ImageTk.PhotoImage(logo_img_obj)
            self.images.append(logo_photo_tk) 
            logo_label = tk.Label(header_frame, image=logo_photo_tk, bg='white')
            logo_label.pack(side=tk.LEFT)
        except Exception as e:
            logging.error(f"Erro ao carregar logo no canvas: {e}", exc_info=True)
            tk.Label(header_frame, text="Logo Indisponível", bg='white').pack(side=tk.LEFT)
        
        city_title_frame = tk.Frame(self.parent, bg="#f2f2f2", bd=1, relief='solid')
        city_title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        city_suffix = self._get_tag('title_city_suffix', ' / SP')
        city_title_label = ttk.Label(city_title_frame, text=f"{cidade.upper()}{city_suffix} (Eleição {ano_eleicao})", style="Header.TLabel", background="#f2f2f2")
        city_title_label.pack(pady=4, padx=10, anchor='w', side=tk.LEFT)
        
        dashboard_button = ttk.Button(city_title_frame, text="Visualizar Dashboard", 
                                      command=lambda c=cidade, a=ano_eleicao: self.app.dispatch("open_dashboard", cidade=c, ano=a))
        dashboard_button.pack(pady=4, padx=10, anchor='e', side=tk.RIGHT)
        
        prefeitura_info = city_data_completo.get("prefeitura")
        if prefeitura_info:
            self._create_section_title(self.parent, self._get_tag('title_section_info', "INFORMAÇÕES MUNICIPAIS"))
            self._create_info_tables(self.parent, prefeitura_info)
        
        # --- LÓGICA REFINADA DO CANDIDATO DESTAQUE ---
        if candidato_destaque:
            card = None
            # Se for um objeto Candidatura, ele tem votos e deve ser exibido como tal
            if isinstance(candidato_destaque, Candidatura):
                nome_urna = (candidato_destaque.nome_urna or candidato_destaque.pessoa.apelido or '').upper()
                titulo_destaque = f"VOTAÇÃO {nome_urna} EM {cidade.upper()}"
                self._create_section_title(self.parent, titulo_destaque)
                card = self._create_report_card(self.parent, candidato_destaque)
            # Se for apenas Pessoa, não tem votação no contexto e é exibido como um contato simples
            elif isinstance(candidato_destaque, Pessoa):
                titulo_destaque = (candidato_destaque.apelido or candidato_destaque.nome).upper()
                self._create_section_title(self.parent, titulo_destaque)
                card = self._create_contact_info_card(self.parent, candidato_destaque)
            
            if card: card.pack(fill=tk.X, padx=10, pady=(0,5))
            
        if prefeito or vice or vereadores:
            self._create_section_title(self.parent, f"PODER EXECUTIVO ({ano_eleicao})")
            exec_frame = tk.Frame(self.parent, bg='white')
            exec_frame.pack(fill=tk.X, padx=10)
            exec_frame.grid_columnconfigure(0, weight=1); exec_frame.grid_columnconfigure(1, weight=1)
            if prefeito:
                prefeito_card = self._create_report_card(exec_frame, prefeito)
                if prefeito_card: prefeito_card.grid(row=0, column=0, padx=(0, 2), pady=(0,5), sticky="nsew") 
            if vice:
                vice_card = self._create_report_card(exec_frame, vice)
                if vice_card: vice_card.grid(row=0, column=1, padx=(2, 0), pady=(0,5), sticky="nsew")

            if vereadores:
                self._create_section_title(self.parent, f"PODER LEGISLATIVO ({ano_eleicao})")
                leg_frame = tk.Frame(self.parent, bg='white')
                leg_frame.pack(fill=tk.X, padx=10)
                leg_frame.grid_columnconfigure(0, weight=1); leg_frame.grid_columnconfigure(1, weight=1)
                for i, candidatura_vereador in enumerate(vereadores):
                    col = i % 2; padding = (0, 2) if col == 0 else (2, 0)
                    vereador_card = self._create_report_card(leg_frame, candidatura_vereador)
                    if vereador_card: vereador_card.grid(row=i//2, column=col, padx=padding, pady=(0, 5), sticky="nsew")

        if ranking_2022:
            for cargo, candidaturas in ranking_2022.items():
                if candidaturas:
                    self._create_ranking_section(self.parent, f"TOP 5 - {cargo.title()} ({ano_eleicao})", candidaturas)

    def _create_contact_info_card(self, parent_widget, pessoa: Pessoa) -> tk.Frame | None:
        if not pessoa: return None
        
        main_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
        photo_tk = self._get_photo_for_card(pessoa)
        if photo_tk:
            photo_label = tk.Label(main_frame, image=photo_tk, bg='white')
        else:
            photo_label = tk.Label(main_frame, text="Foto\nIndisp.", bg='white', width=10, height=5)
        photo_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        info_frame = tk.Frame(main_frame, bg='white')
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def add_info_row(label, value):
            if value:
                row = tk.Frame(info_frame, bg='white')
                row.pack(fill='x', anchor='w')
                tk.Label(row, text=f"{label}:", font=("Helvetica", 9, "bold"), bg='white', anchor='w').pack(side='left')
                tk.Label(row, text=value, font=("Helvetica", 9), bg='white', anchor='w', wraplength=300).pack(side='left', padx=5)

        add_info_row("Nome", pessoa.nome)
        add_info_row("Apelido", pessoa.apelido)
        add_info_row("Celular", pessoa.celular)
        add_info_row("E-mail", pessoa.email)
            
        self._bind_card_to_edit(main_frame, pessoa)
        return main_frame

    # def _create_info_tables(self, parent_widget, prefeitura_data: dict | None):
    #     if not prefeitura_data:
    #         tk.Label(parent_widget, text="Dados da prefeitura não disponíveis.", bg='white', font=("Helvetica", 9)).pack(padx=10, pady=5)
    #         return

    #     populacao = prefeitura_data.get('populacao')
    #     area = prefeitura_data.get('area')
    #     densidade_formatada = ' - '
    #     if populacao and area and area > 0:
    #         densidade_calculada = populacao / area
    #         densidade_formatada = f"{densidade_calculada:,.2f} hab/km²".replace(",", "X").replace(".", ",").replace("X", ".")
    #     else:
    #         densidade_db = prefeitura_data.get('dens_demo')
    #         if densidade_db: densidade_formatada = f"{densidade_db} hab/km²"

    #     pop_formatada = f"{populacao:,}".replace(",", ".") if isinstance(populacao, int) else ' - '
    #     area_suffix = self._get_tag('label_area_suffix', "KM²")
    #     area_formatada = f"{area:,.2f} {area_suffix}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(area, (int, float)) else ' - '
        
    #     eleitorado_fem = prefeitura_data.get('eleitorado_feminino')
    #     eleitorado_mas = prefeitura_data.get('eleitorado_masculino')
    #     eleitorado_total = prefeitura_data.get('eleitorado_total')
    #     fem_formatado = f"{eleitorado_fem:,}".replace(",", ".") if eleitorado_fem is not None else '0'
    #     mas_formatado = f"{eleitorado_mas:,}".replace(",", ".") if eleitorado_mas is not None else '0'
    #     total_formatado = f"{eleitorado_total:,}".replace(",", ".") if eleitorado_total is not None else '0'
        
    #     table_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
    #     table_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
    #     data1 = [
    #         [(self._get_tag('label_prefeitura', 'Prefeitura:'), prefeitura_data.get('endereco')), (self._get_tag('label_cep', 'CEP:'), prefeitura_data.get('cep')), (self._get_tag('label_cod_ibge', 'Cód. IBGE:'), prefeitura_data.get('cod_ibge')), (self._get_tag('label_aniversario_cidade', 'Aniversário:'), prefeitura_data.get('aniversario'))],
    #         [(self._get_tag('label_site', 'Site:'), prefeitura_data.get('url')), (self._get_tag('label_populacao', 'População:'), pop_formatada), (self._get_tag('label_dens_demografica', 'Dens. Demográfica:'), densidade_formatada), None],
    #         [(self._get_tag('label_email', 'Email:'), prefeitura_data.get('email')), (self._get_tag('label_tel', 'Tel:'), prefeitura_data.get('tel')), (self._get_tag('label_gentilico', 'Gentílico:'), prefeitura_data.get('gentilico')), (self._get_tag('label_area', 'Área:'), area_formatada)]
    #     ]
    #     for r_idx, row_data in enumerate(data1):
    #         for c_idx, cell_data in enumerate(row_data):
    #             if cell_data:
    #                 tk.Label(table_frame, text=cell_data[0], bg='white', font=("Helvetica", 9, 'bold')).grid(row=r_idx, column=c_idx*2, sticky='e', padx=(5,0), pady=2)
    #                 tk.Label(table_frame, text=(cell_data[1] or ' - '), bg='white', font=("Helvetica", 9)).grid(row=r_idx, column=c_idx*2+1, sticky='w', padx=(2,5), pady=2)
                      
    #     table2_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
    #     table2_frame.pack(fill=tk.X, padx=10)
        
    #     data2 = [
    #         [(self._get_tag('label_idhm_geral', 'IDHM Geral:'), prefeitura_data.get('idhm_geral')), (self._get_tag('label_idhm_longevidade', 'Longevidade:'), prefeitura_data.get('idhm_long')), (self._get_tag('label_mulheres', 'Mulheres:'), fem_formatado)],
    #         [(self._get_tag('label_idhm_renda', 'Renda:'), prefeitura_data.get('idhm_renda')), (self._get_tag('label_idhm_educacao', 'Educação:'), prefeitura_data.get('idhm_educ')), (self._get_tag('label_homens', 'Homens:'), mas_formatado)],
    #         [None, None, (self._get_tag('label_total', 'Total:'), total_formatado)]
    #     ]
    #     for r_idx, row_data in enumerate(data2):
    #         for c_idx, cell_data in enumerate(row_data):
    #             if cell_data:
    #                 tk.Label(table2_frame, text=cell_data[0], bg='white', font=("Helvetica", 9, 'bold')).grid(row=r_idx, column=c_idx*2, sticky='e', padx=(5,0), pady=2)
    #                 tk.Label(table2_frame, text=(str(cell_data[1]) if cell_data[1] is not None else ' - '), bg='white', font=("Helvetica", 9)).grid(row=r_idx, column=c_idx*2+1, sticky='w', padx=(2,5), pady=2)


    def _exibir_relatorio(self, cidade: str, ano_eleicao: int, prefeito: Candidatura | None, vice: Candidatura | None, vereadores: list[Candidatura], ranking_2022: dict[str, list[Candidatura]], candidato_destaque: Pessoa | Candidatura | None, city_data_completo: dict):
        header_frame = tk.Frame(self.parent, bg='white')
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        try:
            logo_to_use = config.CUSTOM_LOGO_PATH if os.path.exists(config.CUSTOM_LOGO_PATH) else config.LOGO_PATH
            logo_img_obj = Image.open(logo_to_use)
            logo_img_obj.thumbnail((300, 100), Image.LANCZOS)
            logo_photo_tk = ImageTk.PhotoImage(logo_img_obj)
            self.images.append(logo_photo_tk) 
            logo_label = tk.Label(header_frame, image=logo_photo_tk, bg='white')
            logo_label.pack(side=tk.LEFT)
        except Exception as e:
            logging.error(f"Erro ao carregar logo no canvas: {e}", exc_info=True)
            tk.Label(header_frame, text="Logo Indisponível", bg='white').pack(side=tk.LEFT)
        
        city_title_frame = tk.Frame(self.parent, bg="#f2f2f2", bd=1, relief='solid')
        city_title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        city_suffix = self._get_tag('title_city_suffix', ' / SP')
        city_title_label = ttk.Label(city_title_frame, text=f"{cidade.upper()}{city_suffix} (Eleição {ano_eleicao})", style="Header.TLabel", background="#f2f2f2")
        city_title_label.pack(pady=4, padx=10, anchor='w', side=tk.LEFT)
        
        dashboard_button = ttk.Button(city_title_frame, text="Visualizar Dashboard", 
                                      command=lambda c=cidade, a=ano_eleicao: self.app.dispatch("open_dashboard", cidade=c, ano=a))
        dashboard_button.pack(pady=4, padx=10, anchor='e', side=tk.RIGHT)
        
        prefeitura_info = city_data_completo.get("prefeitura")
        if prefeitura_info:
            self._create_section_title(self.parent, self._get_tag('title_section_info', "INFORMAÇÕES MUNICIPAIS"))
            self._create_info_tables(self.parent, prefeitura_info)
        
        # --- LÓGICA REFINADA DO CANDIDATO DESTAQUE ---
        if candidato_destaque:
            card = None
            # Se for um objeto Candidatura, ele tem votos e deve ser exibido como tal
            if isinstance(candidato_destaque, Candidatura):
                nome_urna = (candidato_destaque.nome_urna or candidato_destaque.pessoa.apelido or '').upper()
                titulo_destaque = f"VOTAÇÃO {nome_urna} EM {cidade.upper()}"
                self._create_section_title(self.parent, titulo_destaque)
                card = self._create_report_card(self.parent, candidato_destaque)
            # Se for apenas Pessoa, não tem votação no contexto e é exibido como um contato simples
            elif isinstance(candidato_destaque, Pessoa):
                titulo_destaque = (candidato_destaque.apelido or candidato_destaque.nome).upper()
                self._create_section_title(self.parent, titulo_destaque)
                card = self._create_contact_info_card(self.parent, candidato_destaque)
            
            if card: card.pack(fill=tk.X, padx=10, pady=(0,5))
            
        if prefeito or vice or vereadores:
            self._create_section_title(self.parent, f"PODER EXECUTIVO ({ano_eleicao})")
            exec_frame = tk.Frame(self.parent, bg='white')
            exec_frame.pack(fill=tk.X, padx=10)
            exec_frame.grid_columnconfigure(0, weight=1); exec_frame.grid_columnconfigure(1, weight=1)
            if prefeito:
                prefeito_card = self._create_report_card(exec_frame, prefeito)
                if prefeito_card: prefeito_card.grid(row=0, column=0, padx=(0, 2), pady=(0,5), sticky="nsew") 
            if vice:
                vice_card = self._create_report_card(exec_frame, vice)
                if vice_card: vice_card.grid(row=0, column=1, padx=(2, 0), pady=(0,5), sticky="nsew")

            if vereadores:
                self._create_section_title(self.parent, f"PODER LEGISLATIVO ({ano_eleicao})")
                leg_frame = tk.Frame(self.parent, bg='white')
                leg_frame.pack(fill=tk.X, padx=10)
                leg_frame.grid_columnconfigure(0, weight=1); leg_frame.grid_columnconfigure(1, weight=1)
                for i, candidatura_vereador in enumerate(vereadores):
                    col = i % 2; padding = (0, 2) if col == 0 else (2, 0)
                    vereador_card = self._create_report_card(leg_frame, candidatura_vereador)
                    if vereador_card: vereador_card.grid(row=i//2, column=col, padx=padding, pady=(0, 5), sticky="nsew")

        if ranking_2022:
            for cargo, candidaturas in ranking_2022.items():
                if candidaturas:
                    self._create_ranking_section(self.parent, f"TOP 5 - {cargo.title()} ({ano_eleicao})", candidaturas)

    def _create_report_card(self, parent_widget, candidatura: Candidatura | None) -> tk.Frame | None:
        if not candidatura or not candidatura.pessoa: return None 
        pessoa = candidatura.pessoa 
        
        main_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
        photo_tk = self._get_photo_for_card(pessoa)
        if photo_tk:
            photo_label = tk.Label(main_frame, image=photo_tk, bg='white')
        else:
            photo_label = tk.Label(main_frame, text="Foto\nIndisp.", bg='white', width=10, height=5)
        photo_label.pack(side=tk.LEFT, padx=3, pady=3)
        
        info_frame = tk.Frame(main_frame, bg='white')
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        nome_urna = candidatura.nome_urna or ' - '
        num_candidato = str(candidatura.numero_urna) if candidatura.numero_urna else 'S/N'
        tk.Label(info_frame, text=f"{(nome_urna or '').title()} | {num_candidato}", font=("Helvetica", 10, "bold"), bg='white', anchor='w').pack(fill=tk.X, pady=(2,0))
        
        cargo_cand = (candidatura.cargo or ' - ').title()
        partido_cand = candidatura.partido or ''
        votos_f = f"{candidatura.votos:,}".replace(",", ".") if candidatura.votos is not None else '0'
        situacao_f = f"({candidatura.situacao or 'N/A'})"
        linha_2_str = f"{cargo_cand} - {votos_f} votos {situacao_f}"
        linha_3_str = partido_cand

        tk.Label(info_frame, text=linha_2_str, font=("Helvetica", 9), bg='white', anchor='w').pack(fill=tk.X)
        tk.Label(info_frame, text=linha_3_str, font=("Helvetica", 9, "italic"), bg='white', anchor='w').pack(fill=tk.X)
        tk.Label(info_frame, text=(pessoa.nome or ' - ').title(), font=("Helvetica", 9), bg='white', anchor='w').pack(fill=tk.X)

        aniversario_label_tag = self._get_tag('card_label_aniversario', "ANIVERSÁRIO:")
        aniversario_str = f"{aniversario_label_tag} {pessoa.data_nascimento}" if pessoa.data_nascimento else f"{aniversario_label_tag} -"
        idade_val = pessoa.idade
        idade_label_tag = self._get_tag('card_label_idade', "IDADE:")
        idade_suffix_tag = self._get_tag('card_label_idade_suffix', "anos")
        idade_str = f"{idade_label_tag} {idade_val} {idade_suffix_tag}" if idade_val is not None else f"{idade_label_tag} -"
        
        tk.Label(info_frame, text=aniversario_str, font=("Helvetica", 9), bg='white', anchor='w').pack(fill=tk.X)
        tk.Label(info_frame, text=idade_str, font=("Helvetica", 9), bg='white', anchor='w').pack(fill=tk.X)
            
        self._bind_card_to_edit(main_frame, pessoa)
        return main_frame

    def _create_contact_info_card(self, parent_widget, pessoa: Pessoa) -> tk.Frame | None:
        if not pessoa: return None
        
        main_frame = tk.Frame(parent_widget, bg='white', bd=1, relief='solid')
        photo_tk = self._get_photo_for_card(pessoa)
        if photo_tk:
            photo_label = tk.Label(main_frame, image=photo_tk, bg='white')
        else:
            photo_label = tk.Label(main_frame, text="Foto\nIndisp.", bg='white', width=10, height=5)
        photo_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        info_frame = tk.Frame(main_frame, bg='white')
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def add_info_row(label, value):
            if value:
                row = tk.Frame(info_frame, bg='white')
                row.pack(fill='x', anchor='w')
                tk.Label(row, text=f"{label}:", font=("Helvetica", 9, "bold"), bg='white', anchor='w').pack(side='left')
                tk.Label(row, text=value, font=("Helvetica", 9), bg='white', anchor='w', wraplength=300).pack(side='left', padx=5)

        add_info_row("Nome", pessoa.nome)
        add_info_row("Apelido", pessoa.apelido)
        add_info_row("Celular", pessoa.celular)
        add_info_row("E-mail", pessoa.email)
        # --- MUDANÇA: Adiciona Aniversário e Idade ---
        add_info_row("Aniversário", pessoa.data_nascimento)
        idade_str = f"{pessoa.idade} anos" if pessoa.idade is not None else None
        add_info_row("Idade", idade_str)
            
        self._bind_card_to_edit(main_frame, pessoa)
        return main_frame

    def _create_ranking_section(self, parent_widget, title: str, candidaturas: list[Candidatura]):
        self._create_section_title(parent_widget, title)
        leg_frame = tk.Frame(parent_widget, bg='white')
        leg_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        leg_frame.grid_columnconfigure(0, weight=1); leg_frame.grid_columnconfigure(1, weight=1)
        for i, candidatura_obj in enumerate(candidaturas):
            col = i % 2
            padding = (0, 2) if col == 0 else (2, 0)
            card = self._create_report_card(leg_frame, candidatura_obj)
            if card: card.grid(row=i//2, column=col, padx=padding, pady=(0, 5), sticky="nsew")