import zipfile
from datetime import datetime
from pathlib import Path
import os
import logging

import config

def execute_backup_thread(options: dict, progress_win):
    """
    Função executada em uma thread para criar um backup.
    Verifica a cada passo se a interrupção foi solicitada pelo usuário.
    """
    try:
        progress_win.after(0, lambda: progress_win.update_progress("Coletando arquivos...", 0.05))
        files_to_backup = []
        base_path = Path(config.BASE_PATH)
        excluded_dirs = {'__pycache__', 'backups', '.venv', 'venv', 'archive', 'auxiliares'}
        
        selected_exts = {ext for ext, checked in options.items() if checked and ext.startswith('.')}
        include_images = options.get("images", False)

        for root, dirs, files in os.walk(base_path):
            # --- MUDANÇA: Verifica o sinal de parada durante a coleta de arquivos ---
            if progress_win.stop_event.is_set():
                logging.info("Coleta de arquivos para backup interrompida.")
                progress_win.after(0, lambda: progress_win.operation_finished("", "Coleta de arquivos cancelada pelo usuário."))
                return

            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for filename in files:
                file_path = Path(root) / filename
                ext = file_path.suffix.lower()
                if ext in selected_exts:
                    files_to_backup.append(file_path)
                elif include_images and ext in ['.png', '.jpg', '.jpeg', '.ico', '.gif']:
                    if any(folder in str(file_path) for folder in ['assets', 'fotos_atualizadas', 'fotos_tse_cache']):
                        files_to_backup.append(file_path)

        if not files_to_backup:
            progress_win.after(0, lambda: progress_win.operation_finished("", "Nenhum arquivo encontrado para as opções selecionadas."))
            return

        backup_base_dir = base_path / "backups"
        backup_base_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        zip_path = backup_base_dir / f"evotos_backup_{timestamp}.zip"
        
        total_files = len(files_to_backup)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for i, file_path in enumerate(files_to_backup):
                # --- MUDANÇA: Verifica o sinal de parada a cada arquivo ---
                if progress_win.stop_event.is_set():
                    logging.info("Operação de backup interrompida pelo usuário durante a compactação.")
                    break
                
                progress = (i + 1) / total_files
                progress_win.after(0, lambda p=progress, fn=file_path.name, i=i, t=total_files: progress_win.update_progress(f"Compactando: {fn}", p, f"{i+1} de {t}"))
                arcname = file_path.relative_to(base_path)
                zf.write(file_path, arcname)
        
        # --- MUDANÇA: Verifica se a operação foi parada antes de dar a mensagem final ---
        if progress_win.stop_event.is_set():
            progress_win.after(0, lambda: progress_win.operation_finished("", "Backup interrompido pelo usuário."))
            try:
                os.remove(zip_path) # Apaga o arquivo de backup parcial
                logging.info(f"Backup parcial '{zip_path}' removido.")
            except OSError as e:
                logging.warning(f"Não foi possível remover o backup parcial: {e}")
        else:
            success_msg = f"Backup criado com sucesso em:\n{zip_path}"
            progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
    except Exception as e:
        error_msg = f"Ocorreu um erro: {e}"
        logging.error(f"Erro no backup: {e}", exc_info=True)
        progress_win.after(0, lambda: progress_win.operation_finished("", error_msg))

def execute_restore_thread(backup_path: str, progress_win):
    """
    Função executada em uma thread para restaurar um backup.
    Verifica a cada passo se a interrupção foi solicitada pelo usuário.
    """
    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            file_list = zf.infolist()
            total_files = len(file_list)
            for i, member in enumerate(file_list):
                # --- MUDANÇA: Verifica o sinal de parada a cada arquivo ---
                if progress_win.stop_event.is_set():
                    logging.info("Operação de restauração interrompida pelo usuário.")
                    break
                
                progress = (i + 1) / total_files
                progress_win.after(0, lambda p=progress, m=member.filename, i=i, t=total_files: progress_win.update_progress(f"Restaurando: {m}", p, f"{i+1} de {t}"))
                # A extração é atômica para cada arquivo, então o risco de corrupção é baixo.
                zf.extract(member, config.BASE_PATH)

        # --- MUDANÇA: Verifica se a operação foi parada antes de dar a mensagem final ---
        if progress_win.stop_event.is_set():
            progress_win.after(0, lambda: progress_win.operation_finished("", "Restauração interrompida pelo usuário. Alguns arquivos podem ter sido restaurados. É recomendado reiniciar."))
        else:
            success_msg = "Restauração concluída. É necessário reiniciar a aplicação."
            progress_win.after(0, lambda: progress_win.operation_finished(success_msg))
            
    except Exception as e:
        error_msg = f"Ocorreu um erro durante a restauração: {e}"
        logging.error(f"Erro na restauração: {e}", exc_info=True)
        progress_win.after(0, lambda: progress_win.operation_finished("", error_msg))