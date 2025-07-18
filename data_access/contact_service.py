import sqlite3
import logging
from tkinter import messagebox
from pathlib import Path
import os
import shutil
import re

import config
from dto.pessoa import Pessoa
from dto.organizacao import Organizacao
from functions import ui_helpers, formatters, data_helpers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person_repository import PersonRepository
    from .organization_repository import OrganizationRepository
    from .misc_repository import MiscRepository
    from .geo_service import GeoService

class ContactService:
    def __init__(self, repos: dict):
        self.repos = repos

    def process_and_save_person(self, raw_data: dict, list_ids: list[int], new_photo_path: str | None) -> Pessoa | None:
        """
        Recebe dados brutos do formulário, processa-os, converte nomes em IDs e orquestra o salvamento.
        """
        try:
            misc_repo: 'MiscRepository' = self.repos.get("misc")
            if not misc_repo:
                logging.error("MiscRepository não encontrado no ContactService.")
                return None
            
            tratamento_map = {item['nome']: item['id'] for item in misc_repo.get_lookup_table_data("tratamentos")}
            profissao_map = {item['nome']: item['id'] for item in misc_repo.get_lookup_table_data("profissoes")}
            escolaridade_map = {item['nome']: item['id'] for item in misc_repo.get_lookup_table_data("escolaridades")}
            
            pessoa_obj = raw_data.get('pessoa_obj', Pessoa())

            for field, value in raw_data.items():
                if field == 'pessoa_obj' or not hasattr(pessoa_obj, field):
                    continue

                if field == 'id_tratamento':
                    setattr(pessoa_obj, field, tratamento_map.get(value))
                elif field == 'id_profissao':
                    setattr(pessoa_obj, field, profissao_map.get(value))
                elif field == 'id_escolaridade':
                    setattr(pessoa_obj, field, escolaridade_map.get(value))
                # Correção para gênero vindo do SegmentedButton
                elif field == 'genero' and isinstance(value, str):
                    setattr(pessoa_obj, field, value.lower())
                else:
                    setattr(pessoa_obj, field, value)
            
            saved_pessoa = self._save_person_contact_internal(pessoa_obj, list_ids, new_photo_path)
            
            # --- REMOVIDA LÓGICA ASSÍNCRONA AQUI ---
            # A geocodificação para salvamento de contato individual agora ocorre
            # DE FORMA SÍNCRONA dentro de _save_person_contact_internal.
            # O código assíncrono só é mantido para geocodificação EM MASSA.
            
            return saved_pessoa
            
        except Exception as e:
            logging.error(f"Erro ao processar e salvar pessoa: {e}", exc_info=True)
            messagebox.showerror("Erro de Processamento", f"Ocorreu um erro inesperado ao processar os dados do contato: {e}")
            return None

    def _save_person_contact_internal(self, pessoa: Pessoa, list_ids: list[int], new_photo_path: str | None) -> Pessoa | None:
        person_repo: 'PersonRepository' = self.repos.get("person")
        if not person_repo: return None
        
        # Primeiro salva todos os dados textuais/numéricos, exceto lat/lon que podem estar pendentes
        saved_pessoa = person_repo.save_pessoa(pessoa)
        if not saved_pessoa:
            logging.error(f"Falha ao salvar a entidade principal da pessoa: {pessoa.nome}")
            return None
        
        # Agora, lida com a lógica da foto
        if new_photo_path:
            if new_photo_path == "DELETE":
                person_repo.clear_person_photo_path(saved_pessoa.id_pessoa)
                if saved_pessoa.caminho_foto:
                    try:
                        file_to_remove = Path(config.BASE_PATH) / saved_pessoa.caminho_foto
                        if file_to_remove.exists():
                            os.remove(file_to_remove)
                    except OSError as e:
                        logging.warning(f"Não foi possível remover o arquivo de foto antigo {saved_pessoa.caminho_foto}: {e}")
                saved_pessoa.caminho_foto = None
            else:
                photo_db_path = self._save_photo_file(new_photo_path, saved_pessoa.id_pessoa)
                if photo_db_path and photo_db_path != saved_pessoa.caminho_foto:
                    person_repo.update_pessoa_photo_path(saved_pessoa.id_pessoa, photo_db_path)
                    saved_pessoa.caminho_foto = photo_db_path
        
        # --- LÓGICA SÍNCRONA DE GEOCÓDIGO APLICADA AQUI ---
        # Se a geolocalização está ativa e as coordenadas não estão preenchidas, busca e salva.
        geo_service: 'GeoService' = self.repos.get("geo")
        if saved_pessoa.geo_visivel == 1 and (saved_pessoa.latitude is None or saved_pessoa.longitude is None) and geo_service:
            logging.info(f"Geocodificando PESSOA ID {saved_pessoa.id_pessoa} de forma síncrona...")
            # Chama o método de geocodificação. Este método salva NO BANCO DE DADOS
            # e atualiza o OBJETO saved_pessoa EM MEMÓRIA com as coordenadas ou NULL.
            geo_service.geocode_and_save_entity(saved_pessoa)
        
        # Finalmente, associa as listas
        person_repo.update_list_associations_for_pessoa(saved_pessoa.id_pessoa, list_ids)
        
        return saved_pessoa

    def save_organization(self, org_dto: Organizacao) -> Organizacao | None:
        org_repo: 'OrganizationRepository' = self.repos.get("organization")
        if not org_repo: return None

        try:
            saved_org = org_repo.save_organizacao(org_dto)
            if not saved_org:
                logging.error(f"Falha ao salvar a organização: {org_dto.nome_fantasia}")
                return None
                
            # --- LÓGICA SÍNCRONA DE GEOCÓDIGO APLICADA AQUI PARA ORGANIZAÇÕES ---
            # Se a geolocalização está ativa e as coordenadas não estão preenchidas, busca e salva.
            geo_service: 'GeoService' = self.repos.get("geo")
            if saved_org.geo_visivel == 1 and (saved_org.latitude is None or saved_org.longitude is None) and geo_service:
                 logging.info(f"Geocodificando ORGANIZAÇÃO ID {saved_org.id_organizacao} de forma síncrona...")
                 # Chama o método de geocodificação. Este método salva NO BANCO DE DADOS
                 # e atualiza o OBJETO saved_org EM MEMÓRIA com as coordenadas ou NULL.
                 geo_service.geocode_and_save_entity(saved_org)

            return saved_org
        except Exception as e:
            logging.error(f"Erro no serviço ao salvar organização: {e}", exc_info=True)
            messagebox.showerror("Erro de Serviço", f"Ocorreu um erro ao salvar a organização: {e}")
            return None

    def _save_photo_file(self, temp_photo_path: str, person_id: int) -> str | None:
        if not temp_photo_path or not person_id: return None
        try:
            if not os.path.exists(temp_photo_path):
                logging.error(f"Arquivo de origem da foto não encontrado: {temp_photo_path}")
                return None
                
            dest_folder = Path(config.FOTOS_ATUALIZADAS_PATH)
            dest_folder.mkdir(exist_ok=True)
            file_extension = Path(temp_photo_path).suffix
            dest_filename = f"pessoa_{person_id}{file_extension}"
            dest_path_abs = dest_folder / dest_filename
            
            shutil.copy(temp_photo_path, dest_path_abs)
            
            return os.path.join("fotos_atualizadas", dest_filename).replace("\\", "/")
        except Exception as e:
            messagebox.showwarning("Erro de Foto", f"Ocorreu um erro ao salvar a nova foto: {e}")
            logging.error(f"Erro ao copiar foto para pessoa ID {person_id}: {e}", exc_info=True)
            return None