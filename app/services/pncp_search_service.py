"""
Serviço de Busca PNCP - Busca licitações via API e filtra por palavras-chave

Dois modos de busca:
  - Total: Usa /v1/contratacoes/proposta (tudo com propostas abertas)
  - Incremental: Usa /v1/contratacoes/publicacao (por data de publicação)
"""
from typing import Dict, List, Optional, Callable
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
    
    def _quais_termos_combinam(self, resultado: Dict, termos: List[str]) -> List[str]:
        """
        Retorna lista de termos que combinam com o resultado.
        Busca no objeto da compra e informação complementar.
        """
        objeto = resultado.get("objetoCompra", "") or ""
        info_complementar = resultado.get("informacaoComplementar", "") or ""
        texto_completo = f"{objeto} {info_complementar}"
        
        matched = []
        for termo in termos:
            if self._contem_termo(texto_completo, termo):
                matched.append(termo)
        return matched
    
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
    
    def _filtrar_e_mapear(
        self, 
        items: List[Dict], 
        termos: List[str], 
        urls_vistas: set,
        max_resultados: int,
        resultados: list
    ) -> int:
        """
        Filtra itens da API por termos e mapeia para formato do sistema.
        Retorna quantidade de matches encontrados.
        Modifica resultados e urls_vistas in-place.
        """
        matches = 0
        
        for item in items:
            if len(resultados) >= max_resultados:
                break
            
            # Verifica quais termos combinam
            matched_termos = self._quais_termos_combinam(item, termos)
            if not matched_termos:
                continue
            
            # Evita duplicatas pelo número de controle PNCP
            chave = item.get("numeroControlePNCP") or item.get("linkSistemaOrigem", "")
            if not chave or chave in urls_vistas:
                continue
            urls_vistas.add(chave)
            
            # Mapeia para formato do sistema
            resultado = self._mapear_para_resultado_pesquisa(item)
            resultado['_matched_termos'] = matched_termos
            resultados.append(resultado)
            matches += 1
        
        return matches
    
    def pesquisar(
        self,
        termos: List[str],
        ufs: List[str] = None,
        dias_ate_encerramento: int = 60,
        max_resultados: int = 5000,
        on_uf_progress: Callable = None
    ) -> List[Dict]:
        """
        Busca TOTAL: licitações com propostas abertas, filtradas por termos.
        Usa endpoint /v1/contratacoes/proposta.
        Faz UMA passagem por UF e filtra contra TODOS os termos.
        
        Args:
            termos: Lista de termos para filtrar (todos de uma vez)
            ufs: Lista de UFs para buscar
            dias_ate_encerramento: Dias à frente para propostas
            max_resultados: Máximo de resultados
            on_uf_progress: Callback(uf, uf_index, total_ufs, uf_matches, uf_total_items)
        
        Returns:
            Lista de resultados, cada um com '_matched_termos'
        """
        resultados = []
        urls_vistas = set()
        
        # Data limite
        data_final = (datetime.now() + timedelta(days=dias_ate_encerramento)).strftime("%Y%m%d")
        
        # UFs a buscar
        ufs_busca = ufs if ufs else self.UFS_BRASIL
        
        print(f"🔍 [TOTAL] Buscando licitações em {len(ufs_busca)} UF(s) até {data_final}")
        print(f"🔎 Filtrando por {len(termos)} termos: {termos}")
        
        for uf_idx, uf in enumerate(ufs_busca):
            if len(resultados) >= max_resultados:
                break
            
            try:
                print(f"\n📍 Buscando em {uf}... ({uf_idx+1}/{len(ufs_busca)})")
                
                # Busca todas as páginas desta UF
                items = self.client.buscar_todas_paginas(
                    uf=uf,
                    data_final=data_final,
                    max_paginas=100,
                    tamanho_pagina=50
                )
                
                if not items:
                    print(f"   Nenhum resultado em {uf}")
                    if on_uf_progress:
                        on_uf_progress(uf, uf_idx, len(ufs_busca), 0, 0)
                    continue
                
                print(f"   📊 {len(items)} licitações encontradas em {uf}")
                
                # Filtra contra TODOS os termos de uma vez
                uf_matches = self._filtrar_e_mapear(
                    items, termos, urls_vistas, max_resultados, resultados
                )
                
                print(f"   ✅ {uf_matches} matches com os termos em {uf}")
                
                if on_uf_progress:
                    on_uf_progress(uf, uf_idx, len(ufs_busca), uf_matches, len(items))
                
            except Exception as e:
                print(f"   ❌ Erro ao buscar em {uf}: {e}")
                if on_uf_progress:
                    on_uf_progress(uf, uf_idx, len(ufs_busca), 0, 0)
                continue
        
        print(f"\n✅ [TOTAL] {len(resultados)} licitações encontradas para os termos")
        return resultados
    
    def pesquisar_incremental(
        self,
        termos: List[str],
        ufs: List[str] = None,
        data_inicial: str = None,
        max_resultados: int = 5000,
        on_uf_progress: Callable = None
    ) -> List[Dict]:
        """
        Busca INCREMENTAL: licitações publicadas desde data_inicial.
        Usa endpoint /v1/contratacoes/publicacao.
        Itera pelas modalidades principais (campo obrigatório nesse endpoint).
        
        Args:
            termos: Lista de termos para filtrar
            ufs: Lista de UFs para buscar
            data_inicial: Data inicial (YYYYMMDD) - desde quando buscar
            max_resultados: Máximo de resultados
            on_uf_progress: Callback(uf, uf_index, total_ufs, uf_matches, uf_total_items)
        
        Returns:
            Lista de resultados, cada um com '_matched_termos'
        """
        resultados = []
        urls_vistas = set()
        
        # Se não tem data_inicial, faz busca total
        if not data_inicial:
            print("⚠️ Sem data inicial para incremental, fazendo busca total...")
            return self.pesquisar(termos, ufs, on_uf_progress=on_uf_progress)
        
        data_final = datetime.now().strftime("%Y%m%d")
        ufs_busca = ufs if ufs else self.UFS_BRASIL
        modalidades = self.client.MODALIDADES_PRINCIPAIS
        
        print(f"🔍 [INCREMENTAL] Buscando publicações de {data_inicial} até {data_final}")
        print(f"   📋 {len(modalidades)} modalidades × {len(ufs_busca)} UFs")
        print(f"   🔎 Filtrando por {len(termos)} termos: {termos}")
        
        for uf_idx, uf in enumerate(ufs_busca):
            if len(resultados) >= max_resultados:
                break
            
            try:
                print(f"\n📍 Incremental em {uf}... ({uf_idx+1}/{len(ufs_busca)})")
                uf_total_items = 0
                uf_matches = 0
                
                # Itera pelas modalidades (obrigatório no endpoint /publicacao)
                for modalidade_id in modalidades:
                    if len(resultados) >= max_resultados:
                        break
                    
                    try:
                        items = self.client.buscar_todas_paginas_publicacao(
                            data_inicial=data_inicial,
                            data_final=data_final,
                            codigo_modalidade=modalidade_id,
                            uf=uf,
                            max_paginas=50,
                            tamanho_pagina=50
                        )
                        
                        if not items:
                            continue
                        
                        uf_total_items += len(items)
                        
                        # Filtra contra TODOS os termos
                        matches = self._filtrar_e_mapear(
                            items, termos, urls_vistas, max_resultados, resultados
                        )
                        uf_matches += matches
                        
                    except Exception as e:
                        modal_nome = self.client.MODALIDADES.get(modalidade_id, f"#{modalidade_id}")
                        print(f"     ⚠️ Erro modalidade {modal_nome} em {uf}: {e}")
                        continue
                
                if uf_total_items > 0:
                    print(f"   📊 {uf_total_items} publicações / ✅ {uf_matches} matches em {uf}")
                else:
                    print(f"   Nenhuma publicação nova em {uf}")
                
                if on_uf_progress:
                    on_uf_progress(uf, uf_idx, len(ufs_busca), uf_matches, uf_total_items)
                
            except Exception as e:
                print(f"   ❌ Erro ao buscar em {uf}: {e}")
                if on_uf_progress:
                    on_uf_progress(uf, uf_idx, len(ufs_busca), 0, 0)
                continue
        
        print(f"\n✅ [INCREMENTAL] {len(resultados)} novas licitações encontradas")
        return resultados


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
        print(f"   Termos: {r.get('_matched_termos', [])}")
