from dataclasses import dataclass, field, fields # Adicionado 'fields'
import numbers # Adicionado para verificação de tipo numérico

@dataclass(slots=True)
class Organizacao:
    """Representa um único contato do tipo Organização."""
    id_organizacao: int = 0
    nome_fantasia: str = ""
    razao_social: str = ""
    cnpj: str = ""
    email: str = ""
    telefone: str = ""
    website: str = ""
    id_unidade_vinculada: int | None = None
    data_inicio_atividade: str = ""
    notas: str = ""
    cep: str = ""
    endereco: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    
    id_municipio: int | None = None
    tipo_organizacao: str = "" 
    
    latitude: float | None = None
    longitude: float | None = None
    geo_visivel: int = 0  # Padrão é 0 (não visível)
    
    tags: list[str] = field(default_factory=list, repr=False)
    listas: list[str] = field(default_factory=list, repr=False)

    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return cls()
        
        instance = cls()
        for f in fields(cls): # Itera sobre todos os campos da classe
            value = data.get(f.name)
            
            # --- LÓGICA CRÍTICA DE TRATAMENTO DE LATITUDE/LONGITUDE ---
            # Garante que latitude e longitude sejam float ou None
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