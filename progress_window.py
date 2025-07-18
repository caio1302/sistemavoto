import customtkinter as ctk
import threading

class ProgressWindow(ctk.CTkToplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x300")
        self.transient(parent)
        self.grab_set()

        # --- MUDANÇA: Evento para sinalizar a parada ---
        self.stop_event = threading.Event()

        # Impede o fechamento direto enquanto a operação está em andamento
        self.protocol("WM_DELETE_WINDOW", lambda: None) 
        # --- MUDANÇA: Liga o ESC à função de parar ---
        self.bind("<Escape>", self.stop_operation)

        self.status_label = ctk.CTkLabel(self, text="Iniciando operação...", wraplength=550)
        self.status_label.pack(pady=(20, 10), padx=20)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20, fill="x")

        self.details_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.details_label.pack(pady=5, padx=20)

        # Frame para os botões de ação
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)

        # --- MUDANÇA: Adiciona o botão "Parar" ---
        self.stop_button = ctk.CTkButton(button_frame, text="Parar", fg_color="#D32F2F", hover_color="#B71C1C", command=self.stop_operation)
        self.stop_button.pack(side="left", padx=5)
        
        self.close_button = ctk.CTkButton(button_frame, text="Fechar", state="disabled", command=self.destroy)
        self.close_button.pack(side="left", padx=5)
    
    # --- MUDANÇA: Nova função para parar a operação ---
    def stop_operation(self, event=None):
        """Sinaliza para a thread parar e atualiza a UI."""
        if not self.stop_event.is_set():
            self.stop_event.set()
            self.status_label.configure(text="Sinal de parada enviado... Aguardando a finalização da tarefa atual.")
            self.stop_button.configure(state="disabled")

    def start_operation(self, target_function, *args):
        """Inicia a operação em uma thread separada."""
        # A própria instância (self) é passada para a função alvo,
        # para que ela possa chamar os métodos de atualização e verificar o stop_event.
        thread = threading.Thread(target=target_function, args=(*args, self))
        thread.daemon = True
        thread.start()

    def update_progress(self, status, progress, details=""):
        """Atualiza a UI a partir da thread de operação (thread-safe)."""
        if self.winfo_exists():
            # Não atualiza o status se um sinal de parada foi enviado
            if not self.stop_event.is_set():
                self.status_label.configure(text=status)
            self.progress_bar.set(progress)
            self.details_label.configure(text=details)

    def operation_finished(self, success_message="", error_message=""):
        """Atualiza a UI quando a operação termina."""
        if self.winfo_exists():
            if error_message:
                self.status_label.configure(text="Operação Interrompida ou com Erro!")
                self.details_label.configure(text=error_message, text_color="red")
            else:
                self.status_label.configure(text="Operação Concluída!")
                self.details_label.configure(text=success_message)
                self.progress_bar.set(1)
            
            # Reabilita o fechamento da janela e os botões
            self.stop_button.configure(state="disabled")
            self.close_button.configure(state="normal")
            self.protocol("WM_DELETE_WINDOW", self.destroy)
            # Permite que ESC feche a janela agora que a operação terminou
            self.bind("<Escape>", lambda e: self.destroy())