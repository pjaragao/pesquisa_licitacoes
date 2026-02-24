"""
SearchManager - Gerencia pesquisas em segundo plano
Migrado para usar API PNCP em vez de web scraping
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Migração: Usar API PNCP em vez de scraper
from app.services.pncp_search_service import PncpSearchService
from app.models.palavra_chave import PalavraChave
from app.models.resultado_pesquisa import ResultadoPesquisa

class SearchManager:
    _instance = None
    _lock = threading.Lock()
    
    # Lista padrão de UFs a buscar (pode ser configurável)
    UFS_PADRAO = ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "PE", "CE", "GO", "DF"]
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SearchManager, cls).__new__(cls)
                cls._instance._id_counter = 0
                cls._instance.tasks = {} # task_id -> info
                cls._instance.active_thread = None
        return cls._instance

    def start_search(self, termos: List[str], ufs: List[str] = None, incremental: bool = False) -> str:
        """
        Inicia uma pesquisa em background usando API PNCP.
        """
        task_id = f"search_{int(time.time())}"
        
        task_info = {
            'id': task_id,
            'status': 'pendente',
            'termos': termos,
            'ufs': ufs or self.UFS_PADRAO,
            'incremental': incremental,
            'termos_concluidos': [],
            'total_encontrados': 0,
            'novos_salvos': 0,
            'atualizados': 0,
            'inicio': datetime.now().strftime('%H:%M:%S'),
            'fim': None,
            'erro': None,
            'progresso': 0
        }
        
        self.tasks[task_id] = task_info
        
        # Inicia thread
        thread = threading.Thread(
            target=self._run_search_thread,
            args=(task_id, termos, ufs or self.UFS_PADRAO, incremental)
        )
        thread.daemon = True
        thread.start()
        
        return task_id

    def _run_search_thread(self, task_id: str, termos: List[str], ufs: List[str], incremental: bool = False):
        """Thread de busca usando API PNCP"""
        task = self.tasks[task_id]
        task['status'] = 'rodando'
        
        try:
            service = PncpSearchService()
            total_termos = len(termos)
            
            for i, termo in enumerate(termos):
                try:
                    print(f"🔍 [API PNCP] Pesquisando: {termo} (Incremental: {incremental})")
                    
                    # Busca a palavra-chave no banco (ou cria se não existir)
                    palavras = PalavraChave.listar_todas()
                    palavra_obj = next((p for p in palavras if p.termo.lower() == termo.lower()), None)
                    
                    if not palavra_obj:
                        palavra_obj = PalavraChave.criar(termo)
                    
                    # Determina data inicial se for incremental
                    data_inicial = None
                    if incremental and palavra_obj.ultima_pesquisa:
                        # Pega a data da última pesquisa e volta 1 dia para garantir overlap
                        try:
                            # Formato esperado: '2026-02-05 09:32:56'
                            dt = datetime.strptime(palavra_obj.ultima_pesquisa[:10], '%Y-%m-%d')
                            # Volta 1 dia por segurança
                            dt = dt - timedelta(days=1)
                            data_inicial = dt.strftime('%Y%m%d')
                        except:
                            pass
                    
                    # Executa a pesquisa via API PNCP
                    resultados_raw = service.pesquisar(
                        termos=[termo],
                        ufs=ufs,
                        dias_ate_encerramento=60, # Busca Editais com até 60 dias para fechar
                        max_resultados=1000,
                        palavra_chave_id=palavra_obj.id,
                        data_publicacao_inicial=data_inicial
                    )
                    
                    novos = 0
                    atualizados = 0
                    for r in resultados_raw:
                        # Verifica se já existe para decidir entre criar ou atualizar
                        existente = ResultadoPesquisa.buscar_por_controle_pncp(r.get('numero_controle_pncp'))
                        
                        if existente:
                            if existente.atualizar_dados(r):
                                atualizados += 1
                        else:
                            resultado_db = ResultadoPesquisa.criar(r)
                            if resultado_db:
                                novos += 1
                    
                    palavra_obj.atualizar_ultima_pesquisa()
                    
                    # Atualiza task info
                    task['termos_concluidos'].append(termo)
                    task['total_encontrados'] += len(resultados_raw)
                    task['novos_salvos'] += novos
                    task['atualizados'] += atualizados
                    task['progresso'] = int(((i + 1) / total_termos) * 100)
                    
                except Exception as e:
                    print(f"❌ Erro ao pesquisar termo '{termo}': {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            task['status'] = 'concluido'
            task['fim'] = datetime.now().strftime('%H:%M:%S')
            
        except Exception as e:
            task['status'] = 'erro'
            task['erro'] = str(e)
            print(f"❌ Erro fatal na thread de pesquisa: {e}")

    def get_status(self, task_id: str) -> Optional[Dict]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Dict]:
        # Retorna apenas as últimas 10 tarefas
        return sorted(self.tasks.values(), key=lambda x: x['id'], reverse=True)[:10]

# Singleton instance
search_manager = SearchManager()
