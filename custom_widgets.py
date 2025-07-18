import customtkinter as ctk
import tkinter as tk
import unicodedata
import logging

def _normalize(s: str) -> str:
    """Função auxiliar para normalizar texto, removendo acentos e convertendo para maiúsculas."""
    if not isinstance(s, str): s = str(s)
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').upper()

#==============================================================================
# CLASSE CTkScrollableComboBox (Layout e Posição Corrigidos)
#==============================================================================
class CTkScrollableComboBox(ctk.CTkFrame):
    def __init__(self, master, values=None, command=None, variable=None, **kwargs):
        frame_keys = {"width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color"}
        frame_kwargs = {k: v for k, v in kwargs.items() if k in frame_keys}
        super().__init__(master, **frame_kwargs)

        self.values = values or []
        self.command = command
        self.variable = variable
        self.search_string = ""
        self.last_key_time = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        entry_keys = {"font", "text_color", "placeholder_text"}
        entry_kwargs = {k: v for k, v in kwargs.items() if k in entry_keys}
        entry_kwargs['state'] = "readonly"

        self.entry = ctk.CTkEntry(self, **entry_kwargs)
        self.entry.grid(row=0, column=0, sticky="ew")

        self.dropdown: ctk.CTkToplevel | None = None
        self.listbox: tk.Listbox | None = None

        if self.variable:
            self._set_entry_value(self.variable.get())
        elif self.values:
            self._set_entry_value(self.values[0])

        btn_height = self.entry.cget('height')
        self.arrow_button = ctk.CTkButton(self, text="▼", width=btn_height, height=btn_height, command=self._toggle_dropdown)
        self.arrow_button.grid(row=0, column=1, padx=(4, 0))

        self.entry.bind("<Button-1>", lambda e: self._open_dropdown())

    def _toggle_dropdown(self):
        if self.dropdown and self.dropdown.winfo_exists():
            self._close_dropdown()
        else:
            self._open_dropdown()

    def _open_dropdown(self):
        if self.dropdown and self.dropdown.winfo_exists():
            return

        self.dropdown = ctk.CTkToplevel(self)
        self.dropdown.overrideredirect(True)
        self.dropdown.attributes("-topmost", True)

        self.update_idletasks()
        
        x_pos = self.winfo_rootx()
        y_pos = self.winfo_rooty() + self.winfo_height() + 2
        width_size = self.winfo_width()
        
        self.dropdown.geometry(f"{width_size}x0+{x_pos}+{y_pos}")

        list_frame = ctk.CTkFrame(self.dropdown, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        listbox_bg, listbox_fg, listbox_select_bg, listbox_select_fg, border_color = self._get_listbox_colors()
        
        self.listbox = tk.Listbox(list_frame, 
                                  bg=listbox_bg, fg=listbox_fg,
                                  selectbackground=listbox_select_bg, selectforeground=listbox_select_fg,
                                  highlightthickness=1, highlightbackground=border_color,
                                  borderwidth=0, relief="flat", activestyle="none",
                                  font=self.entry.cget("font"), exportselection=False)
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y", padx=(0,2), pady=2)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(2,0), pady=2)

        self._populate_listbox_data_only()

        self.listbox.bind("<ButtonRelease-1>", self._on_item_select_from_listbox)
        self.listbox.bind("<Return>", self._on_item_select_from_listbox)
        
        self._global_click_bind_id = self.winfo_toplevel().bind("<Button-1>", self._handle_global_click, add="+")
        self.listbox.focus_set()

    def _get_listbox_colors(self):
        mode = 1 if ctk.get_appearance_mode() == "Dark" else 0
        return (ctk.ThemeManager.theme["CTkFrame"]["fg_color"][mode], 
                ctk.ThemeManager.theme["CTkLabel"]["text_color"][mode], 
                ctk.ThemeManager.theme["CTkButton"]["fg_color"][mode], 
                ctk.ThemeManager.theme["CTkButton"]["text_color"][mode], 
                ctk.ThemeManager.theme["CTkEntry"]["border_color"][mode])

    def _on_item_select_from_listbox(self, event):
        if self.listbox and self.listbox.curselection():
            value = self.listbox.get(self.listbox.curselection())
            self._select_item(value)

    def _close_dropdown(self, event=None):
        if hasattr(self, "_global_click_bind_id"):
            self.winfo_toplevel().unbind("<Button-1>", self._global_click_bind_id)
        if self.dropdown and self.dropdown.winfo_exists():
            self.dropdown.destroy()
            self.dropdown = None

    def _select_item(self, value):
        self._set_entry_value(value)
        if self.command: self.command(value)
        self._close_dropdown()

    def get(self) -> str: return self.entry.get()
    
    def _set_entry_value(self, value: str):
        original_state = self.entry.cget("state")
        self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value or "")
        self.entry.configure(state=original_state)
        if self.variable: self.variable.set(value or "")

    def set(self, value: str):
        self._set_entry_value(value)

    def configure(self, **kwargs):
        if 'values' in kwargs:
            self.values = kwargs.pop('values')
        super().configure(**kwargs)

    def _populate_listbox_data_only(self):
        if not self.listbox or not self.listbox.winfo_exists(): return
        self.listbox.delete(0, tk.END)
        for value in self.values: self.listbox.insert(tk.END, value)

        current_val = self.get()
        if current_val in self.values:
            idx = self.values.index(current_val)
            self.listbox.see(idx)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)

        if self.dropdown and self.dropdown.winfo_exists():
            font_obj = self.entry.cget("font")
            item_height = font_obj.metrics("linespace") + 4
            num_items = len(self.values)
            desired_height = min(num_items, 8) * item_height + 4
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height() + 2
            width = self.winfo_width()
            self.dropdown.geometry(f"{width}x{desired_height}+{x}+{y}")

    def _handle_global_click(self, event):
        if self.dropdown and self.dropdown.winfo_exists():
            x, y, w, h = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height()
            if not (x <= event.x_root <= x + w and y <= event.y_root <= y + h):
                self._close_dropdown()

