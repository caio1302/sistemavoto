import tkinter as tk
from tkinter import ttk, messagebox

import config
from functions import ui_helpers, data_helpers

class GlobalSearchWindow(tk.Toplevel):
    def __init__(self, parent_app, repos: dict, ano_eleicao_referencia: int):
        super().__init__(parent_app)
        # MODIFICADO: Recebe 'repos'
        self.parent_app_ref = parent_app
        self.repos = repos
        self.ano_eleicao_ref_search = ano_eleicao_referencia

        # MODIFICADO: Busca a tag de uma fonte consistente (app)
        title_prefix = self.parent_app_ref.get_tag("global_search_window_title_prefix", "Busca Global de Candidatos")
        self.title(f"{title_prefix} (Eleição Referência: {ano_eleicao_referencia})")
        self.geometry("950x600")
        self.configure(bg="white")
        self.transient(parent_app)
        self.grab_set()
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        ui_helpers.center_window(self)
        self._create_global_search_widgets()

    def _create_global_search_widgets(self):
        search_options_frame = ttk.Frame(self, style="TFrame", padding="10")
        search_options_frame.pack(fill=tk.X)
        
        ttk.Label(search_options_frame, text="Buscar por:", style="Normal.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.search_term_var = tk.StringVar()
        search_entry_widget = ttk.Entry(search_options_frame, textvariable=self.search_term_var, width=40, font=(config.FONT_FAMILY, 10))
        search_entry_widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        search_entry_widget.bind("<Return>", self.perform_global_search) 
        
        self.search_criterion_var = tk.StringVar(value="Nome") 
        search_criteria_options = ["Nome", "Partido", "Cidade"] 
        
        criteria_radio_frame = ttk.Frame(search_options_frame, style="TFrame")
        criteria_radio_frame.pack(side=tk.LEFT)
        for crit_opt_text in search_criteria_options:
            ttk.Radiobutton(criteria_radio_frame, text=crit_opt_text, variable=self.search_criterion_var, value=crit_opt_text).pack(side=tk.LEFT, padx=5)
            
        ttk.Button(search_options_frame, text="Buscar", command=self.perform_global_search, width=12).pack(side=tk.LEFT, padx=5)

        results_display_frame = ttk.Frame(self, style="TFrame", padding="10")
        results_display_frame.pack(fill=tk.BOTH, expand=True)
        
        results_cols = ("Nome Urna", "Cargo", "Partido", "Cidade", "Ano Eleição", "Votos")
        self.results_treeview = ttk.Treeview(results_display_frame, columns=results_cols, show="headings", selectmode="browse")
        
        col_widths_map = {"Nome Urna": 250, "Cargo": 150, "Partido": 100, "Cidade": 180, "Ano Eleição": 80, "Votos": 80}
        col_anchors_map = {"Nome Urna": 'w', "Cargo": 'w', "Partido": 'center', "Cidade": 'w', "Ano Eleição": 'center', "Votos": 'e'}
        for col_id in results_cols:
            self.results_treeview.heading(col_id, text=col_id)
            self.results_treeview.column(col_id, width=col_widths_map.get(col_id, 150), anchor=col_anchors_map.get(col_id, 'w'), stretch=tk.YES if col_id == "Nome Urna" else tk.NO)
            
        vsb_results = ttk.Scrollbar(results_display_frame, orient="vertical", command=self.results_treeview.yview)
        self.results_treeview.configure(yscrollcommand=vsb_results.set)
        
        self.results_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_results.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_treeview.bind("<Double-1>", self.on_result_double_click) 
        search_entry_widget.focus_set() 

    def perform_global_search(self, event=None): 
        search_term_str = self.search_term_var.get().strip()
        search_criterion_str = self.search_criterion_var.get()
        
        if not search_term_str:
            messagebox.showwarning("Busca Inválida", "Por favor, digite um termo para a busca.", parent=self)
            return

        for item in self.results_treeview.get_children(): 
            self.results_treeview.delete(item)
            
        person_repo = self.repos.get("person")
        if not person_repo:
            messagebox.showerror("Erro", "Repositório de Pessoas não encontrado.")
            return

        search_results_list = person_repo.search_candidates(search_term_str, search_criterion_str, self.ano_eleicao_ref_search)
        
        if not search_results_list:
            messagebox.showinfo("Sem Resultados", f"Nenhum candidato encontrado para '{search_term_str}' usando o critério '{search_criterion_str}'.", parent=self)
            return
            
        for cand_obj in search_results_list:
            iid_tree = f"{cand_obj.sq_candidato}_{cand_obj.ano_eleicao}_{data_helpers.normalize_city_key(cand_obj.cidade)}"
            
            votos_display = f"{cand_obj.votos:,}".replace(",", ".") if cand_obj.votos is not None else "0"
            values_for_row = (
                (cand_obj.nome_urna or "").title(),
                (cand_obj.cargo or "").title(),
                cand_obj.partido or "",
                (cand_obj.cidade or "").title(),
                str(cand_obj.ano_eleicao or ""),
                votos_display
            )
            self.results_treeview.insert("", "end", iid=iid_tree, values=values_for_row)

    def on_result_double_click(self, event=None):
        selected_item_iid = self.results_treeview.focus()
        if not selected_item_iid: return
        
        try:
            sq_cand_from_iid, ano_eleicao_from_iid_str, cidade_normalizada_from_iid = selected_item_iid.split('_', 2)
            ano_eleicao_from_iid_int = int(ano_eleicao_from_iid_str)
            
            item_values = self.results_treeview.item(selected_item_iid, 'values')
            cidade_original_from_tree = item_values[3] 

            person_repo = self.repos.get("person")
            if not person_repo: return

            candidate_to_edit = person_repo.get_candidate_by_sq(sq_cand_from_iid, ano_eleicao_from_iid_int, cidade_original_from_tree)
            
            if candidate_to_edit:
                # MODIFICADO: Usa o sistema de eventos para abrir o formulário
                self.parent_app_ref.dispatch("open_form", form_name="person", pessoa_dto=candidate_to_edit, parent_view=self)
            else:
                messagebox.showerror("Erro ao Carregar", f"Não foi possível carregar dados completos do candidato.", parent=self)
        except (ValueError, IndexError) as e:
            messagebox.showerror("Erro de ID", f"O ID do item selecionado na lista é inválido: {selected_item_iid}\nDetalhes: {e}", parent=self)