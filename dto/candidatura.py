# --- START OF FILE dto/candidatura.py ---

from dataclasses import dataclass, field
from .pessoa import Pessoa # Importa a classe Pessoa

@dataclass(slots=True)
class Candidatura:
    """Representa a participação de uma Pessoa em uma eleição específica."""
    
    # --- Dados da Tabela 'candidaturas' ---
    id_candidatura: int = 0
    id_pessoa: int = 0
    ano_eleicao: int = 0
    sq_candidato: str = ""
    nome_urna: str = ""
    numero_urna: str = ""
    partido: str = ""
    cargo: str = ""
    cidade: str = ""
    uf: str = ""
    votos: int = 0
    situacao: str = ""
    
    # --- Relação com o DTO Pessoa ---
    # Armazena o objeto Pessoa completo associado a esta candidatura.
    pessoa: Pessoa = field(default_factory=Pessoa)

    @classmethod
    def from_dict(cls, data: dict):
        """Cria uma instância de Candidatura a partir de um dicionário."""
        if not data:
            return cls()

        instance = cls()
        # Preenche os campos da candidatura com base nos dados do dicionário
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        # Cria e anexa o objeto Pessoa com base nos mesmos dados do dicionário
        instance.pessoa = Pessoa.from_dict(data)
        
        # Garante que o ID da pessoa na candidatura e no objeto pessoa sejam consistentes
        if instance.pessoa and 'id_pessoa' in data:
            instance.pessoa.id_pessoa = data['id_pessoa']

        return instance
# --- END OF FILE dto/candidatura.py ---