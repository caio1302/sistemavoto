# --- START OF FILE dto/interaction.py ---

from dataclasses import dataclass, field
from datetime import datetime

@dataclass(slots=True)
class Interaction:
    """Representa uma única interação com um contato."""
    id_interacao: int = 0
    sq_candidato: str = ""
    data_interacao: str = "" # Formato DD/MM/YYYY HH:MM ou DD/MM/YYYY
    tipo_interacao: str = "" # Ex: 'Ligação', 'Reunião', 'WhatsApp'
    descricao: str = ""
    responsavel_interacao: str = "" # Quem da equipe fez o contato

    @classmethod
    def from_dict(cls, data: dict):
        """Cria uma instância de Interaction a partir de um dicionário (ex: linha do DB)."""
        if data is None:
            data = {}
        
        return cls(
            id_interacao=data.get('id_interacao', 0),
            sq_candidato=data.get('sq_candidato', ""),
            data_interacao=data.get('data_interacao', ""),
            tipo_interacao=data.get('tipo_interacao', ""),
            descricao=data.get('descricao', ""),
            responsavel_interacao=data.get('responsavel_interacao', "")
        )

    def to_dict(self) -> dict:
        """Converte a instância de Interaction em um dicionário."""
        return {
            'id_interacao': self.id_interacao,
            'sq_candidato': self.sq_candidato,
            'data_interacao': self.data_interacao,
            'tipo_interacao': self.tipo_interacao,
            'descricao': self.descricao,
            'responsavel_interacao': self.responsavel_interacao
        }

# --- END OF FILE dto/interaction.py ---