import customtkinter as ctk

class BackupOptionsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Opções de Backup")
        self.geometry("400x450")
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.result = None

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.main_frame, text="Selecione os tipos de arquivo para incluir:", font=ctk.CTkFont(weight="bold")).pack(pady=(0, 15))

        self.check_vars = {}
        options = {
            ".py": "Arquivos de Código Fonte (.py)",
            ".html": "Arquivos de Template HTML (.html)",
            ".csv": "Arquivos de Dados Originais (.csv)",
            ".css": "Arquivos de Estilo (.css)",
            ".db": "Banco de Dados (.db)",
            ".txt": "Arquivos de Texto e Configuração (.txt)",
            ".json": "Arquivos de Cache e Tags (.json)",
            "images": "Imagens (Logo, Fotos Customizadas, Placeholders)",
        }

        for key, text in options.items():
            var = ctk.BooleanVar(value=True) # Todos marcados por padrão
            cb = ctk.CTkCheckBox(self.main_frame, text=text, variable=var)
            cb.pack(anchor="w", padx=10, pady=5)
            self.check_vars[key] = var

        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(pady=20, side="bottom")
        ctk.CTkButton(button_frame, text="Iniciar Backup", command=self._start_backup).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", command=self.destroy).pack(side="left", padx=5)

    def _start_backup(self):
        self.result = {key: var.get() for key, var in self.check_vars.items()}
        self.destroy()

    def get_selection(self):
        self.wait_window()
        return self.result