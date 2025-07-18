# --- START OF FILE dto/task.py ---

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass(slots=True)
class Task:
    """Representa uma única tarefa/agendamento."""
    id_tarefa: int = 0
    sq_candidato: Optional[str] = None # Pode ser None para tarefas não vinculadas
    descricao_tarefa: str = ""
    data_criacao: str = "" # Formato DD/MM/YYYY HH:MM
    data_prazo: str = ""   # Formato DD/MM/YYYY
    responsavel_tarefa: str = ""
    status_tarefa: str = "Pendente" # Valores sugeridos: 'Pendente', 'Em Andamento', 'Concluída', 'Cancelada'
    prioridade_tarefa: str = "Normal" # Valores sugeridos: 'Baixa', 'Normal', 'Alta', 'Urgente'
    notas_tarefa: str = ""

    @classmethod
    def from_dict(cls, data: dict):
        """Cria uma instância de Task a partir de um dicionário (ex: linha do DB)."""
        if data is None:
            data = {}
        
        return cls(
            id_tarefa=data.get('id_tarefa', 0),
            sq_candidato=data.get('sq_candidato'), 
            descricao_tarefa=data.get('descricao_tarefa', ""),
            data_criacao=data.get('data_criacao', datetime.now().strftime("%d/%m/%Y %H:%M")),
            data_prazo=data.get('data_prazo', ""),
            responsavel_tarefa=data.get('responsavel_tarefa', ""),
            status_tarefa=data.get('status_tarefa', "Pendente"),
            prioridade_tarefa=data.get('prioridade_tarefa', "Normal"),
            notas_tarefa=data.get('notas_tarefa', "")
        )

    def to_dict(self) -> dict:
        """Converte a instância de Task em um dicionário."""
        return {
            'id_tarefa': self.id_tarefa,
            'sq_candidato': self.sq_candidato,
            'descricao_tarefa': self.descricao_tarefa,
            'data_criacao': self.data_criacao,
            'data_prazo': self.data_prazo,
            'responsavel_tarefa': self.responsavel_tarefa,
            'status_tarefa': self.status_tarefa,
            'prioridade_tarefa': self.prioridade_tarefa,
            'notas_tarefa': self.notas_tarefa
        }

# --- END OF FILE dto/task.py ---