import sqlite3
import logging
import time
import threading
from tkinter import messagebox

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from dto.pessoa import Pessoa
from dto.organizacao import Organizacao

class GeoService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.geolocator = Nominatim(user_agent="e-votos-app/1.0.2") # Incrementa a versão do agente

    def _geocode_address(self, address_to_search: str) -> tuple[float | None, float | None]:
        if not address_to_search or len(address_to_search.split(',')) < 2:
            logging.warning(f"Endereço inválido ou insuficiente para geocodificação: '{address_to_search}'")
            return None, None
        try:
            time.sleep(1.1) 
            location = self.geolocator.geocode(address_to_search, timeout=10, country_codes='BR')
            if location:
                logging.info(f"Endereço '{address_to_search}' geocodificado para: ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
            else:
                logging.warning(f"Nenhum resultado para o endereço: '{address_to_search}'")
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logging.error(f"Erro de serviço no geocoding para '{address_to_search}': {e}")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erro inesperado durante geocoding para '{address_to_search}': {e}")
        return None, None
        
    def geocode_and_save_entity_threaded(self, entity: Pessoa | Organizacao):
        threading.Thread(target=self.geocode_and_save_entity, args=(entity,), daemon=True).start()

    def geocode_and_save_entity(self, entity: Pessoa | Organizacao) -> bool:
        """
        Geocodifica e salva as coordenadas para uma única Pessoa ou Organização,
        com lógica aprimorada de construção de endereço.
        """
        address_parts = []
        
        # Constrói a lista de partes do endereço, ignorando campos vazios
        if isinstance(entity, Pessoa):
            if entity.endereco and entity.endereco.strip(): address_parts.append(entity.endereco)
            if entity.numero and entity.numero.strip(): address_parts.append(entity.numero)
            if entity.cidade and entity.cidade.strip(): address_parts.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts.append(entity.uf)
            else: address_parts.append("SP") # Adiciona SP como padrão se não houver UF
        
        elif isinstance(entity, Organizacao):
            if entity.endereco and entity.endereco.strip(): address_parts.append(entity.endereco)
            if entity.numero and entity.numero.strip(): address_parts.append(entity.numero)
            if entity.cidade and entity.cidade.strip(): address_parts.append(entity.cidade)
            if entity.uf and entity.uf.strip(): address_parts.append(entity.uf)
            else: address_parts.append("SP")

        # Junta as partes válidas com ", "
        address_str = ", ".join(address_parts)
        
        lat, lon = self._geocode_address(address_str)

        if lat and lon:
            # Atualiza o objeto em memória para refletir a mudança
            entity.latitude, entity.longitude = lat, lon
            
            # Salva no banco de dados
            try:
                with self.conn:
                    if isinstance(entity, Pessoa):
                        self.conn.execute("UPDATE pessoas SET latitude = ?, longitude = ? WHERE id_pessoa = ?", (lat, lon, entity.id_pessoa))
                    elif isinstance(entity, Organizacao):
                        self.conn.execute("UPDATE organizacoes SET latitude = ?, longitude = ? WHERE id_organizacao = ?", (lat, lon, entity.id_organizacao))
                return True
            except sqlite3.Error as e:
                logging.error(f"Erro ao salvar coordenadas no DB para {type(entity).__name__} ID {entity.id_pessoa or entity.id_organizacao}: {e}")
                return False

        return False

    def geocode_all_contacts(self, progress_win):
        """Geocodifica TODOS os contatos (Pessoas) que ainda não têm coordenadas."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM pessoas WHERE (latitude IS NULL OR longitude IS NULL) AND (endereco IS NOT NULL AND endereco != '') AND (cidade IS NOT NULL AND cidade != '')")
            people_to_geocode = [Pessoa.from_dict(dict(row)) for row in cursor.fetchall()]

            total = len(people_to_geocode)
            if total == 0:
                progress_win.after(0, progress_win.operation_finished, "Todos os contatos com endereço já possuem coordenadas.")
                return

            success_count = 0
            for i, pessoa in enumerate(people_to_geocode):
                progress = (i + 1) / total
                progress_win.after(0, progress_win.update_progress, f"Geocodificando: {pessoa.nome}", progress, f"Pessoa {i+1}/{total}")
                
                if self.geocode_and_save_entity(pessoa):
                    success_count += 1
            
            final_message = f"Geocodificação de Pessoas concluída!\n{success_count} de {total} contatos foram atualizados."
            progress_win.after(0, progress_win.operation_finished, final_message)

        except Exception as e:
            error_message = f"Um erro ocorreu durante o processo: {e}"
            logging.error(error_message, exc_info=True)
            progress_win.after(0, progress_win.operation_finished, "", error_message)

    def geocode_all_organizations(self, progress_win):
        """Geocodifica TODAS as organizações que ainda não têm coordenadas."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM organizacoes WHERE (latitude IS NULL OR longitude IS NULL) AND (endereco IS NOT NULL AND endereco != '') AND (cidade IS NOT NULL AND cidade != '')")
            orgs_to_geocode = [Organizacao.from_dict(dict(row)) for row in cursor.fetchall()]

            total = len(orgs_to_geocode)
            if total == 0:
                progress_win.after(0, progress_win.operation_finished, "Todas as organizações com endereço já possuem coordenadas.")
                return

            success_count = 0
            for i, org in enumerate(orgs_to_geocode):
                progress = (i + 1) / total
                progress_win.after(0, progress_win.update_progress, f"Geocodificando: {org.nome_fantasia}", progress, f"Organização {i+1}/{total}")
                
                if self.geocode_and_save_entity(org):
                    success_count += 1

            final_message = f"Geocodificação de Organizações concluída!\n{success_count} de {total} organizações elegíveis foram atualizadas."
            progress_win.after(0, progress_win.operation_finished, final_message)

        except Exception as e:
            error_message = f"Um erro ocorreu durante o processo: {e}"
            logging.error(error_message, exc_info=True)
            progress_win.after(0, progress_win.operation_finished, "", error_message)