#==============================================================================
# CLASSE CTkAutocompleteComboBox (COM A CORREÇÃO DE LÓGICA E ERRO)
#==============================================================================
class CTkAutocompleteComboBox(ctk.CTkFrame):
    def __init__(self, master, values=None, command=None, variable=None, **kwargs):
        frame_keys = {"width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color"}
        entry_keys = {"font", "text_color", "placeholder_text", "state"}
        frame_kwargs = {k: v for k, v in kwargs.items() if k in frame_keys}
        entry_kwargs = {k: v for k, v in kwargs.items() if k in entry_keys}
        super().__init__(master, **frame_kwargs)

        self.all_values = values or []
        self._command = command
        self._variable = variable
        self._after_job = None
        self._user_made_selection = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.entry = ctk.CTkEntry(self, **entry_kwargs)
        self.entry.grid(row=0, column=0, sticky="ew")

        btn_height = self.entry.cget('height')
        self.arrow_button = ctk.CTkButton(self, text="▼", width=btn_height, height=btn_height, command=self._toggle_dropdown)
        self.arrow_button.grid(row=0, column=1, padx=(4, 0))

        self._toplevel: ctk.CTkToplevel | None = None
        self._listbox: tk.Listbox | None = None
        
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Return>", self._on_enter_key)
        self.entry.bind("<FocusIn>", self._open_dropdown)
        
        if self._variable:
            self.entry.insert(0, self._variable.get() or "")

    def destroy(self):
        if hasattr(self, "_global_click_bind_id"):
             try: self.winfo_toplevel().unbind("<Button-1>", self._global_click_bind_id)
             except tk.TclError: pass
        super().destroy()

    def _on_key_release(self, event):
        if not (self._toplevel and self._toplevel.winfo_exists()):
            self._open_dropdown()
        if event.keysym in ("Up", "Down"): self._handle_navigation(event.keysym); return
        if event.keysym in ("Return", "Escape", "Tab"): return
        if self._after_job: self.after_cancel(self._after_job)
        self._after_job = self.after(100, self._autocomplete)

    def _autocomplete(self):
        # --- LÓGICA DE AUTOCOMPLETE CORRIGIDA ---
        # Não interfere mais com a digitação, apenas seleciona na lista.
        current_text = self.entry.get()
        if not self._listbox: return

        if not current_text:
            self._listbox.selection_clear(0, tk.END)
            return

        normalized_text = _normalize(current_text)
        
        # Encontra o primeiro item correspondente na lista de valores completa
        first_match = next((v for v in self.all_values if _normalize(v).startswith(normalized_text)), None)

        if first_match:
            # Encontra o índice do item correspondente na listbox visível
            listbox_items = self._listbox.get(0, tk.END)
            try:
                idx = listbox_items.index(first_match)
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(idx)
                self._listbox.see(idx)
            except ValueError:
                # O item correspondente não está na lista (pode acontecer se a lista for filtrada no futuro)
                self._listbox.selection_clear(0, tk.END)
        else:
            self._listbox.selection_clear(0, tk.END)

    def _handle_navigation(self, key):
        if not self._listbox: return
        cur_selection = self._listbox.curselection()
        cur_idx = cur_selection[0] if cur_selection else -1
        if key == "Down": next_idx = cur_idx + 1 if cur_idx < self._listbox.size() - 1 else 0
        elif key == "Up": next_idx = cur_idx - 1 if cur_idx > 0 else self._listbox.size() - 1
        else: return
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(next_idx)
        self._listbox.see(next_idx)
        selected_value = self._listbox.get(next_idx)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, selected_value)
        self.entry.select_range(0, tk.END) # --- CORREÇÃO DO ERRO DE DIGITAÇÃO AQUI ---
        self._user_made_selection = True

    def _on_enter_key(self, event=None):
        if self._listbox and self._listbox.curselection():
            self._select_item_from_listbox()
        else:
            self._confirm_selection(self.entry.get(), user_selected=True)

    def _confirm_selection(self, value, user_selected=False):
        self._user_made_selection = user_selected
        if self._user_made_selection:
            self.set(value, update_var=True)
        self._close_dropdown()
        self.entry.icursor(tk.END)
        self.entry.selection_clear()
        
    def _toggle_dropdown(self):
        if self._toplevel and self._toplevel.winfo_exists():
            self._close_dropdown()
        else:
            self._open_dropdown()

    def _open_dropdown(self, event=None):
        if self._toplevel and self._toplevel.winfo_exists(): return
        self._user_made_selection = False
        self._create_toplevel_and_listbox()
        self._populate_listbox()
        self._global_click_bind_id = self.winfo_toplevel().bind("<Button-1>", self._handle_global_click, add="+")
        
    def _create_toplevel_and_listbox(self):
        self._toplevel = ctk.CTkToplevel(self)
        self._toplevel.overrideredirect(True)
        self._toplevel.wm_attributes("-topmost", True)
        self.update_idletasks()
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        width = self.winfo_width()
        
        list_frame = ctk.CTkFrame(self._toplevel, fg_color="transparent")
        list_frame.pack(expand=True, fill="both")
        
        mode = 1 if ctk.get_appearance_mode() == "Dark" else 0
        listbox_bg = ctk.ThemeManager.theme["CTkFrame"]["fg_color"][mode]
        listbox_fg = ctk.ThemeManager.theme["CTkLabel"]["text_color"][mode]
        listbox_select_bg = ctk.ThemeManager.theme["CTkButton"]["fg_color"][mode]
        listbox_select_fg = ctk.ThemeManager.theme["CTkButton"]["text_color"][mode]
        border_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"][mode]

        self._listbox = tk.Listbox(list_frame, 
                                 bg=listbox_bg, fg=listbox_fg,
                                 selectbackground=listbox_select_bg, selectforeground=listbox_select_fg,
                                 highlightthickness=1, highlightbackground=border_color,
                                 borderwidth=0, relief="flat", activestyle="none",
                                 font=self.entry.cget("font"), exportselection=False)

        scrollbar = ctk.CTkScrollbar(list_frame, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self._listbox.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        
        font_obj = self.entry.cget("font")
        item_height = font_obj.metrics("linespace") + 4
        num_items = len(self.all_values)
        height = min(num_items, 8) * item_height + 4
        self._toplevel.geometry(f"{width}x{height}+{x}+{y}")
        
        self._listbox.bind("<ButtonRelease-1>", lambda e: self._select_item_from_listbox())
        self._listbox.bind("<Escape>", lambda e: self._close_dropdown())

    def _populate_listbox(self):
        if not self._listbox: return
        self._listbox.delete(0, tk.END)
        for value in self.all_values:
            self._listbox.insert(tk.END, value)
        current_value = self.entry.get()
        if current_value in self.all_values:
            try:
                idx = self.all_values.index(current_value)
                self._listbox.selection_set(idx); self._listbox.see(idx)
            except ValueError: pass

    def _close_dropdown(self, event=None):
        if hasattr(self, "_global_click_bind_id"):
            self.winfo_toplevel().unbind("<Button-1>", self._global_click_bind_id)
            delattr(self, "_global_click_bind_id")
        if self._toplevel and self._toplevel.winfo_exists():
            self._toplevel.destroy()
            self._toplevel = None
        if not self._user_made_selection and self._variable:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self._variable.get() or "")

    def _select_item_from_listbox(self):
        if self._listbox and self._listbox.curselection():
            selected_value = self._listbox.get(self._listbox.curselection())
            self._confirm_selection(selected_value, user_selected=True)
            
    def _handle_global_click(self, event):
        if self._toplevel and self._toplevel.winfo_exists():
            x, y, w, h = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height()
            tx, ty, tw, th = self._toplevel.winfo_rootx(), self._toplevel.winfo_rooty(), self._toplevel.winfo_width(), self._toplevel.winfo_height()
            if not ((x <= event.x_root <= x + w and y <= event.y_root <= y + h) or \
                    (tx <= event.x_root <= tx + tw and ty <= event.y_root <= ty + th)):
                self._close_dropdown()

    def get(self):
        return self.entry.get()

    def set(self, value, update_var=False):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value or "")
        if self._variable and update_var:
            self._variable.set(value or "")
        if self._command and update_var:
            self._command(value)

    def configure(self, **kwargs):
        if 'values' in kwargs:
            self.all_values = kwargs.pop('values')
            if self._listbox and self._listbox.winfo_exists():
                self._populate_listbox()
        if 'variable' in kwargs:
            self._variable = kwargs.pop('variable')
            if self._variable: self.set(self._variable.get())
        if 'command' in kwargs:
            self._command = kwargs.pop('command')
        
        entry_keys = {"font", "text_color", "placeholder_text", "state"}
        entry_kwargs = {k: v for k, v in kwargs.items() if k in entry_keys}
        if entry_kwargs: self.entry.configure(**entry_kwargs)
        
        frame_keys = {"width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color"}
        frame_kwargs = {k: v for k, v in kwargs.items() if k in frame_keys}
        if frame_kwargs: super().configure(**frame_kwargs)