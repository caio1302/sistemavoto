# --- START OF FILE dto/user.py ---

from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class User:
    """Representa um usuário do sistema com seus dados de acesso e permissões."""
    id_usuario: int = 0
    nome_usuario: str = ""
    hash_senha: str = ""
    nome_completo: str = ""
    data_nascimento: str = ""
    telefone: str = ""
    email: str = ""
    caminho_foto: str = ""
    nivel_acesso: str = "assessor" # 'admin', 'coordenador', 'assessor'
    
    # Campos de sessão/token, não precisam estar no __init__ padrão
    login_token: Optional[str] = field(default=None, repr=False)
    token_validade: Optional[str] = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, data: dict):
        """Cria uma instância de User a partir de um dicionário (ex: linha do DB)."""
        if data is None:
            data = {}
        
        return cls(
            id_usuario=data.get('id_usuario', 0),
            nome_usuario=data.get('nome_usuario', ""),
            hash_senha=data.get('hash_senha', ""),
            nome_completo=data.get('nome_completo', ""),
            data_nascimento=data.get('data_nascimento', ""),
            telefone=data.get('telefone', ""),
            email=data.get('email', ""),
            caminho_foto=data.get('caminho_foto', ""),
            nivel_acesso=data.get('nivel_acesso', "assessor"),
            login_token=data.get('login_token'),
            token_validade=data.get('token_validade')
        )

    def to_dict(self) -> dict:
        """Converte a instância de User em um dicionário para salvar no DB."""
        return {
            'id_usuario': self.id_usuario,
            'nome_usuario': self.nome_usuario,
            'hash_senha': self.hash_senha,
            'nome_completo': self.nome_completo,
            'data_nascimento': self.data_nascimento,
            'telefone': self.telefone,
            'email': self.email,
            'caminho_foto': self.caminho_foto,
            'nivel_acesso': self.nivel_acesso,
            'login_token': self.login_token,
            'token_validade': self.token_validade
        }

    @property
    def is_admin(self) -> bool:
        return self.nivel_acesso and self.nivel_acesso.lower() == 'admin'

# --- END OF FILE dto/user.py ---