# --- START OF FILE popups/progress_windows.py ---

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import zipfile
import time
import traceback
from pathlib import Path
from datetime import datetime
import os

import config
from functions import ui_helpers

class _ProgressBaseWindow(tk.Toplevel):
    def __init__(self, parent_app, title_text: str):
        super().__init__(parent_app)
        self.parent_app_ref = parent_app 
        self.title(title_text)
        self.geometry("450x180") 
        self.resizable(False, False)
        self.transient(parent_app)
        self.grab_set() 
        self.focus_set()
        
        self.protocol("WM_DELETE_WINDOW", lambda: None) 
        self.bind("<Escape>", lambda e: None) 
        
        ui_helpers.center_window(self) 
        
        style = ttk.Style(self)
        style.configure("TFrame", background='white') # Garante o fundo branco para o frame
        style.configure("Normal.TLabel", background='white')
        
        self.container_frame = ttk.Frame(self, style="TFrame", padding=20)
        self.container_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label_widget = ttk.Label(self.container_frame, text="Iniciando operação...", style="Normal.TLabel", wraplength=400)
        self.status_label_widget.pack(pady=(0, 10), anchor='w', fill=tk.X)
        
        self.progress_bar_widget = ttk.Progressbar(self.container_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar_widget.pack(pady=10, fill=tk.X)
        
        self.details_label_widget = ttk.Label(self.container_frame, text="", style="Normal.TLabel", foreground="grey", wraplength=400)
        self.details_label_widget.pack(pady=(5, 0), anchor='w', fill=tk.X)
        
        self.close_button_widget = ttk.Button(self.container_frame, text="Fechar", command=self.destroy, state="disabled")
        self.close_button_widget.pack(pady=(15, 0))

    def _start_operation_in_thread(self, target_function_ref, *args_for_function):
        self.operation_thread = threading.Thread(target=target_function_ref, args=args_for_function)
        self.operation_thread.daemon = True 
        self.operation_thread.start()

    def _update_progress_display_safe(self, status_message: str, current_progress_value: float, detail_message: str = ""):
        if self.winfo_exists(): 
            self.status_label_widget.config(text=status_message)
            self.progress_bar_widget['value'] = current_progress_value
            self.details_label_widget.config(text=detail_message)
            self.update_idletasks() 

    def _operation_finished_ui_update(self, success_message: str = "", error_message: str = ""):
        if not self.winfo_exists(): return 

        self.progress_bar_widget['value'] = 100 
        if error_message:
            self.status_label_widget.config(text="Erro na Operação!")
            self.details_label_widget.config(text=error_message, foreground="red")
            messagebox.showerror("Erro na Operação", error_message, parent=self)
        else:
            self.status_label_widget.config(text="Operação Concluída!")
            self.details_label_widget.config(text=success_message)
            messagebox.showinfo("Sucesso", success_message, parent=self)
        
        self.close_button_widget.config(state="normal") 
        self.protocol("WM_DELETE_WINDOW", self.destroy) 
        self.bind("<Escape>", lambda e: self.destroy()) 


class BackupProgressWindow(_ProgressBaseWindow):
    def __init__(self, parent_app, selected_extensions: list):
        super().__init__(parent_app, "Criando Backup Completo do Sistema...")
        self.selected_extensions = selected_extensions
        self._start_operation_in_thread(self._execute_backup_logic, self.selected_extensions)

    def _execute_backup_logic(self, extensions_to_include: list):
        try:
            backup_base_dir = Path(config.BASE_PATH) / "backups"
            backup_base_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_zip_filename = backup_base_dir / f"BACKUP_EVOTOS_{timestamp_str}.zip"
            
            self.after(0, self._update_progress_display_safe, "Coletando arquivos para backup...", 2)
            time.sleep(0.1) # Pequena pausa para a UI atualizar

            # --- LÓGICA DE COLETA DE ARQUIVOS REFEITA PARA SER MAIS SEGURA ---
            files_to_backup = []
            base_path_obj = Path(config.BASE_PATH)

            for root, dirs, files in os.walk(base_path_obj):
                # Evita descer para pastas que não queremos no backup
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'venv', 'backups', 'fotos']]
                
                for filename in files:
                    file_path = Path(root) / filename
                    ext = file_path.suffix.lower()

                    # Verifica cada categoria selecionada
                    if ext == '.py' and '.py' in extensions_to_include:
                        files_to_backup.append(file_path)
                    elif ext == '.csv' and '.csv' in extensions_to_include:
                        files_to_backup.append(file_path)
                    elif ext == '.txt' and '.txt' in extensions_to_include:
                        files_to_backup.append(file_path)
                    elif ext == '.json' and '.json' in extensions_to_include:
                        files_to_backup.append(file_path)
                    elif ext == '.html' and '.html' in extensions_to_include:
                        # Exclui o relatório temporário
                        if "relatorio_temp_para_impressao" not in filename:
                            files_to_backup.append(file_path)
                    elif ext == '.css' and '.css' in extensions_to_include:
                        files_to_backup.append(file_path)
                    elif ext == '.db' and '.db' in extensions_to_include:
                        # Garante que é o banco de dados correto
                        if file_path.resolve() == Path(config.DB_PATH_CONFIG).resolve():
                            files_to_backup.append(file_path)
                    elif ext in ['.jpg', '.jpeg', '.png', '.gif'] and 'images' in extensions_to_include:
                        files_to_backup.append(file_path)
            
            final_items_to_backup = list(set(files_to_backup)) # Remove duplicatas se houver
            total_files_to_process = len(final_items_to_backup)
            
            if total_files_to_process == 0:
                self.after(0, lambda: self._operation_finished_ui_update(error_message="Nenhum arquivo correspondente aos filtros foi encontrado para o backup."))
                return

            self.after(0, self._update_progress_display_safe, f"Encontrados {total_files_to_process} arquivos. Iniciando compactação...", 5)
            
            with zipfile.ZipFile(backup_zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for i, file_path_obj in enumerate(final_items_to_backup):
                    arcname_in_zip = file_path_obj.relative_to(base_path_obj)
                    progress_val = 5 + (i / total_files_to_process) * 90
                    
                    self.after(0, self._update_progress_display_safe, 
                               f"Adicionando: {arcname_in_zip}", 
                               progress_val, f"Item {i+1}/{total_files_to_process}")
                    
                    zf.write(file_path_obj, arcname=arcname_in_zip)
                    # Não é necessário um sleep aqui, pois a UI é atualizada via 'after'
            
            success_msg_backup = f"Backup completo criado com sucesso em:\n{backup_zip_filename}"
            self.after(0, lambda: self._operation_finished_ui_update(success_message=success_msg_backup))
        except Exception as e:
            traceback.print_exc()
            error_msg_backup = f"Ocorreu um erro durante o processo de backup:\n{e}"
            self.after(0, lambda: self._operation_finished_ui_update(error_message=error_msg_backup))


class RestoreProgressWindow(_ProgressBaseWindow):
    def __init__(self, parent_app, backup_zip_filepath: str):
        super().__init__(parent_app, "Restaurando Sistema de um Backup...")
        self.backup_filepath_to_restore = backup_zip_filepath
        self._start_operation_in_thread(self._execute_restore_logic)

    def _execute_restore_logic(self):
        try:
            if not Path(self.backup_filepath_to_restore).is_file():
                self.after(0, lambda: self._operation_finished_ui_update(error_message="Arquivo de backup selecionado não encontrado."))
                return

            self.after(0, self._update_progress_display_safe, "Analisando arquivo de backup...", 0)
            
            with zipfile.ZipFile(self.backup_filepath_to_restore, 'r') as zf:
                list_of_files_in_zip = zf.infolist()
                if not list_of_files_in_zip:
                    self.after(0, lambda: self._operation_finished_ui_update(error_message="O arquivo de backup está vazio ou corrompido."))
                    return

                self.after(0, self._update_progress_display_safe, "Iniciando processo de restauração...", 5)
                
                total_files_to_extract = len(list_of_files_in_zip)
                for i, zip_member_info in enumerate(list_of_files_in_zip):
                    target_extraction_path = Path(config.BASE_PATH) / zip_member_info.filename
                    
                    if not str(target_extraction_path.resolve()).startswith(str(Path(config.BASE_PATH).resolve())):
                        raise ValueError(f"Tentativa de extração insegura detectada: '{zip_member_info.filename}' para fora de BASE_PATH.")

                    target_extraction_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    progress_val = 5 + (i / total_files_to_extract) * 90
                    self.after(0, self._update_progress_display_safe, 
                               f"Restaurando arquivo: {Path(zip_member_info.filename).name}", 
                               progress_val, f"{i+1}/{total_files_to_extract}")
                    
                    zf.extract(zip_member_info, Path(config.BASE_PATH)) 
            
            parent_window_for_msg = self.parent_app_ref if self.parent_app_ref.winfo_exists() else self
            self.after(0, lambda: messagebox.showinfo("Restauração Concluída", 
                                                      "Backup restaurado com sucesso.\n\n"
                                                      "É ALTAMENTE RECOMENDÁVEL reiniciar o aplicativo para que todas as alterações tenham efeito.", 
                                                      parent=parent_window_for_msg))
            
            success_msg_restore = "Restauração finalizada. Por favor, reinicie o aplicativo."
            self.after(0, lambda: self._operation_finished_ui_update(success_message=success_msg_restore))

        except Exception as e:
            traceback.print_exc()
            error_msg_restore = f"Ocorreu um erro durante a restauração do backup:\n{e}"
            self.after(0, lambda: self._operation_finished_ui_update(error_message=error_msg_restore))
            
# --- END OF FILE popups/progress_windows.py ---