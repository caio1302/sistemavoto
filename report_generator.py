import base64
from pathlib import Path
from tkinter import messagebox
import os
from datetime import datetime
import logging

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from functions import data_helpers
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura

class ReportGenerator:
    def __init__(self, repos: dict):
        self.repos = repos
        self.logo_base64 = self._encode_logo()
        
        template_dir = os.path.join(config.BASE_PATH, 'style')
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.jinja_env.globals['get_photo_uri'] = self._get_photo_uri_from_candidatura
        self.jinja_env.globals['now'] = datetime.now()
        
        # --- MUDANÇA CRÍTICA AQUI: Adiciona as classes e a função isinstance ao ambiente Jinja ---
        # Isso permite usar 'isinstance(objeto, Classe)' diretamente nos templates.
        self.jinja_env.globals['Pessoa'] = Pessoa
        self.jinja_env.globals['Candidatura'] = Candidatura
        self.jinja_env.globals['isinstance'] = isinstance # Adiciona a função isinstance

        try:
            self.jinja_env.globals['macros'] = self.jinja_env.get_template('macros.html').module
        except Exception as e:
            logging.error(f"Erro ao carregar macros.html: {e}", exc_info=True)
            self.jinja_env.globals['macros'] = None

    def _get_tag(self, tag_id, default_text):
        misc_repo = self.repos.get("misc")
        if misc_repo:
            return misc_repo.get_ui_tags().get(tag_id, default_text)
        return default_text

    def _encode_logo(self):
        logo_to_use = config.CUSTOM_LOGO_PATH if os.path.exists(config.CUSTOM_LOGO_PATH) else config.LOGO_PATH
        try:
            with open(logo_to_use, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            logging.warning(f"Arquivo de logo não encontrado em '{logo_to_use}'.")
            return ""

    def _get_photo_uri_from_candidatura(self, obj: Candidatura | Pessoa | None) -> str:
        pessoa = None
        if isinstance(obj, Candidatura):
            pessoa = obj.pessoa
        elif isinstance(obj, Pessoa):
            pessoa = obj
            
        if not pessoa:
            return Path(config.PLACEHOLDER_PHOTO_PATH).as_uri()
        
        return self._get_photo_uri_for_pessoa(pessoa)


    def _get_photo_uri_for_pessoa(self, pessoa: Pessoa) -> str:
        """Busca o caminho da foto para um objeto Pessoa."""
        if not pessoa: 
            return Path(config.PLACEHOLDER_PHOTO_PATH).as_uri()
        
        path_str = data_helpers.get_candidate_photo_path(pessoa, self.repos)
        path_obj = Path(path_str)
        if path_obj.exists() and path_obj.is_file():
            return path_obj.as_uri()
        else:
            return Path(config.PLACEHOLDER_PHOTO_PATH).as_uri()

    def generate_html(self, report_data: dict) -> str:
        d = report_data
        
        prefeitura_data = d.get('prefeitura_data', {})
        if prefeitura_data:
            populacao = prefeitura_data.get('populacao')
            area = prefeitura_data.get('area')
            densidade_formatada = ' - '
            if populacao and area and area > 0:
                densidade_calculada = populacao / area
                densidade_formatada = f"{densidade_calculada:,.2f} hab/km²".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                densidade_db = prefeitura_data.get('dens_demo')
                if densidade_db: densidade_formatada = f"{densidade_db} hab/km²"
            prefeitura_data['densidade_demografica_calculada'] = densidade_formatada
            
            pop_val = prefeitura_data.get('populacao')
            prefeitura_data['populacao_formatada'] = f"{pop_val:,}".replace(",", ".") if isinstance(pop_val, int) else ' - '
            
            area_val = prefeitura_data.get('area')
            area_suffix = self._get_tag('label_area_suffix', "KM²")
            prefeitura_data['area_formatada'] = f"{area_val:,.2f} {area_suffix}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(area_val, (int, float)) else ' - '
            
            eleitorado_fem = prefeitura_data.get('eleitorado_feminino')
            eleitorado_mas = prefeitura_data.get('eleitorado_masculino')
            eleitorado_total = prefeitura_data.get('eleitorado_total')
            prefeitura_data['eleitorado_feminino_formatado'] = f"{eleitorado_fem:,}".replace(",", ".") if eleitorado_fem is not None else '0'
            prefeitura_data['eleitorado_masculino_formatado'] = f"{eleitorado_mas:,}".replace(",", ".") if eleitorado_mas is not None else '0'
            prefeitura_data['eleitorado_total_formatado'] = f"{eleitorado_total:,}".replace(",", ".") if eleitorado_total is not None else '0'

        css_content = ""
        css_path = os.path.join(config.BASE_PATH, 'style', 'report.css')
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
        except FileNotFoundError:
            logging.warning(f"Aviso: Arquivo CSS do relatório não encontrado em: {css_path}")

        cidade_nome = d.get('cidade', '').upper()
        proprietario = d.get('candidato_destaque')
        titulo_proprietario = ""
        
        if proprietario:
            if isinstance(proprietario, Candidatura):
                nome_urna_destaque = (proprietario.nome_urna or proprietario.pessoa.apelido or '').upper()
                titulo_proprietario = f"VOTAÇÃO {nome_urna_destaque} EM {cidade_nome}"
            elif isinstance(proprietario, Pessoa):
                 titulo_proprietario = (proprietario.apelido or proprietario.nome).upper()

        context = {
            'css_content': css_content,
            'cidade_upper_com_sufixo': f"{cidade_nome}{self._get_tag('title_city_suffix', ' / SP')}",
            'ano_eleicao': d.get('ano_eleicao'),
            'logo_base64': self.logo_base64,
            'prefeitura_data': prefeitura_data,
            'candidato_destaque': proprietario,
            'titulo_proprietario': titulo_proprietario,
            'tags': self.repos.get("misc").get_ui_tags() if self.repos.get("misc") else {}
        }

        if d.get("rankings"):
            template = self.jinja_env.get_template('report_template_federal.html')
            context['rankings'] = d.get('rankings')
        else:
            template = self.jinja_env.get_template('report_template.html')
            vereadores = d.get('vereadores', [])
            vereadores_por_pagina = 16 
            vereadores_primeira_pagina = 8
            pages = []
            if vereadores:
                page1_vereadores = vereadores[:vereadores_primeira_pagina]
                pages.append({'vereadores': page1_vereadores})
                vereadores_restantes = vereadores[vereadores_primeira_pagina:]
                if vereadores_restantes:
                    for i in range(0, len(vereadores_restantes), vereadores_por_pagina):
                        chunk = vereadores_restantes[i:i + vereadores_por_pagina]
                        pages.append({'vereadores': chunk})
            else:
                pages.append({'vereadores': []})
            
            context.update({
                'pages': pages,
                'ano_eleicao_municipal': d.get('ano_eleicao_municipal'),
                'prefeito': d.get('prefeito'),
                'vice': d.get('vice_prefeito')
            })
        
        return template.render(context)