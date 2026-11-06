"""
SearchManager - Gerencia pesquisas em segundo plano
Otimizado para usar busca unificada (single-pass) API PNCP com log no BD.
"""
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.pncp_search_service import PncpSearchService
from app.models.palavra_chave import PalavraChave
from app.models.resultado_pesquisa import ResultadoPesquisa
from app.models.historico_pesquisa import HistoricoPesquisa

class SearchManager:
    _instance = None
    _lock = threading.Lock()
    
    # Lista padrão de UFs a buscar
    UFS_PADRAO = ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "PE", "CE", "GO", "DF"]
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SearchManager, cls).__new__(cls)
        return cls._instance

    def start_search(self, termos: List[str], ufs: List[str] = None, incremental: bool = False, task_id_reiniciar: int = None) -> int:
        """
        Inicia uma pesquisa em background usando API PNCP persitente no BD.
        """
        ufs = ufs or self.UFS_PADRAO
        
        # Se termos vier vazio, carregar todas as ativas do banco
        if not termos and not task_id_reiniciar:
            palavras_obj = PalavraChave.listar_todas(apenas_ativas=True)
            termos = [p.termo for p in palavras_obj]
            
        if not termos and not task_id_reiniciar:
            raise ValueError("Nenhuma palavra-chave ativa encontrada para pesquisar.")
        
        # Cria novo ou reinicia existente
        if task_id_reiniciar:
            historico = HistoricoPesquisa.buscar_por_id(task_id_reiniciar)
            if not historico:
                raise ValueError("Pesquisa não encontrada para reiniciar.")
            termos = historico.termos # Recupera termos originais
            ufs = historico.ufs        # Recupera UFs originais
            incremental = historico.incremental # Recupera modo
            
            historico.set_status('pendente')
            historico.log(mensagem="🔄 Pesquisa reiniciada pelo usuário")
            # Reseta metricas
            historico.atualizar_progresso(0, uf_atual="")
            historico.atualizar_metricas(0,0,0)
            task_id = historico.id
        else:
            historico = HistoricoPesquisa.criar(termos=termos, ufs=ufs, incremental=incremental)
            if not historico:
                 # Backup safety if DB fails
                 return None
            task_id = historico.id
        
        # Inicia thread
        thread = threading.Thread(
            target=self._run_search_thread,
            args=(task_id, termos, ufs, incremental)
        )
        thread.daemon = True
        thread.start()
        
        return task_id

    def _run_search_thread(self, task_id: int, termos: List[str], ufs: List[str], incremental: bool = False):
        """Thread de busca usando API PNCP (Single-Pass)"""
        import traceback
        
        # Como o request context do flask morre, a thread gerencia seu proprio escopo 
        # para invocar HistoricoPesquisa e Models independentemente.
        historico = HistoricoPesquisa.buscar_por_id(task_id)
        if not historico:
            return
            
        historico.set_status('rodando')
        historico.log("🚀 Iniciando thread de busca no servidor")
        
        try:
            service = PncpSearchService()
            
            # 1. Obter informações das palavras-chave
            palavras = PalavraChave.listar_todas(apenas_ativas=False)
            mapa_palavras = {} # termo -> id
            mapa_objetos = {} # termo -> objeto
            
            historico.log("🔍 Mapeando palavras-chave ativas no sistema")
            for t in termos:
                p_obj = next((p for p in palavras if p.termo.lower() == t.lower()), None)
                if not p_obj:
                    historico.log(f"➕ Criando nova palavra-chave: {t}")
                    p_obj = PalavraChave.criar(t)
                mapa_palavras[t.lower()] = p_obj.id
                mapa_objetos[t.lower()] = p_obj
                
            # 2. Determinar data inicial se for incremental
            data_inicial = None
            if incremental:
                datas = []
                for t in termos:
                    p = mapa_objetos.get(t.lower())
                    if p and p.ultima_pesquisa:
                        try:
                            # Tenta parsear a data
                            dt = datetime.strptime(p.ultima_pesquisa[:10], '%Y-%m-%d')
                            datas.append(dt)
                        except:
                            pass
                
                # Se achou alguma data, pega a mais antiga e recua 1 dia
                if datas:
                    dt_oldest = min(datas) - timedelta(days=1)
                    data_inicial = dt_oldest.strftime('%Y%m%d')
                    historico.log(f"🔄 Modo Incremental ativado: Buscando itens pós {data_inicial}")
                else:
                    historico.log(f"⚠️ Nenhuma pesquisa anterior válida foi encontrada. Fazendo busca desde o início.")
                    
            # 3. Callback de progresso
            def update_progress(uf: str, uf_index: int, total_ufs: int, matches: int, total_items_baixados: int):
                # Usar um objeto novo para nao cachear objeto stale na thread callback
                hist_local = HistoricoPesquisa.buscar_por_id(task_id)
                pct = int(((uf_index + 1) / total_ufs) * 100)
                msg = f"📍 {uf} analisado: {total_items_baixados} baixados -> {matches} passaram no filtro" 
                
                hist_local.log(msg)
                hist_local.atualizar_progresso(pct, f"{uf} ({uf_index+1}/{total_ufs})")
            
            # 4. Executar pesquisa UNIFICADA
            if incremental and data_inicial:
                historico.log("📡 Chamando API PNCP (Endpoint: contratações/publicacao)")
                resultados_raw = service.pesquisar_incremental(
                    termos=termos,
                    ufs=ufs,
                    data_inicial=data_inicial,
                    max_resultados=5000,
                    on_uf_progress=update_progress
                )
            else:
                historico.log("📡 Chamando API PNCP (Endpoint: contratações/proposta)")
                resultados_raw = service.pesquisar(
                    termos=termos,
                    ufs=ufs,
                    dias_ate_encerramento=60,
                    max_resultados=5000,
                    on_uf_progress=update_progress
                )
            
            # Recarrega o objeto depois das atts do callback
            historico = HistoricoPesquisa.buscar_por_id(task_id)
            historico.log(f"✅ Downloads finalizados. Total que deu match: {len(resultados_raw)}. Salvando na base...")
            historico.atualizar_progresso(100, "Salvando...")
            
            # 5. Processar e salvar resultados
            novos = 0
            atualizados = 0
            falhas = 0
            
            for r in resultados_raw:
                id_controle = r.get('numero_controle_pncp') or r.get('numero_processo', 'S/N')
                try:
                    termos_match = r.get('_matched_termos', [])
                    if not termos_match:
                        continue
                    
                    primeiro_termo = termos_match[0]
                    r['palavra_chave_id'] = mapa_palavras.get(primeiro_termo.lower())
                    
                    existente = ResultadoPesquisa.buscar_por_controle_pncp(r.get('numero_controle_pncp'))
                    
                    if existente:
                        if existente.atualizar_dados(r):
                            atualizados += 1
                    else:
                        resultado_db = ResultadoPesquisa.criar(r)
                        if resultado_db:
                            novos += 1
                        else:
                            # Caso onde ResultadoPesquisa.criar retorna None (ex: duplicado ignorado)
                            pass
                except Exception as ex_item:
                    falhas += 1
                    historico.log(f"⚠️ Erro ao salvar item {id_controle}: {str(ex_item)}")
            
            # 6. Atualizar última pesquisa de todas as keywords
            historico.log("⚙️ Atualizando timestamps das palavras-chave...")
            for _, p_obj in mapa_objetos.items():
                p_obj.atualizar_ultima_pesquisa()
                
            # Finaliza a task
            historico.atualizar_metricas(len(resultados_raw), novos, atualizados)
            resumo_msg = f"🏁 Concluído! Novos: {novos} | Atualizados: {atualizados}"
            if falhas > 0:
                resumo_msg += f" | Falhas: {falhas}"
            historico.log(resumo_msg)
            historico.set_status('concluido', finalizar=True)
            historico.atualizar_progresso(100, "Finalizado")

        except Exception as e:
            trace = traceback.format_exc()
            historico = HistoricoPesquisa.buscar_por_id(task_id) # reload
            historico.log(f"❌ ERRO FATAL: {str(e)}")
            print(f"Erro fatal na thread de pesquisa: {trace}")
            historico.uf_atual = str(e)[:30] + "..."
            historico.set_status('erro', finalizar=True)

    def get_status(self, task_id: int) -> Optional[Dict]:
        h = HistoricoPesquisa.buscar_por_id(task_id)
        return h.to_dict() if h else None

    # Função migrada para listar direto do BD
    def get_all_tasks(self) -> List[Dict]:
        return [h.to_dict() for h in HistoricoPesquisa.listar_recentes()]

# Singleton instance
search_manager = SearchManager()
