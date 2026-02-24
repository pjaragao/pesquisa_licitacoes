"""
Cliente HTTP para API PNCP (Portal Nacional de Contratações Públicas)
Documentação: https://pncp.gov.br/api/consulta/swagger-ui/index.html
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time


class PncpApiClient:
    """Cliente para consumir a API de consulta do PNCP"""
    
    BASE_URL = "https://pncp.gov.br/api/consulta"
    
    # Modalidades de contratação (para referência)
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
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
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
    
    def _fazer_requisicao(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Faz requisição GET com retry automático
        
        Args:
            endpoint: Caminho do endpoint (ex: /v1/contratacoes/proposta)
            params: Parâmetros de query string
        
        Returns:
            Resposta JSON da API
        
        Raises:
            Exception: Se todas as tentativas falharem
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        for tentativa in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 204:
                    # Sem conteúdo - retorna estrutura vazia
                    return {"data": [], "totalRegistros": 0, "totalPaginas": 0}
                elif response.status_code == 429:
                    # Rate limit - espera e tenta novamente
                    wait_time = 2 ** tentativa
                    print(f"⏳ Rate limit atingido, aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️ Erro HTTP {response.status_code}: {response.text[:200]}")
                    if tentativa < self.max_retries - 1:
                        time.sleep(1)
                        continue
                    raise Exception(f"Erro HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"⏳ Timeout na tentativa {tentativa + 1}/{self.max_retries}")
                if tentativa < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise Exception("Timeout após múltiplas tentativas")
            except requests.exceptions.RequestException as e:
                print(f"❌ Erro de conexão: {e}")
                if tentativa < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise
        
        return {"data": [], "totalRegistros": 0, "totalPaginas": 0}
    
    def buscar_contratacoes_propostas_abertas(
        self,
        data_final: str = None,
        uf: str = None,
        codigo_modalidade: int = None,
        codigo_municipio_ibge: str = None,
        cnpj: str = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
        data_publicacao_inicial: str = None,
        data_publicacao_final: str = None
    ) -> Dict:
        """
        Busca contratações com recebimento de propostas aberto.
        Endpoint: /v1/contratacoes/proposta
        
        Args:
            data_final: Data limite para propostas (formato YYYYMMDD).
            uf: Sigla da UF (ex: "SP", "RJ")
            codigo_modalidade: Código da modalidade
            pagina: Número da página
            data_publicacao_inicial: Data inicial de publicação (YYYYMMDD)
            data_publicacao_final: Data final de publicação (YYYYMMDD)
        """
        if not data_final:
            # Padrão: 60 dias à frente se não especificado
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
        if data_publicacao_inicial:
            params["dataPublicacaoInicial"] = data_publicacao_inicial
        if data_publicacao_final:
            params["dataPublicacaoFinal"] = data_publicacao_final
        
        return self._fazer_requisicao("/v1/contratacoes/proposta", params)
    
    def buscar_todas_paginas(
        self,
        uf: str = None,
        data_final: str = None,
        codigo_modalidade: int = None,
        max_paginas: int = 20,
        tamanho_pagina: int = 50,
        data_publicacao_inicial: str = None,
        data_publicacao_final: str = None
    ) -> List[Dict]:
        """
        Busca todas as páginas de resultados e retorna lista consolidada.
        """
        todos_resultados = []
        pagina = 1
        
        while pagina <= max_paginas:
            resultado = self.buscar_contratacoes_propostas_abertas(
                data_final=data_final,
                uf=uf,
                codigo_modalidade=codigo_modalidade,
                pagina=pagina,
                tamanho_pagina=tamanho_pagina,
                data_publicacao_inicial=data_publicacao_inicial,
                data_publicacao_final=data_publicacao_final
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
    
    def buscar_contratacao_detalhes(
        self,
        cnpj: str,
        ano: int,
        sequencial: int
    ) -> Optional[Dict]:
        """
        Obtém detalhes completos de uma contratação específica.
        Endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}
        
        Args:
            cnpj: CNPJ do órgão (com ou sem formatação)
            ano: Ano da compra
            sequencial: Número sequencial da compra
        
        Returns:
            Dict com detalhes da contratação ou None se não encontrada
        """
        # Remove formatação do CNPJ
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        
        endpoint = f"/v1/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}"
        
        try:
            return self._fazer_requisicao(endpoint)
        except Exception as e:
            print(f"⚠️ Erro ao buscar detalhes: {e}")
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
