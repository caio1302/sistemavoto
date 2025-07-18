# --- START OF FILE popups/helpers.py ---

from datetime import datetime, date

# --- MUDANÇA: Remoção da dependência de 'locale' para máxima compatibilidade ---

MONTHS_PT_FULL_MAP = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}
WEEKDAYS_PT_FULL_MAP = {
    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
}

def format_date_with_weekday_robust(date_obj: date) -> str:
    """Formata data como 'DD de Mês (DiaDaSemana)' de forma robusta e sem 'locale'."""
    if not isinstance(date_obj, (datetime, date)): return ""
    
    day = date_obj.day
    month_name = MONTHS_PT_FULL_MAP.get(date_obj.month, str(date_obj.month))
    # weekday() em Python: Segunda é 0, Domingo é 6.
    py_weekday_idx = date_obj.weekday()
    weekday_name_pt = WEEKDAYS_PT_FULL_MAP.get(py_weekday_idx, str(py_weekday_idx))
    
    return f"{day:02d} de {month_name} ({weekday_name_pt})"

# --- END OF FILE popups/helpers.py ---