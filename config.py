# --- START OF FILE config.py ---

import os

# -- Base Path --
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# -- File and Folder Paths --
FOTOS_PATH = os.path.join(BASE_PATH, "fotos")
FOTOS_ATUALIZADAS_PATH = os.path.join(BASE_PATH, "fotos_atualizadas")
FOTOS_TSE_CACHE_PATH = os.path.join(BASE_PATH, "fotos_tse_cache")
PLACEHOLDER_PHOTO_PATH = os.path.join(FOTOS_PATH, "foto_nao_disponivel.png")
LOGO_PATH = os.path.join(BASE_PATH, "saulo_logo.png")
CUSTOM_LOGO_PATH = os.path.join(FOTOS_ATUALIZADAS_PATH, "logo_app.png")
SAULO_PHOTO_PATH = os.path.join(BASE_PATH, "saulo.jpeg")

# Arquivos de sessão e cache de usuário
LAST_CITY_PATH = os.path.join(BASE_PATH, "last_city.txt") # Armazena a última cidade selecionada no cerimonial
LAST_SESSION_PATH = os.path.join(BASE_PATH, "session_token.txt") # Armazena o token de sessão para login automático
LOG_FILE_PATH = os.path.join(BASE_PATH, 'app.log') # Caminho para o arquivo de log da aplicação

# -- CSV Paths (Legado) --
CSV_ELEICAO_PATH = os.path.join(BASE_PATH, "eleicao2024.csv")
CSV_VICES_PATH = os.path.join(BASE_PATH, "vices2024.csv")
CSV_SAULO_PATH = os.path.join(BASE_PATH, "saulo2022.csv")
CSV_PREFEITURAS_PATH = os.path.join(BASE_PATH, "prefeituras_sp.csv")
CSV_ELEITORADO_PATH = os.path.join(BASE_PATH, "eleitorado2024.csv")
CSV_CONTATOS_PATH = os.path.join(BASE_PATH, "contato_candidatos.csv")

# -- Cache and Tag Paths --
TAGS_PATH = os.path.join(BASE_PATH, "tags.json")
ACTIVITY_LOG_JSON_PATH = os.path.join(BASE_PATH, 'activity_log.json') 

# -- Font Settings --
FONT_FAMILY = "Helvetica"
FONT_SIZE_NORMAL = 11
FONT_SIZE_BOLD = 12
FONT_SIZE_HEADER = 16

# -- Database Path --
DB_PATH_CONFIG = os.path.join(BASE_PATH, 'dados.db')

# --- Códigos de Eleição do TSE ---
ELECTION_CODES = {
    2024: "2045202024",  # Eleições Municipais 2024
    2022: "2040602022",  # Eleições Gerais 2022
    2020: "2030402020",  # Eleições Municipais 2020
    2018: "2022802018",  # Eleições Gerais 2018
    2016: "2",           # Eleições Municipais 2016
    2014: "680",         # Eleições Gerais 2014
    2012: "1699"         # Eleições Municipais 2012
    # Adicionar outros anos/códigos conforme necessário
}

# --- END OF FILE config.py ---