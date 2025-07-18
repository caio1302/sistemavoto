import customtkinter as ctk
import threading
import os
import logging
from PIL import Image, ImageTk

try:
    import tkintermapview
except ImportError:
    tkintermapview = None

import config
from dto.pessoa import Pessoa
from dto.organizacao import Organizacao

class GeolocalizacaoView(ctk.CTkFrame):
    def __init__(self, parent, repos: dict, app): 
        super().__init__(parent, fg_color="transparent")
        self.repos = repos
        self.app = app 
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        if tkintermapview is None:
            self._show_library_error()
            return

        self._load_marker_icons()
        self._create_widgets()
        
        self.map_widget.set_position(-23.55052, -46.633308) # Posição inicial (São Paulo)
        self.map_widget.set_zoom(7)
        
        self.map_widget.add_left_click_map_command(self.on_marker_click)

        self.load_markers_threaded()

    def on_data_updated(self):
        logging.info("GeolocalizacaoView: Atualizando marcadores devido ao evento 'data_changed'.")
        self.load_markers_threaded()

    def on_marker_click(self, coords):
        pass

    def _load_marker_icons(self):
        self.person_icon = self._create_icon(os.path.join(config.BASE_PATH, "assets", "marker.png"))
        self.org_icon = self._create_icon(os.path.join(config.BASE_PATH, "assets", "org.png"))
        self.pref_icon = self._create_icon(os.path.join(config.BASE_PATH, "assets", "pref.png"))
        
    def _create_icon(self, path):
        if os.path.exists(path):
            try:
                # O tkintermapview requer PhotoImage, não CTkImage
                return ImageTk.PhotoImage(Image.open(path).resize((16, 16), Image.LANCZOS))
            except Exception as e:
                logging.error(f"Erro ao carregar ícone em {path}: {e}")
        else:
            logging.warning(f"Arquivo de ícone não encontrado: {path}")
        return None

    def _show_library_error(self):
        error_label = ctk.CTkLabel(self, 
            text="Erro: A biblioteca 'tkintermapview' é necessária.\nInstale com: pip install tkintermapview",
            font=ctk.CTkFont(size=14), justify="center")
        error_label.place(relx=0.5, rely=0.5, anchor="center")

    def _create_widgets(self):
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(self.control_frame, text="Exibir:").pack(side="left", padx=(0, 5))
        self.show_people_var = ctk.BooleanVar(value=True)
        self.show_orgs_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.control_frame, text="Pessoas", variable=self.show_people_var, command=self.load_markers_threaded).pack(side="left", padx=5)
        ctk.CTkCheckBox(self.control_frame, text="Organizações", variable=self.show_orgs_var, command=self.load_markers_threaded).pack(side="left", padx=5)
        
        ctk.CTkButton(self.control_frame, text="Recarregar Marcadores", command=self.load_markers_threaded).pack(side="left", padx=20)
        self.status_label = ctk.CTkLabel(self.control_frame, text="Carregando...", fg_color=("white", "gray20"), corner_radius=6)

        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=0)
        
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=pt-BR&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        
        self.map_widget.grid(row=1, column=0, sticky="nsew")
        
    def load_markers_threaded(self):
        self.status_label.pack(side="left", padx=10, pady=0)
        self.status_label.configure(text="Buscando contatos...")
        
        threading.Thread(target=self._fetch_data_for_map, daemon=True).start()

    def _fetch_data_for_map(self):
        people_list = []
        orgs_list = []
        
        try:
            person_repo = self.repos.get("person")
            if self.show_people_var.get() and person_repo:
                people_list = person_repo.get_all_geocoded_pessoas()

            org_repo = self.repos.get("organization")
            if self.show_orgs_var.get() and org_repo:
                orgs_list = org_repo.get_all_geocoded_organizacoes()
            
            if self.winfo_exists():
                self.after(0, self._update_map_with_data, people_list, orgs_list)
        except Exception as e:
            logging.error(f"Erro ao buscar dados para o mapa: {e}", exc_info=True) 

    def _update_map_with_data(self, people_list, orgs_list):
        try:
            self.status_label.configure(text="Atualizando mapa...")
            self.map_widget.delete_all_marker()
            
            total_people = 0
            if self.show_people_var.get():
                for pessoa in people_list:
                    command_pessoa = lambda m, pid=pessoa.id_pessoa: self.app.dispatch("open_form", form_name="person", person_id=pid)
                    
                    # --- CORREÇÃO AQUI: Verifica se a latitude/longitude é um número real antes de converter ---
                    # Adicionalmente, verifica se não é string vazia.
                    if (isinstance(pessoa.latitude, (float, int)) or (isinstance(pessoa.latitude, str) and pessoa.latitude.strip())) and \
                       (isinstance(pessoa.longitude, (float, int)) or (isinstance(pessoa.longitude, str) and pessoa.longitude.strip())):
                        
                        try:
                            self.map_widget.set_marker(float(pessoa.latitude), float(pessoa.longitude),
                                                        icon=self.person_icon,
                                                        command=command_pessoa)
                        except ValueError as ve:
                            logging.warning(f"Não foi possível converter Lat/Lon para float para Pessoa ID {pessoa.id_pessoa}: {pessoa.latitude}, {pessoa.longitude}. Erro: {ve}")
                            continue # Pula este marcador se a conversão falhar
                        
                total_people = len(people_list)

            total_orgs = 0
            if self.show_orgs_var.get():
                for org in orgs_list:
                    icon_to_use = self.pref_icon if org.tipo_organizacao == "Prefeitura" else self.org_icon
                    command_org = lambda m, oid=org.id_organizacao: self.app.dispatch("open_form", form_name="organization", org_id=oid)
                    
                    # --- CORREÇÃO AQUI: Verifica se a latitude/longitude é um número real antes de converter ---
                    if (isinstance(org.latitude, (float, int)) or (isinstance(org.latitude, str) and org.latitude.strip())) and \
                       (isinstance(org.longitude, (float, int)) or (isinstance(org.longitude, str) and org.longitude.strip())):
                        try:
                            self.map_widget.set_marker(float(org.latitude), float(org.longitude),
                                                            icon=icon_to_use,
                                                            command=command_org)
                        except ValueError as ve:
                            logging.warning(f"Não foi possível converter Lat/Lon para float para Org ID {org.id_organizacao}: {org.latitude}, {org.longitude}. Erro: {ve}")
                            continue # Pula este marcador
                total_orgs = len(orgs_list)

            self.status_label.configure(text=f"{total_people} pessoas e {total_orgs} organizações no mapa.")
            self.after(3000, lambda: self.status_label.pack_forget())
        except Exception as e:
            # Capture any remaining exceptions during marker drawing
            logging.error(f"Erro ao desenhar marcadores: {e}", exc_info=True)