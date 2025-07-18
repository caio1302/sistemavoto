import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
import webbrowser
import logging
import os
import shutil

import config
from functions import ui_helpers
from changelog import CHANGELOG_TEXT
from tag_definitions import TAG_DEFINITIONS

class EditTagsWindow(tk.Toplevel):
    def __init__(self, parent, repos: dict, app):
        super().__init__(parent)
        self.parent_app = app
        self.repos = repos
        self.tag_definitions_map = TAG_DEFINITIONS 

        self.title("Editar Textos e Rótulos da Interface (Tags UI)")
        self.geometry("900x700")
        
        self.configure(bg="white")
        self.resizable(True, True) 
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        
        self.tag_entry_widgets_map = {} 
        self._create_edit_tags_widgets()
        ui_helpers.center_window(self)
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_mousewheel_for_tags_edit(self, event): 
        if hasattr(self, 'tags_edit_canvas') and self.tags_edit_canvas.winfo_exists():
            self.tags_edit_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _create_edit_tags_widgets(self):
        content_main_frame = tk.Frame(self, bg='white')
        content_main_frame.pack(fill=tk.BOTH, expand=True)

        footer_buttons_frame = tk.Frame(content_main_frame, bg='white', pady=10)
        footer_buttons_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Separator(footer_buttons_frame).pack(side=tk.TOP, fill=tk.X, padx=10)
        
        btn_container_inner = tk.Frame(footer_buttons_frame, bg='white')
        btn_container_inner.pack(pady=(10,0))
        
        ttk.Button(btn_container_inner, text="Salvar Alterações de Tags", command=self._save_ui_tags_action, width=25).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_container_inner, text="Restaurar Padrões", command=self._restore_default_ui_tags_action, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_container_inner, text="Fechar", command=self.destroy, width=15).pack(side=tk.LEFT, padx=10)

        canvas_container_for_tags = tk.Frame(content_main_frame, bg='white')
        canvas_container_for_tags.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.tags_edit_canvas = tk.Canvas(canvas_container_for_tags, bg='white', highlightthickness=0)
        scrollbar_for_tags_canvas = ttk.Scrollbar(canvas_container_for_tags, orient="vertical", command=self.tags_edit_canvas.yview)
        
        self.scrollable_tags_edit_frame = tk.Frame(self.tags_edit_canvas, bg='white')
        self.scrollable_tags_edit_frame.bind("<Configure>", lambda e: self.tags_edit_canvas.configure(scrollregion=self.tags_edit_canvas.bbox("all")))
        self.tags_edit_canvas.bind("<MouseWheel>", self._on_mousewheel_for_tags_edit)
        
        self.tags_canvas_window_item_id = self.tags_edit_canvas.create_window((0, 0), window=self.scrollable_tags_edit_frame, anchor="nw")
        self.tags_edit_canvas.configure(yscrollcommand=scrollbar_for_tags_canvas.set)
        self.tags_edit_canvas.bind("<Configure>", lambda e: self.tags_edit_canvas.itemconfig(self.tags_canvas_window_item_id, width=e.width) if self.tags_edit_canvas.winfo_exists() else None)
        
        self.tags_edit_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_for_tags_canvas.pack(side=tk.RIGHT, fill=tk.Y)

        misc_repo = self.repos.get("misc")
        if not misc_repo: return
        current_tags = misc_repo.get_ui_tags()

        for section_title, tags_in_section_dict in self.tag_definitions_map.items():
            section_label = tk.Label(self.scrollable_tags_edit_frame, text=section_title, font=(config.FONT_FAMILY, 11, "bold", "underline"), bg="white", pady=10, anchor="w")
            section_label.pack(fill=tk.X, pady=(15, 5), padx=5)
            
            grid_frame_for_section = tk.Frame(self.scrollable_tags_edit_frame, bg='white')
            grid_frame_for_section.pack(fill=tk.X, padx=5)
            grid_frame_for_section.columnconfigure(1, weight=1) 

            for i, (tag_id_key, default_tag_text) in enumerate(tags_in_section_dict.items()):
                label_widget = tk.Label(grid_frame_for_section, text=f"{default_tag_text}:", font=(config.FONT_FAMILY, 10, "italic"), fg="#555", bg='white', anchor='e')
                label_widget.grid(row=i, column=0, sticky='we', pady=2, padx=(0,5))
                string_var_for_entry = tk.StringVar(value=current_tags.get(tag_id_key, default_tag_text))
                tag_entry_widget = ttk.Entry(grid_frame_for_section, textvariable=string_var_for_entry, font=(config.FONT_FAMILY, 10))
                tag_entry_widget.grid(row=i, column=1, sticky='we', pady=2)
                self.tag_entry_widgets_map[tag_id_key] = (tag_entry_widget, default_tag_text)

    def _save_ui_tags_action(self):
        tags_to_save_dict = {}
        for tag_id, (entry_widget, default_text) in self.tag_entry_widgets_map.items():
            current_entry_value = entry_widget.get().strip()
            if current_entry_value and current_entry_value != default_text:
                tags_to_save_dict[tag_id] = current_entry_value
        
        misc_repo = self.repos.get("misc")
        if misc_repo and misc_repo.save_ui_tags_to_file(tags_to_save_dict):
            messagebox.showinfo("Sucesso", "Textos salvos com sucesso. Algumas alterações podem requerer que a aplicação seja reiniciada.", parent=self)
            self.destroy()

    def _restore_default_ui_tags_action(self):
        if messagebox.askyesno("Restaurar Padrões", "Isso removerá todas as personalizações de texto da interface. Tem certeza?", parent=self, icon='warning'):
            misc_repo = self.repos.get("misc")
            if misc_repo and misc_repo.delete_ui_tags_file(): 
                messagebox.showinfo("Sucesso", "Textos restaurados para o padrão. Reinicie a aplicação.", parent=self)
                self.destroy()

class ChangelogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Histórico de Atualizações do Sistema")
        self.geometry("800x800")
        self.configure(bg="white")
        self.resizable(True,True) 
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self._create_changelog_widgets()
        ui_helpers.center_window(self)
        self.bind("<Escape>", lambda e: self.destroy())

    def _create_changelog_widgets(self):
        text_area = tk.Text(self, wrap="word", bd=0, padx=15, pady=15, font=(config.FONT_FAMILY, 11),spacing1=2, spacing2=2, spacing3=4)
        text_area.pack(expand=True, fill="both")
        
        text_area.tag_configure('h1', font=(config.FONT_FAMILY, 14, 'bold'), foreground="#003366", spacing3=10, lmargin1=5, lmargin2=5)
        text_area.tag_configure('h2', font=(config.FONT_FAMILY, 12, 'bold'), foreground="#004C99", spacing3=8, lmargin1=10, lmargin2=10)
        text_area.tag_configure('li', lmargin1=20, lmargin2=35) 
        
        for line in CHANGELOG_TEXT.strip().split('\n'):
            stripped_line = line.strip()
            if stripped_line.startswith('# '): 
                text_area.insert(tk.END, f"{stripped_line[2:]}\n\n", 'h1')
            elif stripped_line.startswith('## '): 
                text_area.insert(tk.END, f"{stripped_line[3:]}\n", 'h2')
            elif stripped_line.startswith('- '): 
                text_area.insert(tk.END, f"• {stripped_line[2:]}\n", 'li')
            else: 
                text_area.insert(tk.END, f"{line}\n")
                
        text_area.config(state="disabled") 
        ttk.Button(self, text="Fechar", command=self.destroy, width=10).pack(pady=10)