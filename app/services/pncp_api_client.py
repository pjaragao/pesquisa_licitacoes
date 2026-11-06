"""
Cliente HTTP para API PNCP (Portal Nacional de Contratações Públicas)
Documentação: https://pncp.gov.br/api/consulta/swagger-ui/index.html

Endpoints utilizados:
  /v1/contratacoes/proposta     - Contratações com propostas abertas (busca total)
  /v1/contratacoes/publicacao   - Contratações por data de publicação (busca incremental)
  /v1/orgaos/{cnpj}/compras/... - Detalhes de contratação específica
"""
import requests
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import time
import threading


class PncpRateLimiter:
    """Controlador global seguro entre threads para evitar Rate Limit e enfileirar chamadas"""
    _lock = threading.Lock()
    _last_call = 0.0
    _min_interval = 0.35  # Aproximadamente 3 requisições por segundo para evitar 429

    @classmethod
    def wait(cls):
        with cls._lock:
            now = time.time()
            elapsed = now - cls._last_call
            if elapsed < cls._min_interval:
                time.sleep(cls._min_interval - elapsed)
            cls._last_call = time.time()

class PncpApiClient:
    """Cliente para consumir a API de consulta do PNCP"""
    
    BASE_URL = "https://pncp.gov.br/api/consulta"
    DETAIL_BASE_URL = "https://pncp.gov.br/api/pncp"
    
    # Modalidades de contratação
    MODALIDADES = {
        1: "Leilão - Loss",
        2: "Diálogo Competitivo",
        3: "Concurso",
        4: "Concorrência - Loss",
        5: "Concorrência - LLCA",
        6: "Pregão - Loss",
        7: "Pregão - LLCA",
        8: "Dispensa de Licitação",
        9: "Inexigibilidade",
        10: "Manifestação de Interesse",
        11: "Pré-qualificação",
        12: "Credenciamento",
        13: "Leilão - LLCA",
    }
    
    # Modalidades principais para busca incremental
    # (as mais comuns em licitações públicas)
    MODALIDADES_PRINCIPAIS = [6, 7, 8, 4, 5, 9, 12, 3]
    
    def __init__(self, timeout: int = 45, max_retries: int = 3):
        """
        Args:
            timeout: Timeout em segundos para requisições
            max_retries: Número máximo de tentativas em caso de falha
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PesquisaLicitacoes/1.0"
        })
    
    def _fazer_requisicao(self, endpoint: str, params: Dict = None, use_detail_base: bool = False) -> Dict:
        """
        Faz requisição GET com retry automático
        
        Args:
            endpoint: Caminho do endpoint (ex: /v1/contratacoes/proposta)
            params: Parâmetros de query string
            use_detail_base: Se deve usar a URL de detalhamento (api/pncp) ou consulta (api/consulta)
        
        Returns:
            Resposta JSON da API
        
        Raises:
            Exception: Se todas as tentativas falharem
        """
        base_url = self.DETAIL_BASE_URL if use_detail_base else self.BASE_URL
        url = f"{base_url}{endpoint}"
        
        for tentativa in range(self.max_retries):
            try:
                # Fila de espera global anti rate-limit
                PncpRateLimiter.wait()
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 204:
                    # Sem conteúdo - retorna estrutura vazia
                    return {"data": [], "totalRegistros": 0, "totalPaginas": 0}
                elif response.status_code == 429:
                    # Rate limit - espera e tenta novamente
                    wait_time = 2 ** tentativa
                    print(f"⏳ [PNCP API] Rate limit (429) em {url}. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️ [PNCP API] Erro HTTP {response.status_code} em {url}: {response.text[:200]}")
                    if tentativa < self.max_retries - 1:
                        time.sleep(1)
                        continue
                    # Não levanta exceção aqui para não quebrar o loop de UFs, 
                    # mas o retorno vazio indicará falha nesta UF.
                    
            except requests.exceptions.Timeout:
                print(f"⏳ [PNCP API] Timeout ({self.timeout}s) na tentativa {tentativa + 1}/{self.max_retries} em {url}")
                if tentativa < self.max_retries - 1:
                    time.sleep(2) # Espera um pouco mais em caso de timeout
                    continue
            except requests.exceptions.RequestException as e:
                print(f"❌ [PNCP API] Erro de conexão em {url}: {str(e)}")
                if tentativa < self.max_retries - 1:
                    time.sleep(1)
                    continue
        
        return {"data": [], "totalRegistros": 0, "totalPaginas": 0}
    
    # =====================================================
    # ENDPOINT: /v1/contratacoes/proposta  (busca total)
    # Retorna contratações com recebimento de propostas aberto
    # NÃO suporta filtro por data de publicação
    # =====================================================
    
    def buscar_contratacoes_propostas_abertas(
        self,
        data_final: str = None,
        uf: str = None,
        codigo_modalidade: int = None,
        codigo_municipio_ibge: str = None,
        cnpj: str = None,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> Dict:
        """
        Busca contratações com recebimento de propostas aberto.
        Endpoint: /v1/contratacoes/proposta
        
        Parâmetros suportados pela API:
          dataFinal*, codigoModalidadeContratacao, uf,
          codigoMunicipioIbge, cnpj, codigoUnidadeAdministrativa,
          idUsuario, pagina*, tamanhoPagina
        """
        if not data_final:
            data_final = (datetime.now() + timedelta(days=60)).strftime("%Y%m%d")
        
        params = {
            "dataFinal": data_final,
            "pagina": pagina,
            "tamanhoPagina": min(max(tamanho_pagina, 10), 50)
        }
        
        if uf:
            params["uf"] = uf.upper()
        if codigo_modalidade:
            params["codigoModalidadeContratacao"] = codigo_modalidade
        if codigo_municipio_ibge:
            params["codigoMunicipioIbge"] = codigo_municipio_ibge
        if cnpj:
            params["cnpj"] = cnpj
        
        return self._fazer_requisicao("/v1/contratacoes/proposta", params)
    
    def buscar_todas_paginas(
        self,
        uf: str = None,
        data_final: str = None,
        codigo_modalidade: int = None,
        max_paginas: int = 100,
        tamanho_pagina: int = 50
    ) -> List[Dict]:
        """
        Busca todas as páginas de resultados do endpoint /proposta.
        """
        todos_resultados = []
        pagina = 1
        
        while pagina <= max_paginas:
            resultado = self.buscar_contratacoes_propostas_abertas(
                data_final=data_final,
                uf=uf,
                codigo_modalidade=codigo_modalidade,
                pagina=pagina,
                tamanho_pagina=tamanho_pagina
            )
            
            dados = resultado.get("data", [])
            if not dados:
                break
            
            todos_resultados.extend(dados)
            
            total_paginas = resultado.get("totalPaginas", 1)
            print(f"📄 Página {pagina}/{total_paginas} - {len(dados)} registros")
            
            if pagina >= total_paginas:
                break
            
            pagina += 1
            time.sleep(0.3)  # Rate limiting amigável
        
        return todos_resultados
    
    # =====================================================
    # ENDPOINT: /v1/contratacoes/publicacao  (incremental)
    # Retorna contratações por data de publicação
    # Suporta dataInicial + dataFinal (obrigatórios)
    # Requer codigoModalidadeContratacao (obrigatório)
    # =====================================================
    
    def buscar_contratacoes_por_publicacao(
        self,
        data_inicial: str,
        data_final: str,
        codigo_modalidade: int,
        uf: str = None,
        cnpj: str = None,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> Dict:
        """
        Busca contratações por data de publicação.
        Endpoint: /v1/contratacoes/publicacao
        
        Parâmetros suportados pela API:
          dataInicial*, dataFinal*, codigoModalidadeContratacao*,
          codigoModoDisputa, uf, codigoMunicipioIbge, cnpj,
          codigoUnidadeAdministrativa, idUsuario, pagina*, tamanhoPagina
        
        Args:
            data_inicial: Data inicial de publicação (formato YYYYMMDD) - OBRIGATÓRIO
            data_final: Data final de publicação (formato YYYYMMDD) - OBRIGATÓRIO
            codigo_modalidade: Código da modalidade - OBRIGATÓRIO
            uf: Sigla da UF (ex: "SP")
            pagina: Número da página
            tamanho_pagina: Tamanho da página (10-50)
        """
        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "codigoModalidadeContratacao": codigo_modalidade,
            "pagina": pagina,
            "tamanhoPagina": min(max(tamanho_pagina, 10), 50)
        }
        
        if uf:
            params["uf"] = uf.upper()
        if cnpj:
            params["cnpj"] = cnpj
        
        return self._fazer_requisicao("/v1/contratacoes/publicacao", params)
    
    def buscar_todas_paginas_publicacao(
        self,
        data_inicial: str,
        data_final: str,
        codigo_modalidade: int,
        uf: str = None,
        max_paginas: int = 50,
        tamanho_pagina: int = 50
    ) -> List[Dict]:
        """
        Busca todas as páginas do endpoint /publicacao para uma modalidade.
        """
        todos_resultados = []
        pagina = 1
        
        while pagina <= max_paginas:
            resultado = self.buscar_contratacoes_por_publicacao(
                data_inicial=data_inicial,
                data_final=data_final,
                codigo_modalidade=codigo_modalidade,
                uf=uf,
                pagina=pagina,
                tamanho_pagina=tamanho_pagina
            )
            
            dados = resultado.get("data", [])
            if not dados:
                break
            
            todos_resultados.extend(dados)
            
            total_paginas = resultado.get("totalPaginas", 1)
            
            if pagina >= total_paginas:
                break
            
            pagina += 1
            time.sleep(0.3)
        
        return todos_resultados
    
    # =====================================================
    # ENDPOINT: /v1/orgaos/{cnpj}/compras/{ano}/{seq}
    # Detalhes de contratação específica
    # =====================================================
    
    def buscar_contratacao_detalhes(
        self,
        cnpj: str,
        ano: int,
        sequencial: int
    ) -> Optional[Dict]:
        """
        Obtém detalhes completos de uma contratação específica.
        Endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}
        """
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        endpoint = f"/v1/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}"
        
        try:
            return self._fazer_requisicao(endpoint, use_detail_base=True)
        except Exception as e:
            print(f"⚠️ Erro ao buscar detalhes: {e}")
            return None

    def buscar_contratacao_itens(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> Optional[Dict]:
        """
        Obtém listagem de itens de uma contratação específica.
        Endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens
        """
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        endpoint = f"/v1/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/itens"
        
        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina
        }
        
        try:
            return self._fazer_requisicao(endpoint, params, use_detail_base=True)
        except Exception as e:
            print(f"⚠️ Erro ao buscar itens: {e}")
            return None

    def buscar_contratacao_arquivos(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> Optional[Dict]:
        """
        Obtém listagem de arquivos anexos de uma contratação.
        Endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos
        """
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        endpoint = f"/v1/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/arquivos"
        
        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina
        }
        
        try:
            return self._fazer_requisicao(endpoint, params, use_detail_base=True)
        except Exception as e:
            print(f"⚠️ Erro ao buscar arquivos: {e}")
            return None

    def buscar_contratacao_historico(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> Optional[Dict]:
        """
        Obtém listagem de histórico (andamento) de uma contratação.
        Endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/historico
        """
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        endpoint = f"/v1/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/historico"
        
        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina
        }
        
        try:
            return self._fazer_requisicao(endpoint, params, use_detail_base=True)
        except Exception as e:
            print(f"⚠️ Erro ao buscar historico: {e}")
            return None



# Teste rápido
if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO CLIENTE API PNCP")
    print("=" * 60)
    
    client = PncpApiClient()
    
    # Busca licitações abertas em SP
    print("\n🔍 Buscando licitações com propostas abertas em SP...")
    resultado = client.buscar_contratacoes_propostas_abertas(uf="SP", tamanho_pagina=10)
    
    print(f"\n📊 Total de registros: {resultado.get('totalRegistros', 0)}")
    print(f"📊 Total de páginas: {resultado.get('totalPaginas', 0)}")
    
    dados = resultado.get("data", [])
    print(f"\n📋 Primeiros {len(dados)} resultados:")
    
    for i, item in enumerate(dados[:5], 1):
        print(f"\n{i}. {item.get('numeroControlePNCP', 'N/A')}")
        print(f"   Objeto: {item.get('objetoCompra', 'N/A')[:80]}...")
        print(f"   Órgão: {item.get('unidadeOrgao', {}).get('nomeUnidade', 'N/A')}")
        print(f"   Modalidade: {item.get('modalidadeNome', 'N/A')}")
        print(f"   Valor Est.: R$ {item.get('valorTotalEstimado', 'N/A')}")
