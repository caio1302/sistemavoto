import re

def validate_cpf(cpf: str) -> bool:
    """Valida um CPF brasileiro. Retorna True se válido, False caso contrário."""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    
    try:
        # Cálculo do primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10) % 11
        if digito1 == 10: digito1 = 0
        if digito1 != int(cpf[9]):
            return False
            
        # Cálculo do segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10) % 11
        if digito2 == 10: digito2 = 0
        if digito2 != int(cpf[10]):
            return False
    except (ValueError, TypeError):
        return False
        
    return True

def validate_email(email: str) -> bool:
    """Valida um formato de e-mail usando uma expressão regular simples."""
    if not email: return True # Permite campo vazio
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def _apply_mask_template(value, template):
    """
    Função auxiliar genérica para aplicar máscaras.
    value: string atual no campo (já contendo apenas dígitos).
    template: string da máscara (ex: "(##) # ####-####"). '#' indica dígito.
    """
    if not value:
        return ""

    formatted_value = []
    val_idx = 0
    for char_template in template:
        if val_idx >= len(value):
            break
        
        if char_template == '#':
            formatted_value.append(value[val_idx])
            val_idx += 1
        else:
            # Insere o caractere da máscara se ainda houver dígitos para formatar
            # ou se for o próximo caractere a ser inserido.
            if len(formatted_value) < len(template.replace("#", "") + value):
                 formatted_value.append(char_template)

    return "".join(formatted_value)

def format_telefone(p_s: str) -> str:
    """Formata a string para o padrão de telefone (XX) XXXX-XXXX."""
    digits = re.sub(r'\D', '', p_s)
    return _apply_mask_template(digits, "(##) ####-####")

def format_celular(p_s: str) -> str:
    """Formata a string para o padrão de celular (XX) X XXXX-XXXX."""
    digits = re.sub(r'\D', '', p_s)
    if len(digits) > 10:
        return _apply_mask_template(digits, "(##) # ####-####")
    return _apply_mask_template(digits, "(##) ####-####")

def format_cpf(p_s: str) -> str:
    """Formata a string para o padrão de CPF ###.###.###-##."""
    digits = re.sub(r'\D', '', p_s)
    return _apply_mask_template(digits, "###.###.###-##")

def format_cep(p_s: str) -> str:
    """Formata a string para o padrão de CEP XXXXX-XXX."""
    digits = re.sub(r'\D', '', p_s)
    return _apply_mask_template(digits, "#####-###")

def format_date_input(p_s: str) -> str:
    """Formata a string para o padrão de data DD/MM/YYYY."""
    digits = re.sub(r'\D', '', p_s)
    return _apply_mask_template(digits, "##/##/####")

def format_cnpj(p_s: str) -> str:
    """Formata a string para o padrão de CNPJ ##.###.###/####-##."""
    digits = re.sub(r'\D', '', p_s)
    return _apply_mask_template(digits, "##.###.###/####-##")