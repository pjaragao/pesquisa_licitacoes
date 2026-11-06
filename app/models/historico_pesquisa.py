"""
Model: Histórico de Pesquisa
Persiste todos os jobs de buscas rodando em 2º plano, guardando logs detalhados
"""
import json
from datetime import datetime
from app import get_db

class HistoricoPesquisa:
    """Gerencia registros do hitórico de pesquisas disparadas"""
    
    def __init__(
        self, id=None, termos=None, ufs=None, incremental=False, status='pendente',
        progresso=0, uf_atual=None, total_encontrados=0, novos_salvos=0, atualizados=0,
        logs_auditoria=None, criado_em=None, atualizado_em=None, finalizado_em=None
    ):
        self.id = id
        self.termos = termos or []
        self.ufs = ufs or []
        self.incremental = incremental
        self.status = status
        self.progresso = progresso
        self.uf_atual = uf_atual
        self.total_encontrados = total_encontrados
        self.novos_salvos = novos_salvos
        self.atualizados = atualizados
        self.logs_auditoria = logs_auditoria or []
        self.criado_em = criado_em
        self.atualizado_em = atualizado_em
        self.finalizado_em = finalizado_em

    @staticmethod
    def criar(termos: list, ufs: list, incremental: bool = False) -> 'HistoricoPesquisa':
        """Inicializa um registro de pesquisa pendente no DB e retorna o Model"""
        new_id = None
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO historico_pesquisas 
                (termos, ufs, incremental, status, logs_auditoria) 
                VALUES (?, ?, ?, 'pendente', ?)
                """,
                (
                    json.dumps(termos),
                    json.dumps(ufs),
                    1 if incremental else 0,
                    json.dumps([{"hora": datetime.now().strftime('%H:%M:%S'), "msg": "Pesquisa registrada"}])
                )
            )
            new_id = cursor.lastrowid
        
        return HistoricoPesquisa.buscar_por_id(new_id)

    def _salvar(self):
        """Salva o estado atual no banco"""
        with get_db() as conn:
            conn.execute(
                """
                UPDATE historico_pesquisas SET
                    status = ?,
                    progresso = ?,
                    uf_atual = ?,
                    total_encontrados = ?,
                    novos_salvos = ?,
                    atualizados = ?,
                    logs_auditoria = ?,
                    atualizado_em = CURRENT_TIMESTAMP,
                    finalizado_em = ?
                WHERE id = ?
                """,
                (
                    self.status,
                    self.progresso,
                    self.uf_atual,
                    self.total_encontrados,
                    self.novos_salvos,
                    self.atualizados,
                    json.dumps(self.logs_auditoria),
                    self.finalizado_em,
                    self.id
                )
            )

    def log(self, mensagem: str):
        """Adiciona um log ao bloco de auditoria e salva o estado"""
        if not isinstance(self.logs_auditoria, list):
            self.logs_auditoria = []
        
        self.logs_auditoria.append({
            "hora": datetime.now().strftime('%H:%M:%S'),
            "msg": mensagem
        })
        # Limita logs aos últimos 200 eventos para não estourar espaço
        if len(self.logs_auditoria) > 200:
            self.logs_auditoria = self.logs_auditoria[-200:]
            
        self._salvar()

    def set_status(self, novo_status: str, finalizar=False):
        """Transaciona status da tarefa"""
        self.status = novo_status
        if finalizar:
            self.finalizado_em = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._salvar()

    def atualizar_progresso(self, progresso: int, uf_atual: str = None):
        """Atualiza barra de progresso do frontend"""
        self.progresso = progresso
        if uf_atual:
            self.uf_atual = uf_atual
        self._salvar()
        
    def atualizar_metricas(self, total: int, novos: int, atualizados: int):
        self.total_encontrados = total
        self.novos_salvos = novos
        self.atualizados = atualizados
        self._salvar()

    @staticmethod
    def buscar_por_id(id: int) -> 'HistoricoPesquisa':
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM historico_pesquisas WHERE id = ?", (id,))
            row = cursor.fetchone()
            return HistoricoPesquisa._from_row(row) if row else None

    @staticmethod
    def listar_recentes(limite: int = 15) -> list:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM historico_pesquisas ORDER BY criado_em DESC LIMIT ?", (limite,)
            )
            return [HistoricoPesquisa._from_row(row) for row in cursor.fetchall()]
            
    @staticmethod
    def verificar_travadas():
        """Move para 'erro' pesquisas 'rodando' que não atualizam há 10 minutos"""
        # Ex: Travou por falta de memória ou queda docker
        with get_db() as conn:
            conn.execute(
                """
                UPDATE historico_pesquisas 
                SET status = 'erro', uf_atual = 'Abortada por tempo limite (timeout silencioso)' 
                WHERE status = 'rodando' AND 
                (strftime('%s','now') - strftime('%s', atualizado_em) > 600)
                """
            )

    @staticmethod
    def _from_row(row) -> 'HistoricoPesquisa':
        if not row:
            return None
        
        # Safe JSON parse
        termos, ufs, logs = [], [], []
        
        try: termos = json.loads(row['termos'])
        except: pass
        try: ufs = json.loads(row['ufs'])
        except: pass
        try: logs = json.loads(row['logs_auditoria'])
        except: pass
        
        return HistoricoPesquisa(
            id=row['id'],
            termos=termos,
            ufs=ufs,
            incremental=bool(row['incremental']),
            status=row['status'],
            progresso=row['progresso'],
            uf_atual=row['uf_atual'],
            total_encontrados=row['total_encontrados'],
            novos_salvos=row['novos_salvos'],
            atualizados=row['atualizados'],
            logs_auditoria=logs,
            criado_em=row['criado_em'],
            atualizado_em=row['atualizado_em'],
            finalizado_em=row['finalizado_em']
        )
        
    def to_dict(self):
        # Format "15:24:00" from iso or string dates if we have them
        try: 
            inicio_fmt = datetime.strptime(self.criado_em, '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
        except: 
            inicio_fmt = self.criado_em[11:19] if self.criado_em and len(self.criado_em)>11 else ""
            
        fim_fmt = ""
        if self.finalizado_em:
            try: fim_fmt = datetime.strptime(self.finalizado_em, '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
            except: fim_fmt = self.finalizado_em[11:19] if len(self.finalizado_em)>11 else ""
            
        return {
            'id': self.id,
            'termos': self.termos,
            'ufs': self.ufs,
            'incremental': self.incremental,
            'status': self.status,
            'progresso': self.progresso,
            'uf_atual': self.uf_atual,
            'total_encontrados': self.total_encontrados,
            'novos_salvos': self.novos_salvos,
            'atualizados': self.atualizados,
            'inicio': inicio_fmt,
            'fim': fim_fmt,
            'logs': self.logs_auditoria,
            'erro': self.uf_atual if self.status in ['erro', 'travado'] else None
        }
