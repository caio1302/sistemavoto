# --- START OF FILE functions/ui_helpers.py ---

def center_window(win):
    """Centraliza uma janela Toplevel em relação à janela pai ou à tela."""
    win.update_idletasks() # Garante que as dimensões da janela sejam conhecidas
    width = win.winfo_width()
    height = win.winfo_height()
    
    parent = win.master
    if parent and parent.winfo_viewable(): # Verifica se o pai existe e está visível
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
    else: # Centraliza na tela se não houver pai visível
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
    # Garante que a janela não apareça fora da tela
    x = max(0, x)
    y = max(0, y)
    
    win.geometry(f'{width}x{height}+{x}+{y}')

# --- END OF FILE functions/ui_helpers.py ---