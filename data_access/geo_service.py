import sqlite3
import logging
import time
import threading
from tkinter import messagebox

from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderQuotaExceeded

from dto.pessoa import Pessoa
from dto.organizacao import Organizacao

# Para Type Hinting
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ..modules.person_form_window import PersonFormWindow

class GeoService:
    def __init__(self, conn: sqlite3.Connection, api_key: str):
        self.conn = conn
        if not api_key:
            raise ValueError("A chave de API do Google não foi fornecida na inicialização do GeoService.")
        
        self.geolocator = GoogleV3(api_key=api_key)
        self.api_key = api_key

    def _geocode_address(self, address_to_search: str) -> tuple[float | None, float | None]:
        if not address_to_search or len(address_to_search.split(',')) < 2:
            logging.warning(f"Endereço inválido ou insuficiente para geocodificação: '{address_to_search}'")
            return None, None
        try:
            # time.sleep(0.01) 
            location = self.geolocator.geocode(address_to_search, timeout=1, language='pt-BR')
            
            if location:
                logging.info(f"Endereço '{address_to_search}' geocodificado para: ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
            else:
                logging.warning(f"Nenhum resultado para o endereço: '{address_to_search}'")
        except GeocoderQuotaExceeded:
            logging.error(f"Cota da API do Google excedida. Verifique seu painel do Google Cloud.")
            raise
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logging.error(f"Erro de serviço no geocoding para '{address_to_search}': {e}")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erro inesperado durante geocoding para '{address_to_search}': {e}")
        return None, None
        
    def geocode_and_save_entity_threaded(self, entity: Pessoa | Organizacao, ui_callback: Callable = None):
        threading.Thread(target=self.geocode_and_save_entity, args=(entity, ui_callback), daemon=True).start()

    def geocode_and_save_entity(self, entity: Pessoa | Organizacao, ui_callback: Callable = None) -> bool:
        """
        Geocodifica e salva as coordenadas para uma única Pessoa ou Organização.
        Pode receber um ui_callback para atualizar a interface (ex: preencher lat/lon).
        """
        address_parts_priority = []
        address_parts_fallback = []

        if isinstance(entity, Pessoa):
            if entity.endereco and entity.endereco.strip(): address_parts_priority.append(entity.endereco)
            if entity.numero and entity.numero.strip(): address_parts_priority.append(entity.numero)
            if entity.complemento and entity.complemento.strip(): address_parts_priority.append(entity.complemento)
            if entity.bairro and entity.bairro.strip(): address_parts_priority.append(entity.bairro)
            if entity.cidade and entity.cidade.strip(): address_parts_priority.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts_priority.append(entity.uf)
            
            if entity.cidade and entity.cidade.strip(): address_parts_fallback.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts_fallback.append(entity.uf)
            else: address_parts_fallback.append("SP")

        elif isinstance(entity, Organizacao):
            if entity.endereco and entity.endereco.strip(): address_parts_priority.append(entity.endereco)
            if entity.numero and entity.numero.strip(): address_parts_priority.append(entity.numero)
            if entity.complemento and entity.complemento.strip(): address_parts_priority.append(entity.complemento)
            if entity.bairro and entity.bairro.strip(): address_parts_priority.append(entity.bairro)
            if entity.cidade and entity.cidade.strip(): address_parts_priority.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts_priority.append(entity.uf)

            if entity.cidade and entity.cidade.strip(): address_parts_fallback.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts_fallback.append(entity.uf)
            else: address_parts_fallback.append("SP")

        address_str = ", ".join(address_parts_priority)
        if not address_str or len(address_str.split(',')) < 2:
            address_str = ", ".join(address_parts_fallback)
            
        if not address_str or len(address_str.split(',')) < 1: 
            logging.warning(f"Não há informações de endereço suficientes para geocodificar a entidade ID {getattr(entity, 'id_pessoa', getattr(entity, 'id_organizacao', 'N/A'))}.")
            if ui_callback:
                 ui_callback(None, None)
            return False

        lat, lon = self._geocode_address(address_str)

        if lat is not None and lon is not None:
            entity.latitude, entity.longitude = lat, lon

            try:
                with self.conn:
                    id_to_update = getattr(entity, 'id_pessoa', getattr(entity, 'id_organizacao', None))
                    table_name = "pessoas" if isinstance(entity, Pessoa) else "organizacoes"
                    id_column = "id_pessoa" if isinstance(entity, Pessoa) else "id_organizacao"
                    
                    self.conn.execute(f"UPDATE {table_name} SET latitude = ?, longitude = ? WHERE {id_column} = ?", (lat, lon, id_to_update))
                
                if ui_callback:
                    ui_callback(lat, lon)
                return True
            except sqlite3.Error as e:
                logging.error(f"Erro ao salvar coordenadas no DB para {type(entity).__name__} ID {id_to_update}: {e}")
                if ui_callback:
                    ui_callback(None, None)
                return False
        else: # Se a geocodificação falhou ou retornou None (não encontrado)
            try:
                with self.conn:
                    id_to_update = getattr(entity, 'id_pessoa', getattr(entity, 'id_organizacao', None))
                    table_name = "pessoas" if isinstance(entity, Pessoa) else "organizacoes"
                    id_column = "id_pessoa" if isinstance(entity, Pessoa) else "id_organizacao"
                    
                    self.conn.execute(f"UPDATE {table_name} SET latitude = NULL, longitude = NULL WHERE {id_column} = ?", (id_to_update,))
                
                if ui_callback:
                    ui_callback(None, None)
                return False
            except sqlite3.Error as e:
                logging.error(f"Erro ao limpar coordenadas no DB para {type(entity).__name__} ID {id_to_update} após falha: {e}")
                if ui_callback:
                    ui_callback(None, None)
                return False

    def geocode_all_contacts(self, progress_win):
        try:
            class InterruptedError(Exception): pass

            cursor = self.conn.cursor()
            # --- MUDANÇA AQUI: Adicionado a condição `geo_visivel = 1` ---
            cursor.execute("SELECT * FROM pessoas WHERE geo_visivel = 1 AND (latitude IS NULL OR longitude IS NULL) AND (cidade IS NOT NULL AND cidade != '' OR uf IS NOT NULL AND uf != '')")
            people_to_geocode = [Pessoa.from_dict(dict(row)) for row in cursor.fetchall()]

            total = len(people_to_geocode)
            if total == 0:
                progress_win.after(0, lambda: progress_win.operation_finished("Todos os contatos visíveis com endereço já possuem coordenadas."))
                return

            success_count = 0
            for i, pessoa in enumerate(people_to_geocode):
                if progress_win.stop_event.is_set(): raise InterruptedError

                progress = (i + 1) / total
                progress_win.after(0, lambda p=pessoa.nome, pr=progress, i=i, t=total: progress_win.update_progress(f"Geocodificando: {p}", pr, f"Pessoa {i+1}/{t}"))
                
                if self.geocode_and_save_entity(pessoa): 
                    success_count += 1
            
            final_message = f"Geocodificação de Pessoas concluída!\n{success_count} de {total} contatos visíveis foram atualizados."
            progress_win.after(0, lambda msg=final_message: progress_win.operation_finished(msg))
        
        except InterruptedError:
             progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada pelo usuário."))
        except GeocoderQuotaExceeded:
            progress_win.after(0, lambda: progress_win.operation_finished("", "ERRO: Cota da API do Google Maps excedida. A operação foi parada."))
        except Exception as e:
            error_message = f"Um erro ocorreu durante o processo: {e}"
            logging.error(error_message, exc_info=True)
            progress_win.after(0, lambda err=error_message: progress_win.operation_finished("", err))

    def geocode_all_organizations(self, progress_win):
        try:
            class InterruptedError(Exception): pass
            
            cursor = self.conn.cursor()
            # --- MUDANÇA AQUI: Adicionado a condição `geo_visivel = 1` ---
            cursor.execute("SELECT * FROM organizacoes WHERE geo_visivel = 1 AND (latitude IS NULL OR longitude IS NULL) AND (cidade IS NOT NULL AND cidade != '' OR uf IS NOT NULL AND uf != '')")
            orgs_to_geocode = [Organizacao.from_dict(dict(row)) for row in cursor.fetchall()]

            total = len(orgs_to_geocode)
            if total == 0:
                progress_win.after(0, lambda: progress_win.operation_finished("Todas as organizações visíveis com endereço já possuem coordenadas."))
                return

            success_count = 0
            for i, org in enumerate(orgs_to_geocode):
                if progress_win.stop_event.is_set(): raise InterruptedError

                progress = (i + 1) / total
                progress_win.after(0, lambda o=org.nome_fantasia, p=progress, i=i, t=total: progress_win.update_progress(f"Geocodificando: {o}", p, f"Organização {i+1}/{t}"))
                
                if self.geocode_and_save_entity(org): 
                    success_count += 1

            final_message = f"Geocodificação de Organizações concluída!\n{success_count} de {total} organizações visíveis foram atualizadas."
            progress_win.after(0, lambda msg=final_message: progress_win.operation_finished(msg))

        except InterruptedError:
             progress_win.after(0, lambda: progress_win.operation_finished("", "Operação cancelada pelo usuário."))
        except GeocoderQuotaExceeded:
            progress_win.after(0, lambda: progress_win.operation_finished("", "ERRO: Cota da API do Google Maps excedida. A operação foi parada."))
        except Exception as e:
            error_message = f"Um erro ocorreu durante o processo: {e}"
            logging.error(error_message, exc_info=True)
            progress_win.after(0, lambda err=error_message: progress_win.operation_finished("", err))