"""
Serviço de Busca PNCP - Busca licitações via API e filtra por palavras-chave
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re

from app.services.pncp_api_client import PncpApiClient


class PncpSearchService:
    """Serviço para buscar e filtrar licitações do PNCP"""
    
    # UFs do Brasil para busca
    UFS_BRASIL = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO"
    ]
    
    def __init__(self):
        self.client = PncpApiClient()
    
    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza texto para comparação (minúsculas, sem acentos extras)"""
        if not texto:
            return ""
        return texto.lower().strip()
    
    def _contem_termo(self, texto: str, termo: str) -> bool:
        """Verifica se o texto contém o termo (case insensitive)"""
        texto_norm = self._normalizar_texto(texto)
        termo_norm = self._normalizar_texto(termo)
        return termo_norm in texto_norm
    
    def _resultado_contem_termos(self, resultado: Dict, termos: List[str]) -> bool:
        """
        Verifica se o resultado contém algum dos termos buscados.
        Busca no objeto da compra e informação complementar.
        """
        # Campos a verificar
        objeto = resultado.get("objetoCompra", "") or ""
        info_complementar = resultado.get("informacaoComplementar", "") or ""
        texto_completo = f"{objeto} {info_complementar}"
        
        for termo in termos:
            if self._contem_termo(texto_completo, termo):
                return True
        return False
    
    def _mapear_para_resultado_pesquisa(self, item: Dict, palavra_chave_id: int = None) -> Dict:
        """
        Mapeia um item da API PNCP para o formato do ResultadoPesquisa.
        Inclui todos os campos disponíveis para armazenamento completo.
        """
        unidade = item.get("unidadeOrgao", {}) or {}
        orgao_entidade = item.get("orgaoEntidade", {}) or {}
        amparo = item.get("amparoLegal", {}) or {}
        
        # Obter valor numérico
        valor = item.get("valorTotalEstimado")
        valor_homologado = item.get("valorTotalHomologado")
        
        # Formatar valor para exibição
        valor_formatado = ""
        if valor is not None:
            try:
                valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                valor_formatado = f"R$ {valor}"
        
        # Formatar datas
        def formatar_data(data_str: str) -> str:
            if not data_str:
                return ""
            try:
                dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y %H:%M")
            except:
                return data_str
        
        # Construir URL do processo no PNCP
        numero_pncp = item.get("numeroControlePNCP", "")
        url_pncp = ""
        if numero_pncp:
            url_pncp = f"https://pncp.gov.br/app/editais/{numero_pncp}"
        
        # Fallback para link do sistema origem
        url_processo = item.get("linkSistemaOrigem") or url_pncp
        
        return {
            "palavra_chave_id": palavra_chave_id,
            # Campos originais
            "numero_processo": item.get("numeroCompra") or numero_pncp or "",
            "titulo": item.get("objetoCompra", "")[:500] if item.get("objetoCompra") else "",
            "objeto": item.get("objetoCompra", "") or "",
            "orgao": unidade.get("nomeUnidade") or orgao_entidade.get("razaoSocial") or "",
            "uf": unidade.get("ufSigla", "") or "",
            "municipio": unidade.get("municipioNome", "") or "",
            "modalidade": item.get("modalidadeNome", "") or "",
            "status": item.get("situacaoCompraNome", "") or "Recebendo propostas",
            "data_realizacao": formatar_data(item.get("dataEncerramentoProposta", "")),
            "valor_estimado": valor_formatado,
            "url_processo": url_processo,
            "inicio_propostas": formatar_data(item.get("dataAberturaProposta", "")),
            "limite_recebimento": formatar_data(item.get("dataEncerramentoProposta", "")),
            "abertura_propostas": formatar_data(item.get("dataEncerramentoProposta", "")),
            # Novos campos API PNCP
            "numero_controle_pncp": numero_pncp,
            "processo": item.get("processo", ""),
            "valor_estimado_numerico": valor,
            "valor_homologado": valor_homologado,
            "cnpj_orgao": orgao_entidade.get("cnpj", ""),
            "codigo_ibge": unidade.get("codigoIbge", ""),
            "modalidade_id": item.get("modalidadeId"),
            "modo_disputa": item.get("modoDisputaNome", ""),
            "srp": item.get("srp", False),
            "amparo_legal": amparo.get("nome", ""),
            "data_publicacao_pncp": formatar_data(item.get("dataPublicacaoPncp", "")),
            "informacao_complementar": item.get("informacaoComplementar", ""),
            "link_processo_eletronico": item.get("linkProcessoEletronico", ""),
            "data_atualizacao_api": formatar_data(item.get("dataAtualizacao", ""))
        }
    
    def pesquisar(
        self,
        termos: List[str],
        ufs: List[str] = None,
        dias_ate_encerramento: int = 30,
        max_resultados: int = 5000,
        palavra_chave_id: int = None,
        data_publicacao_inicial: str = None
    ) -> List[Dict]:
        """
        Busca licitações na API PNCP e filtra por termos localmente.
        """
        resultados = []
        urls_vistas = set()
        
        # Data limite
        data_final = (datetime.now() + timedelta(days=dias_ate_encerramento)).strftime("%Y%m%d")
        
        # UFs a buscar
        ufs_busca = ufs if ufs else self.UFS_BRASIL
        
        print(f"🔍 Buscando licitações em {len(ufs_busca)} UF(s) até {data_final}")
        if data_publicacao_inicial:
            print(f"📅 Incremental: A partir de {data_publicacao_inicial}")
        print(f"🔎 Filtrando por termos: {termos}")
        
        for uf in ufs_busca:
            if len(resultados) >= max_resultados:
                break
            
            try:
                print(f"\n📍 Buscando em {uf}...")
                
                # Busca todas as páginas desta UF (aumentado para capturar tudo)
                items = self.client.buscar_todas_paginas(
                    uf=uf,
                    data_final=data_final,
                    max_paginas=500,
                    tamanho_pagina=50,
                    data_publicacao_inicial=data_publicacao_inicial
                )
                
                if not items:
                    print(f"   Nenhum resultado em {uf}")
                    continue
                
                print(f"   📊 {len(items)} licitações encontradas em {uf}")
                
                # Filtra por termos
                for item in items:
                    if len(resultados) >= max_resultados:
                        break
                    
                    # Verifica se contém algum dos termos
                    if not self._resultado_contem_termos(item, termos):
                        continue
                    
                    # Evita duplicatas
                    url = item.get("linkSistemaOrigem") or item.get("numeroControlePNCP", "")
                    if url in urls_vistas:
                        continue
                    urls_vistas.add(url)
                    
                    # Mapeia para formato do sistema
                    resultado = self._mapear_para_resultado_pesquisa(item, palavra_chave_id)
                    resultados.append(resultado)
                    
                    print(f"   ✓ {resultado['numero_processo']}: {resultado['titulo'][:50]}...")
                
            except Exception as e:
                print(f"   ❌ Erro ao buscar em {uf}: {e}")
                continue
        
        print(f"\n✅ Total: {len(resultados)} licitações encontradas para os termos")
        return resultados
    
    def pesquisar_por_uf(
        self,
        uf: str,
        termos: List[str] = None,
        dias_ate_encerramento: int = 30,
        max_resultados: int = 100,
        palavra_chave_id: int = None
    ) -> List[Dict]:
        """
        Busca licitações em uma UF específica.
        
        Args:
            uf: Sigla da UF (ex: "SP")
            termos: Termos para filtrar (opcional)
            dias_ate_encerramento: Dias à frente para buscar
            max_resultados: Máximo de resultados
            palavra_chave_id: ID da palavra-chave
        
        Returns:
            Lista de resultados no formato do sistema
        """
        return self.pesquisar(
            termos=termos or [],
            ufs=[uf.upper()],
            dias_ate_encerramento=dias_ate_encerramento,
            max_resultados=max_resultados,
            palavra_chave_id=palavra_chave_id
        )


# Teste rápido
if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO SERVIÇO DE BUSCA PNCP")
    print("=" * 60)
    
    service = PncpSearchService()
    
    # Teste: buscar licitações de saneamento em SP
    resultados = service.pesquisar(
        termos=["saneamento", "esgoto", "água"],
        ufs=["SP"],
        max_resultados=10
    )
    
    print("\n" + "=" * 60)
    print(f"RESULTADOS: {len(resultados)}")
    print("=" * 60)
    
    for i, r in enumerate(resultados[:5], 1):
        print(f"\n{i}. {r['numero_processo']}")
        print(f"   Título: {r['titulo'][:70]}...")
        print(f"   Órgão: {r['orgao']}")
        print(f"   UF: {r['uf']} | Município: {r['municipio']}")
        print(f"   Valor: {r['valor_estimado']}")
        print(f"   Data: {r['data_realizacao']}")
