import unicodedata
from datetime import datetime
from pathlib import Path
import os
import logging
import requests
import time
from requests.adapters import HTTPAdapter, Retry

import config
from dto.pessoa import Pessoa
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from data_access.misc_repository import MiscRepository

def normalize_city_key(text):
    if not isinstance(text, str): return ""
    # --- MUDANÇA CRÍTICA AQUI ---
    # Substitui qualquer apóstrofo por um espaço, conforme a lógica da sua consulta SQL.
    text = text.replace("'", " ") 
    nfkd_form = unicodedata.normalize('NFD', text.upper())
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).strip()

def normalize_csv_row(row):
    return {k.strip().upper(): v.strip() if v else '' for k, v in row.items() if k}

def calculate_age(birth_date_str):
    if not birth_date_str: return None 
    try:
        birth_date = datetime.strptime(birth_date_str, "%d/%m/%Y").date()
        today = datetime.now().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except (ValueError, TypeError): return None

def safe_int(value, default=0):
    if value is None or value == '': return default
    try:
        return int(str(value).split('.')[0])
    except (ValueError, TypeError): return default

# MUDANÇA: o corpo desta função foi alterado para se alinhar com a nova lógica de busca de URL.
def get_candidate_photo_path(pessoa: Pessoa, repos: dict) -> str:
    """
    Localiza o caminho da foto de um candidato, com a seguinte prioridade e lógica de fallback.
    """
    if pessoa.caminho_foto:
        abs_path = Path(config.BASE_PATH) / pessoa.caminho_foto
        if abs_path.is_file():
            return str(abs_path)
    sq_cand_proprietario, num_urna_proprietario = '250001604965', '5515'
    if (hasattr(pessoa, 'sq_candidato') and pessoa.sq_candidato == sq_cand_proprietario) or \
            (hasattr(pessoa, 'numero_urna') and pessoa.numero_urna == num_urna_proprietario):
        return config.SAULO_PHOTO_PATH
    if not (hasattr(pessoa, 'ano_eleicao') and pessoa.ano_eleicao and hasattr(pessoa,
                                                                              'sq_candidato') and pessoa.sq_candidato):
        return config.PLACEHOLDER_PHOTO_PATH
    cache_dir = Path(config.FOTOS_TSE_CACHE_PATH)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_photo_path = cache_dir / f"{pessoa.ano_eleicao}_{pessoa.sq_candidato}.jpg"
    if cached_photo_path.is_file():
        return str(cached_photo_path)
    time.sleep(0.1)  # Pequena pausa para não sobrecarregar
    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        misc_repo = repos.get("misc")
        cidade = getattr(pessoa, 'cidade_candidatura_recente', None) or pessoa.cidade
        uf_candidatura = getattr(pessoa, 'uf', 'SP')  # Default para SP se não houver
        cod_municipio_tse = misc_repo.get_municipio_cod_tse(cidade) if misc_repo and cidade else None

        cod_eleicao = str(config.ELECTION_CODES.get(pessoa.ano_eleicao, "0"))
        # MUDANÇA: esta seção foi reescrita para refletir as diferentes URLs
        # que você forneceu.
        url_base = "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img"
        ano = str(pessoa.ano_eleicao)

        url_params_a_tentar = []

        if ano == "2024" or ano == "2020" or ano == "2016":
            # Formato municipal: precisa do código do município
            if cod_municipio_tse:
                url_params_a_tentar.append(
                    f"/{cod_eleicao}/{pessoa.sq_candidato}/{cod_municipio_tse}")

        elif ano == "2022" or ano == "2018" or ano == "2014":
            # Formato estadual/federal: precisa da UF
            url_params_a_tentar.append(
                f"/{cod_eleicao}/{pessoa.sq_candidato}/SP")

        for params in url_params_a_tentar:
            url = f"{url_base}{params}"
            logging.debug(f"Tentando baixar foto de: {pessoa.nome_urna} {pessoa.sq_candidato} - {url}")
            try:
                response = session.get(url, timeout=10, headers=headers)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    with open(cached_photo_path, 'wb') as f:
                        f.write(response.content)
                    logging.info(
                        f"Foto de : {pessoa.ano_eleicao};{pessoa.nome_urna};{pessoa.sq_candidato};{pessoa.cidade}")
                    return str(cached_photo_path)
                else:
                    logging.warning(
                        f"URL falhou (Status: {response.status_code}): {url}")
            except requests.exceptions.RequestException as req_e:
                logging.warning(
                    f"Exceção de requisição para a URL {url}: {req_e}")
            time.sleep(0.5)

    except Exception as e:
        logging.error(
            f"Erro inesperado no processo de busca de foto para {pessoa.nome}: {e}", exc_info=True)

    return config.PLACEHOLDER_PHOTO_PATH