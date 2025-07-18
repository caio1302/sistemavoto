from dataclasses import dataclass, field, fields
from datetime import datetime
import numbers # Adicionado para verificar tipos numéricos


@dataclass(slots=True)
class Pessoa:
    """
    Representa os dados de identificação e CRM de uma pessoa.
    Inclui campos-chave da última candidatura para conveniência e lookups.
    """
    # --- Dados da Tabela 'pessoas' ---
    id_pessoa: int = 0
    nome: str = ""
    apelido: str = ""
    cpf: str = ""
    data_nascimento: str = ""
    genero: str = ""
    email: str = ""
    celular: str = ""
    telefone_residencial: str = ""
    caminho_foto: str = ""
    notas_pessoais: str = ""
    voto: str = ""
    id_tratamento: int | None = None
    id_profissao: int | None = None
    id_escolaridade: int | None = None
    id_organizacao_trabalho: int | None = None
    rg: str = ""
    titulo_eleitor: str = ""
    
    # --- Endereço e Geolocalização ---
    endereco: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cep: str = ""
    cidade: str = ""
    uf: str = ""
    latitude: float | None = None
    longitude: float | None = None
    geo_visivel: int = 1 

    # --- MUDANÇA: Campos da ÚLTIMA candidatura (campos de conveniência/atalho) ---
    # Estes campos são preenchidos por JOINs e representam a candidatura mais recente.
    id_candidatura: int | None = None
    ano_eleicao: int | None = None
    sq_candidato: str = ""
    nome_urna: str = ""
    numero_urna: str = ""
    partido: str = ""
    cargo: str = ""
    votos: int = 0
    situacao: str = ""
    
    # --- Campos que não vêm da tabela, mas são calculados/unidos ---
    nome_organizacao_trabalho: str = ""
    nome_tratamento: str = ""
    is_candidate: bool = False
    cidade_candidatura_recente: str = ""

    # Listas de dados associados (não são campos do DB, são preenchidas depois)
    historico_candidaturas: list[dict] = field(default_factory=list, repr=False)
    historico_atendimentos: list[dict] = field(default_factory=list, repr=False)
    relacionamentos: list[dict] = field(default_factory=list, repr=False)
    
    @property
    def nome_completo(self) -> str:
        return self.nome

    @property
    def idade(self) -> int | None:
        if not self.data_nascimento: return None
        try:
            birth_date = datetime.strptime(self.data_nascimento, "%d/%m/%Y").date()
            today = datetime.now().date()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, TypeError): return None
        
    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return cls()
        
        instance = cls() 
        for f in fields(cls): # Itera sobre todos os campos da classe
            value = data.get(f.name)
            
            # --- LÓGICA CRÍTICA DE TRATAMENTO DE LATITUDE/LONGITUDE (IDÊNTICA À DE ORGANIZAÇÃO) ---
            if f.name in ('latitude', 'longitude'):
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    setattr(instance, f.name, None) # Strings vazias ou None se tornam None
                elif isinstance(value, numbers.Real): # Se já é um número (float ou int)
                    setattr(instance, f.name, float(value))
                elif isinstance(value, str): # Se é uma string que pode ser um número
                    try:
                        setattr(instance, f.name, float(value))
                    except ValueError:
                        setattr(instance, f.name, None) # Se não for conversível, torna None
                else:
                    setattr(instance, f.name, None) # Qualquer outro tipo inesperado também vira None
            # --- FIM DA LÓGICA DE TRATAMENTO ---
            
            # Para todos os outros campos, atribui o valor diretamente se presente
            elif f.name in data:
                setattr(instance, f.name, value)

        return instance