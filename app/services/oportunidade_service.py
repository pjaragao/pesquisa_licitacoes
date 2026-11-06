"""
Serviço de Oportunidades
Gerencia a criação de oportunidades a partir de resultados de pesquisa
"""
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading
import requests
import time
import os
import re

from app import get_db
from app.models.resultado_pesquisa import ResultadoPesquisa
from app.models.oportunidade import Oportunidade
from app.config import DOWNLOADS_DIR


class OportunidadeService:
    """Serviço para criar e gerenciar oportunidades"""
    
    def criar_oportunidade(self, resultado_id: int) -> Optional[Oportunidade]:
        """
        Cria uma oportunidade a partir de um resultado de pesquisa.
        """
        resultado = ResultadoPesquisa.buscar_por_id(resultado_id)
        if not resultado:
            return None
        
        # Verifica se já existe
        ov = Oportunidade.buscar_por_resultado_id(resultado_id)
        if ov:
            return ov
            
        pasta_local = str(DOWNLOADS_DIR / f"tmp_{resultado_id}") # Pasta temporária, código final vem do criar()
        
        # Mapeia dados do resultado para a oportunidade
        dados = {
            'resultado_id': resultado_id,
            'numero_processo': resultado.numero_processo,
            'titulo': resultado.titulo,
            'objeto': resultado.objeto,
            'orgao': resultado.orgao,
            'uf': resultado.uf,
            'municipio': resultado.municipio,
            'modalidade': resultado.modalidade,
            'status': resultado.status,
            'url_processo': resultado.url_processo,
            'valor_estimado': resultado.valor_estimado,
            'inicio_propostas': resultado.inicio_propostas,
            'abertura_propostas': resultado.abertura_propostas,
            'pasta_local': pasta_local # Será corrigido abaixo se necessário
        }
        
        # Cria no banco (o modelo gera o código OP... e insere)
        o = Oportunidade.criar(dados)
        
        if o:
            # Atualiza pasta_local com o código oficial gerado
            oficial_pasta = str(DOWNLOADS_DIR / o.codigo)
            o.pasta_local = oficial_pasta
            
            # Persiste o caminho correto da pasta
            with get_db() as conn:
                conn.execute("UPDATE oportunidades SET pasta_local = ? WHERE id = ?", (oficial_pasta, o.id))
            
            # Marca o resultado como selecionado na pesquisa
            resultado.marcar_selecionado(True)
            
            # Dispara download em segundo plano
            if resultado.numero_controle_pncp:
                thread = threading.Thread(
                    target=self._baixar_arquivos_background,
                    args=(resultado.numero_controle_pncp, Path(oficial_pasta))
                )
                thread.daemon = True
                thread.start()
                
            return o
            
        return None

    def sincronizar_cache_pncp(self, oportunidade_id: int, control: str):
        """Busca itens e arquivos do PNCP e salva no cache (banco)"""
        oportunidade = Oportunidade.buscar_por_id(oportunidade_id)
        if not oportunidade:
            return
            
        from app.services.pncp_api_client import PncpApiClient
        client = PncpApiClient()
        ids = self._extrair_pncp_ids(control)
        if not ids:
            return
            
        cnpj, ano, seq = ids
        
        # 1. Itens
        itens = client.buscar_contratacao_itens(cnpj, ano, seq)
        if itens:
            oportunidade.salvar_itens_cache(itens)
            
        # 2. Arquivos
        arquivos = client.buscar_contratacao_arquivos(cnpj, ano, seq)
        if arquivos:
            oportunidade.salvar_arquivos_cache(arquivos)
            
        # 3. Histórico
        historico = client.buscar_contratacao_historico(cnpj, ano, seq)
        if historico:
            oportunidade.salvar_historico_cache(historico)

    def obter_itens(self, oportunidade_id: int, force_refresh=False):
        oportunidade = Oportunidade.buscar_por_id(oportunidade_id)
        cache = oportunidade.obter_itens_cache() if oportunidade else []
        if (not cache or force_refresh) and oportunidade:
            resultado = ResultadoPesquisa.buscar_por_id(oportunidade.resultado_id)
            if resultado and resultado.numero_controle_pncp:
                self.sincronizar_cache_pncp(oportunidade_id, resultado.numero_controle_pncp)
                cache = oportunidade.obter_itens_cache()
        return cache

    def obter_arquivos(self, oportunidade_id: int, force_refresh=False):
        oportunidade = Oportunidade.buscar_por_id(oportunidade_id)
        cache = oportunidade.obter_arquivos_cache() if oportunidade else []
        if (not cache or force_refresh) and oportunidade:
            resultado = ResultadoPesquisa.buscar_por_id(oportunidade.resultado_id)
            if resultado and resultado.numero_controle_pncp:
                self.sincronizar_cache_pncp(oportunidade_id, resultado.numero_controle_pncp)
                cache = oportunidade.obter_arquivos_cache()
        return cache

    def obter_historico(self, oportunidade_id: int, force_refresh=False):
        oportunidade = Oportunidade.buscar_por_id(oportunidade_id)
        cache = oportunidade.obter_historico_cache() if oportunidade else []
        if (not cache or force_refresh) and oportunidade:
            resultado = ResultadoPesquisa.buscar_por_id(oportunidade.resultado_id)
            if resultado and resultado.numero_controle_pncp:
                self.sincronizar_cache_pncp(oportunidade_id, resultado.numero_controle_pncp)
                cache = oportunidade.obter_historico_cache()
        return cache

    def _extrair_pncp_ids(self, control: str):
        control = str(control).strip().replace('\n', '').replace('\r', '')
        try:
            if "/" in control and "-" in control:
                parts = control.split("/")
                ano = int(parts[1])
                prefix = parts[0]
                cnpj = prefix.split("-")[0].replace(".", "").replace("/", "")
                sequencial = int(prefix.split("-")[-1])
            else:
                cnpj = control[:14]
                ano = int(control[14:18])
                sequencial = int(control[18:])
            return cnpj, ano, sequencial
        except:
            return None
            
    def _baixar_arquivos_background(self, control: str, pasta_local: Path):
        """Baixa os arquivos do PNCP com ultra-resiliência."""
        control = str(control).strip().replace('\n', '').replace('\r', '')
        ids = self._extrair_pncp_ids(control)
        if not ids:
            return
            
        cnpj, ano, seq = ids
        from app.services.pncp_api_client import PncpApiClient
        client = PncpApiClient()
        
        arquivos_resp = client.buscar_contratacao_arquivos(cnpj, ano, seq)
        arquivos = []
        if isinstance(arquivos_resp, list):
            arquivos = arquivos_resp
        elif isinstance(arquivos_resp, dict) and 'data' in arquivos_resp:
            arquivos = arquivos_resp['data']
            
        if not arquivos:
            return

        os.makedirs(pasta_local, exist_ok=True)
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        for index, arq in enumerate(arquivos, start=1):
            link = arq.get('url') or arq.get('linkArquivo') or arq.get('href') or arq.get('uri')
            titulo = arq.get('tituloArquivo') or arq.get('nomeArquivo') or arq.get('titulo') or arq.get('descricao')
            if not titulo or titulo == 'None':
                titulo = f"documento_{index}.pdf"
            
            if '.' not in titulo:
                titulo += '.pdf'
                
            titulo_seguro = re.sub(r'[^a-zA-Z0-9\._-]', '_', titulo).strip()
            
            if link:
                caminho_arquivo = pasta_local / titulo_seguro
                if caminho_arquivo.exists() and caminho_arquivo.stat().st_size > 0:
                    continue

                try:
                    with requests.get(link, stream=True, timeout=120, verify=False, headers=headers) as r:
                        r.raise_for_status()
                        with open(caminho_arquivo, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=16384):
                                f.write(chunk)
                except Exception as e:
                    print(f"Erro download: {e}")
            
            time.sleep(0.5)

    def listar_oportunidades(self) -> list:
        return Oportunidade.listar_todas()
    
    def buscar_oportunidade(self, codigo: str) -> Optional[Oportunidade]:
        return Oportunidade.buscar_por_codigo(codigo)
