# Arquivo: dto/candidate.py

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import List # Manter importação de List
from .interaction import Interaction # Corrigido para import relativo

@dataclass(slots=True)
class Candidate:
    # Dados da Tabela 'candidatos' (específicos de uma eleição)
    sq_candidato: str = ""
    ano_eleicao: int = 0
    nome_urna: str = ""
    nome_completo: str = "" # Mantido aqui para dados básicos eleitorais
    partido: str = ""
    cargo: str = ""
    numero: str = ""
    uf: str = ""
    cidade: str = ""
    votos: int = 0
    situacao: str = ""

    # NOVOS CAMPOS AQUI para a tabela candidaturas
    cd_eleicao: str = ""
    ds_eleicao: str = ""
    dt_eleicao: str = ""
    tp_abrangencia: str = ""
    sg_ue: str = ""
    cd_cargo: str = ""
    nm_social_candidato: str = ""
    nr_partido: str = ""
    cd_sit_tot_turno: str = ""

    # Dados da Tabela 'contatos' (dados pessoais/CRM)
    data_nascimento: str = ""
    foto_customizada: str = ""
    endereco: str = ""
    cep: str = ""
    email_principal: str = ""
    email_secundario: str = ""
    celular: str = ""
    telefone_fixo: str = ""
    assessor_principal: str = ""
    telefone_assessor: str = ""
    nivel_relacionamento: str = ""
    responsavel_equipe: str = ""
    origem_contato: str = ""
    areas_interesse: str = ""
    perfil_historico: str = ""
    instagram: str = ""
    facebook: str = ""
    x_twitter: str = ""
    website: str = ""
    observacoes_gerais: str = ""

    # Lista para armazenar as tags associadas (nomes das tags)
    tags: List[str] = field(default_factory=list, repr=False)

    # Lista para armazenar as interações associadas
    interacoes: List[Interaction] = field(default_factory=list, repr=False)

    _raw_data: dict = field(default_factory=dict, repr=False, compare=False) # Para armazenar a linha original do DB

    @property
    def idade(self) -> int | None:
        if not self.data_nascimento: return None
        try:
            birth_date = datetime.strptime(self.data_nascimento, "%d/%m/%Y").date()
            today = datetime.now().date()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, TypeError): return None

    def to_dict(self) -> dict:
        """Converte o objeto para um dicionário, útil para salvar ou serializar."""
        d = {}
        for f in fields(self):
            if not f.name.startswith('_') and f.name not in ['tags', 'interacoes']: # Não incluir campos privados ou listas complexas
                d[f.name] = getattr(self, f.name, None)
        return d

    @classmethod
    def from_dict(cls, data: dict):
        if data is None: data = {}

        init_data = {}
        candidate_fields = {f.name for f in fields(cls)}

        for db_key, value in data.items():
            # Tenta mapear diretamente ou com normalização de caixa
            field_name_direct = db_key.lower()
            field_name_original = db_key

            if field_name_direct in candidate_fields:
                init_data[field_name_direct] = value
            elif field_name_original in candidate_fields: # Caso o nome do campo no DB seja case-sensitive e coincida
                 init_data[field_name_original] = value


        # Mapeamentos específicos para compatibilidade com nomes de colunas CSV/DB antigos
        # Prioriza o que já foi mapeado, depois tenta aliases comuns
        if 'sq_candidato' not in init_data or not init_data['sq_candidato']:
            init_data['sq_candidato'] = data.get('SQ_CANDIDATO')
        if 'ano_eleicao' not in init_data:
            init_data['ano_eleicao'] = data.get('ANO_ELEICAO')
        if 'nome_urna' not in init_data or not init_data['nome_urna']:
            init_data['nome_urna'] = data.get('NOME_URNA') or data.get('NM_URNA_CANDIDATO')
        if 'nome_completo' not in init_data or not init_data['nome_completo']:
            init_data['nome_completo'] = data.get('NOME_COMPLETO') or data.get('NM_CANDIDATO')
        if 'partido' not in init_data or not init_data['partido']:
            init_data['partido'] = data.get('PARTIDO') or data.get('SIGLA_PARTIDO') or data.get('SG_PARTIDO')
        if 'cargo' not in init_data or not init_data['cargo']:
            init_data['cargo'] = data.get('CARGO')
        if 'numero' not in init_data or not init_data['numero']:
            init_data['numero'] = data.get('NUMERO') or data.get('NUM_CANDIDATO') or data.get('NR_CANDIDATO') or data.get('NUM CANDIDATO')
        if 'uf' not in init_data or not init_data['uf']:
            init_data['uf'] = data.get('UF') or data.get('SG_UF')
        if 'cidade' not in init_data or not init_data['cidade']:
            init_data['cidade'] = data.get('CIDADE')
        if 'votos' not in init_data:
            init_data['votos'] = data.get('VOTOS')
        if 'situacao' not in init_data or not init_data['situacao']:
            init_data['situacao'] = data.get('SITUACAO') or data.get('DS_SIT_TOT_TURNO')

        # NOVOS CAMPOS AQUI (da tabela candidaturas)
        if 'cd_eleicao' not in init_data: init_data['cd_eleicao'] = data.get('CD_ELEICAO')
        if 'ds_eleicao' not in init_data: init_data['ds_eleicao'] = data.get('DS_ELEICAO')
        if 'dt_eleicao' not in init_data: init_data['dt_eleicao'] = data.get('DT_ELEICAO')
        if 'tp_abrangencia' not in init_data: init_data['tp_abrangencia'] = data.get('TP_ABRANGENCIA')
        if 'sg_ue' not in init_data: init_data['sg_ue'] = data.get('SG_UE')
        if 'cd_cargo' not in init_data: init_data['cd_cargo'] = data.get('CD_CARGO')
        if 'nm_social_candidato' not in init_data: init_data['nm_social_candidato'] = data.get('NM_SOCIAL_CANDIDATO')
        if 'nr_partido' not in init_data: init_data['nr_partido'] = data.get('NR_PARTIDO')
        if 'cd_sit_tot_turno' not in init_data: init_data['cd_sit_tot_turno'] = data.get('CD_SIT_TOT_TURNO')


        # Campos de 'contatos'
        if 'data_nascimento' not in init_data or not init_data['data_nascimento']:
            init_data['data_nascimento'] = data.get('DT_NASCIMENTO')
        if 'foto_customizada' not in init_data:
             init_data['foto_customizada'] = data.get('foto_customizada') # Já deve ser minúsculo do DB
        # ... outros campos de contato já devem ser mapeados diretamente se vierem do JOIN com nomes corretos

        # Tratamento para inteiros
        try:
            init_data['votos'] = int(init_data.get('votos', 0) or 0)
        except (ValueError, TypeError):
            init_data['votos'] = 0
            
        try:
            init_data['ano_eleicao'] = int(init_data.get('ano_eleicao', 0) or 0)
        except (ValueError, TypeError):
            init_data['ano_eleicao'] = 0

        # Filtra chaves que não são campos do dataclass
        final_init_data = {k: v for k, v in init_data.items() if k in candidate_fields and not k.startswith('_') and k not in ['tags', 'interacoes']}
        
        # Cria a instância, passando os campos explicitamente para o construtor
        # e o dicionário original para _raw_data
        return cls(**final_init_data, _raw_data=data)