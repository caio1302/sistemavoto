import sqlite3
import logging
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

import config
from dto.pessoa import Pessoa
from dto.candidatura import Candidatura
from functions import data_helpers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person_repository import PersonRepository
    from .misc_repository import MiscRepository

class ReportService:
    def __init__(self, conn: sqlite3.Connection, person_repo: 'PersonRepository', misc_repo: 'MiscRepository'):
        self.conn = conn
        self.person_repo = person_repo
        self.misc_repo = misc_repo

    def get_recent_activities(self, limit=20) -> list[dict]:
        activities = []
        try:
            cursor = self.conn.cursor()
            queries = {
                "Pessoa": "SELECT 'Pessoa' AS tipo, COALESCE(apelido, nome) AS descricao, data_criacao AS data FROM pessoas",
                "Organização": "SELECT 'Organização' AS tipo, nome_fantasia AS descricao, data_criacao AS data FROM organizacoes",
                "Atendimento": "SELECT 'Atendimento' AS tipo, titulo AS descricao, data_criacao AS data FROM atendimentos",
                "Proposição": "SELECT 'Proposição' AS tipo, titulo AS descricao, data_criacao AS data FROM proposicoes",
                "Evento": "SELECT 'Evento' AS tipo, titulo AS descricao, data_criacao AS data FROM eventos",
            }

            all_results = []
            for query_str in queries.values():
                cursor.execute(f"{query_str} WHERE data IS NOT NULL")
                all_results.extend(cursor.fetchall())
            
            sorted_results = sorted(
                [dict(row) for row in all_results if row['data']],
                key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'), 
                reverse=True
            )
            
            local_timezone = pytz.timezone('America/Sao_Paulo')
            for activity in sorted_results[:limit]:
                try:
                    utc_dt = pytz.utc.localize(datetime.strptime(activity['data'], '%Y-%m-%d %H:%M:%S'))
                    local_dt = utc_dt.astimezone(local_timezone)
                    activity['data_local'] = local_dt.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    activity['data_local'] = activity['data']
                activities.append(activity)

            return activities
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar atividades recentes: {e}", exc_info=True)
            return []

    def get_upcoming_birthdays(self, days: int = 7, roles: list[str] | None = None) -> list[tuple[datetime.date, Candidatura]]:
        try:
            today = datetime.now().date()
            target_mmdd_strings = [(today + timedelta(days=i)).strftime('%m-%d') for i in range(days)]
            placeholders = ','.join(['?'] * len(target_mmdd_strings))
            
            cursor = self.conn.cursor()
            
            query = f"""
                SELECT p.*, c.*
                FROM pessoas p
                JOIN candidaturas c ON p.id_pessoa = c.id_pessoa
                WHERE (c.ano_eleicao, c.id_pessoa) IN (
                    SELECT MAX(ano_eleicao), id_pessoa 
                    FROM candidaturas 
                    GROUP BY id_pessoa
                )
                AND p.data_nascimento IS NOT NULL AND p.data_nascimento != ''
                AND c.situacao IN ('ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'REELEITO')
                AND SUBSTR(p.data_nascimento, 4, 2) || '-' || SUBSTR(p.data_nascimento, 1, 2) IN ({placeholders})
            """
            
            params = list(target_mmdd_strings)
            if roles:
                role_placeholders = ','.join(['?'] * len(roles))
                query += f" AND c.cargo IN ({role_placeholders})"
                params.extend(roles)
            
            cursor.execute(query, tuple(params))
            found_candidaturas = [Candidatura.from_dict(dict(row)) for row in cursor.fetchall()]
            
            result_list = []
            for cand in found_candidaturas:
                try:
                    birth_date = datetime.strptime(cand.pessoa.data_nascimento, "%d/%m/%Y").date()
                    next_birthday = birth_date.replace(year=today.year)
                    if next_birthday < today:
                        next_birthday = next_birthday.replace(year=today.year + 1)
                    result_list.append((next_birthday, cand))
                except (ValueError, TypeError):
                    continue
            
            result_list.sort(key=lambda x: (x[0], (x[1].cidade or '').lower(), (x[1].pessoa.nome or '').lower()))
            return result_list
        except Exception as e:
            logging.error(f"Erro ao buscar aniversariantes: {e}", exc_info=True)
            return []

    def get_cerimonial_data(self, cidade: str, ano: int) -> dict:
        if not cidade or not ano: return {}
        data = {"prefeito": None, "vice": None, "vereadores": [], "prefeitura": {}, "candidato_destaque": None, "ranking_2022": {}}
        
        try:
            cursor = self.conn.cursor()
            cidade_key = data_helpers.normalize_city_key(cidade)
            is_federal_or_state_election = ano % 4 == 2

            def get_candidaturas(cargo: str, situacoes: list, limit=None) -> list[Candidatura]:
                # --- CORREÇÃO AQUI ---
                # A função agora chama o novo método preciso do repositório, em vez do método de busca genérico.
                return self.person_repo.get_candidaturas_por_cidade_exata(
                    cidade=cidade,
                    ano=ano,
                    cargo=cargo,
                    situacoes=situacoes,
                    limit=limit
                )

            if not is_federal_or_state_election:
                data['prefeito'] = next(iter(get_candidaturas('PREFEITO', ['ELEITO'], limit=1)), None)
                data['vice'] = next(iter(get_candidaturas('VICE-PREFEITO', ['ELEITO'], limit=1)), None)
                data['vereadores'] = get_candidaturas('VEREADOR', ['ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'REELEITO'])
            else:
                data['ranking_2022'] = self.get_ranking_por_cargo(cidade_key, ano)

            id_pessoa_proprietario = self.misc_repo.get_app_setting('proprietario_id_pessoa')
            if id_pessoa_proprietario:
                proprietario_obj = self.person_repo.get_person_details(int(id_pessoa_proprietario))
                
                if proprietario_obj:
                    data['candidato_destaque'] = proprietario_obj
                    
                    # --- MUDANÇA: Adiciona 'SUPLENTE' à lista de situações válidas ---
                    situacoes_validas = ['ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'REELEITO', 'SUPLENTE']
                    
                    ultima_candidatura_relevante = next(
                        (cand for cand in proprietario_obj.historico_candidaturas if cand.get('situacao') in situacoes_validas), 
                        None
                    )

                    if ultima_candidatura_relevante:
                        sq_cand_relevante = ultima_candidatura_relevante.get('sq_candidato')
                        ano_relevante = ultima_candidatura_relevante.get('ano_eleicao')
                        
                        cursor.execute(
                            "SELECT votos FROM votos_por_municipio WHERE sq_candidato = ? AND cidade = ? AND ano_eleicao = ?",
                            (sq_cand_relevante, cidade_key, ano_relevante)
                        )
                        votos_row = cursor.fetchone()
                        votos_na_cidade = votos_row['votos'] if votos_row and votos_row['votos'] is not None else 0

                        if votos_na_cidade > 0:
                            candidatura_destaque = Candidatura(
                                pessoa=proprietario_obj,
                                id_candidatura=ultima_candidatura_relevante.get('id_candidatura', 0),
                                id_pessoa=proprietario_obj.id_pessoa,
                                ano_eleicao=ano_relevante,
                                sq_candidato=sq_cand_relevante,
                                nome_urna=ultima_candidatura_relevante.get('nome_urna'),
                                numero_urna=ultima_candidatura_relevante.get('numero_urna'),
                                partido=ultima_candidatura_relevante.get('partido'),
                                cargo=ultima_candidatura_relevante.get('cargo'),
                                situacao=ultima_candidatura_relevante.get('situacao'),
                                votos=votos_na_cidade,
                                cidade=cidade
                            )
                            data['candidato_destaque'] = candidatura_destaque
                            # logging.info(f"Destaque '{proprietario_obj.nome}' exibido como Candidato com {votos_na_cidade} votos em '{cidade}'.")
                        else:
                            logging.info(f"Destaque '{proprietario_obj.nome}' não possui votos em '{cidade}' para sua última eleição relevante. Exibindo como Contato.")
                    else:
                        logging.info(f"Nenhuma candidatura eleita ou suplente encontrada para '{proprietario_obj.nome}'. Exibindo como Contato.")
            
            query_municipio = """
                SELECT m.*, e.total as eleitorado_total, e.masculino as eleitorado_masculino, e.feminino as eleitorado_feminino,
                       o.endereco, o.cep, o.email, o.telefone as tel, o.website as url
                FROM municipios m
                LEFT JOIN eleitorado e ON m.id = e.id_municipio AND e.ano = (SELECT MAX(ano) FROM eleitorado WHERE id_municipio = m.id AND ano <= ?)
                LEFT JOIN organizacoes o ON m.id = o.id_municipio AND o.tipo_organizacao = 'Prefeitura'
                WHERE m.cidade_key = ?
            """
            cursor.execute(query_municipio, (ano, cidade_key))
            municipio_completo_row = cursor.fetchone()
            if municipio_completo_row:
                data['prefeitura'] = dict(municipio_completo_row)
            return data
        except Exception as e:
            logging.error(f"Erro ao buscar dados do cerimonial para {cidade}/{ano}: {e}", exc_info=True)
            return data
   
    def get_ranking_por_cargo(self, cidade_key: str, ano: int) -> dict[str, list[Candidatura]]:
        ranking_data = defaultdict(list)
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT c.cargo FROM votos_por_municipio v JOIN candidaturas c ON v.sq_candidato = c.sq_candidato WHERE v.ano_eleicao = ? AND v.cidade = ? AND c.cargo IS NOT NULL", (ano, cidade_key))
            cargos = [row['cargo'] for row in cursor.fetchall() if row['cargo'] not in ['PRESIDENTE', 'VICE-PRESIDENTE']]

            for cargo in cargos:
                cursor.execute("""
                    SELECT p.*, c.*, v.votos as votos_no_municipio FROM pessoas p
                    JOIN candidaturas c ON p.id_pessoa = c.id_pessoa 
                    JOIN votos_por_municipio v ON c.sq_candidato = v.sq_candidato
                    WHERE c.ano_eleicao = ? AND c.cargo = ? AND v.cidade = ? ORDER BY v.votos DESC LIMIT 5
                """, (ano, cargo, cidade_key))
                
                candidatos_ranqueados = []
                for row in cursor.fetchall():
                    candidato = Candidatura.from_dict(dict(row))
                    candidato.votos = row['votos_no_municipio']
                    candidatos_ranqueados.append(candidato)
                
                ranking_data[cargo] = candidatos_ranqueados
            return dict(ranking_data)
        except Exception as e:
            logging.error(f"Erro ao buscar ranking por cargo para {cidade_key}/{ano}: {e}", exc_info=True)
            return {}

    def get_eleitoral_dashboard_data(self, cidade: str, ano: int) -> dict:
        data = {"party_composition": [], "top_vereadores": []}
        try:
            cursor = self.conn.cursor()
            cidade_key = data_helpers.normalize_city_key(cidade)
            
            query_party = "SELECT cand.partido, COUNT(*) as count FROM candidaturas cand WHERE cand.cidade = ? AND cand.ano_eleicao = ? AND cand.cargo = 'VEREADOR' AND cand.situacao IN ('ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'REELEITO') GROUP BY cand.partido ORDER BY count DESC"
            cursor.execute(query_party, (cidade_key, ano))
            data['party_composition'] = [dict(row) for row in cursor.fetchall()]
            
            vereadores = self.person_repo.search_candidaturas(search_term=cidade_key, criteria='Cidade', ano_ref=ano)
            eleitos = [c for c in vereadores if c.cargo == 'VEREADOR' and c.situacao in ('ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'REELEITO')]
            sorted_eleitos = sorted(eleitos, key=lambda c: c.votos, reverse=True)
            
            data['top_vereadores'] = [c.pessoa for c in sorted_eleitos[:5]]
            
            for pessoa_obj, cand_obj in zip(data['top_vereadores'], sorted_eleitos[:5]):
                pessoa_obj.votos = cand_obj.votos
                pessoa_obj.partido = cand_obj.partido
                pessoa_obj.nome_urna = cand_obj.nome_urna

            return data
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar dados do dashboard eleitoral: {e}", exc_info=True)
            return data

    def get_dashboard_stats(self) -> dict:
        stats = { 'total_pessoas': 0, 'total_organizacoes': 0, 'total_atendimentos_pendentes': 0, 'total_proposicoes_ano': 0, 'votos_sim': 0 }
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(id_pessoa) FROM pessoas"); stats['total_pessoas'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(id_organizacao) FROM organizacoes"); stats['total_organizacoes'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(id_atendimento) FROM atendimentos WHERE status IN ('Aberto', 'Em Andamento')"); stats['total_atendimentos_pendentes'] = cursor.fetchone()[0]
            current_year = datetime.now().year
            cursor.execute("SELECT COUNT(id_proposicao) FROM proposicoes WHERE SUBSTR(data_proposicao, 1, 4) = ?", (str(current_year),)); stats['total_proposicoes_ano'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(id_pessoa) FROM pessoas WHERE voto = 'sim'"); stats['votos_sim'] = cursor.fetchone()[0]
            return stats
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar estatísticas do dashboard: {e}", exc_info=True)
            return stats

    def get_new_contacts_per_month(self, months_ago=12) -> dict[str, int]:
            """
            Busca o número de novos contatos (pessoas) criados por mês nos últimos 'months_ago' meses.
            Retorna um dicionário como {'JAN/25': 15, 'FEV/25': 28, ...}.
            """
            try:
                # Adicionado para importar datetime se ainda não estiver no arquivo
                from datetime import datetime, timedelta

                today = datetime.now()
                # Garante que a data de início seja calculada corretamente
                start_date = today - timedelta(days=365) # Busca o último ano completo

                query = """
                    SELECT
                        STRFTIME('%m/%Y', data_criacao) as mes_ano,
                        COUNT(id_pessoa) as contagem
                    FROM
                        pessoas
                    WHERE
                        data_criacao >= ?
                    GROUP BY
                        mes_ano
                    ORDER BY
                        SUBSTR(mes_ano, 4, 4), SUBSTR(mes_ano, 1, 2)
                    LIMIT ?;
                """
                cursor = self.conn.cursor()
                cursor.execute(query, (start_date.strftime('%Y-%m-%d 00:00:00'), months_ago))

                month_map = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN', 7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}

                results = {}
                for row in cursor.fetchall():
                    mes, ano = row['mes_ano'].split('/')
                    ano_curto = ano[2:]
                    mes_abrev = month_map.get(int(mes), '???')
                    results[f"{mes_abrev}/{ano_curto}"] = row['contagem']

                return results
            except sqlite3.Error as e:
                logging.error(f"Erro ao buscar novos contatos por mês: {e}", exc_info=True)
                return {}
            
    def get_candidate_count_by_role_year(self) -> list[dict]:
        """
        Busca a contagem de candidaturas agrupadas por ano e cargo.
        Retorna uma lista de dicionários, ex: [{'ano_eleicao': 2024, 'cargo': 'VEREADOR', 'contagem': 150}]
        """
        try:
            cursor = self.conn.cursor()
            # Seleciona apenas os cargos mais relevantes para evitar poluir o gráfico
            cargos_relevantes = ('PREFEITO', 'VICE-PREFEITO', 'VEREADOR', 'DEPUTADO ESTADUAL', 'DEPUTADO FEDERAL')
            
            placeholders = ','.join(['?'] * len(cargos_relevantes))
            
            query = f"""
                SELECT
                    ano_eleicao,
                    cargo,
                    COUNT(id_candidatura) as contagem
                FROM
                    candidaturas
                WHERE
                    cargo IN ({placeholders})
                GROUP BY
                    ano_eleicao, cargo
                ORDER BY
                    ano_eleicao DESC, cargo ASC;
            """
            cursor.execute(query, cargos_relevantes)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar contagem de candidatos por cargo/ano: {e}", exc_info=True)
            return []            