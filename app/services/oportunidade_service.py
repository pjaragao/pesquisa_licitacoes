"""
Serviço de Oportunidades
Gerencia a criação de oportunidades a partir de resultados de pesquisa
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.models.resultado_pesquisa import ResultadoPesquisa
from app.models.oportunidade import Oportunidade
from app.scrapers.detalhe_scraper import DetalheScraper
from app.config import DOWNLOADS_DIR


class OportunidadeService:
    """Serviço para criar e gerenciar oportunidades"""
    
    def __init__(self):
        self.scraper = DetalheScraper()
    
    def criar_oportunidade(self, resultado_id: int) -> Optional[Oportunidade]:
        """
        Cria uma oportunidade a partir de um resultado de pesquisa
        
        1. Busca o resultado no banco
        2. Acessa a página do processo e extrai detalhes
        3. Baixa os documentos do edital
        4. Cria a oportunidade com código OPXXYYY
        
        Args:
            resultado_id: ID do resultado de pesquisa
        
        Returns:
            Oportunidade criada ou None se falhar
        """
        # Busca o resultado
        resultado = ResultadoPesquisa.buscar_por_id(resultado_id)
        if not resultado:
            print(f"❌ Resultado {resultado_id} não encontrado")
            return None
        
        if not resultado.url_processo:
            print(f"❌ Resultado {resultado_id} não possui URL do processo")
            return None
        
        print(f"\n🔄 Criando oportunidade para: {resultado.titulo[:50]}...")
        
        try:
            # Extrai detalhes do processo
            detalhes = self.scraper.extrair_detalhes(resultado.url_processo)
            
            # Gera código da oportunidade
            codigo = Oportunidade.gerar_codigo()
            
            # Cria pasta local para documentos
            pasta_oportunidade = DOWNLOADS_DIR / codigo
            pasta_oportunidade.mkdir(parents=True, exist_ok=True)
            
            # Baixa documentos
            arquivos = self.scraper.baixar_documentos(
                resultado.url_processo, 
                pasta_oportunidade
            )
            
            # Monta dados da oportunidade
            dados = {
                'resultado_id': resultado_id,
                'numero_processo': detalhes.get('numero_processo') or resultado.numero_processo,
                'titulo': detalhes.get('titulo') or resultado.titulo,
                'objeto': detalhes.get('objeto') or resultado.objeto,
                'orgao': detalhes.get('orgao') or resultado.orgao,
                'uf': resultado.uf,
                'municipio': resultado.municipio,
                'tipo': detalhes.get('tipo'),
                'modalidade': detalhes.get('modalidade') or resultado.modalidade,
                'tratamento_fase_lances': detalhes.get('tratamento_fase_lances'),
                'operacao': detalhes.get('operacao'),
                'modo_disputa': detalhes.get('modo_disputa'),
                'pregoeiro': detalhes.get('pregoeiro'),
                'autoridade_competente': detalhes.get('autoridade_competente'),
                'apoio': detalhes.get('apoio'),
                'origem_recursos': detalhes.get('origem_recursos'),
                'legislacao_aplicavel': detalhes.get('legislacao_aplicavel'),
                'data_publicacao': detalhes.get('data_publicacao'),
                'inicio_propostas': detalhes.get('inicio_propostas'),
                'limite_impugnacoes': detalhes.get('limite_impugnacoes'),
                'limite_esclarecimentos': detalhes.get('limite_esclarecimentos'),
                'limite_recebimento_propostas': detalhes.get('limite_recebimento_propostas'),
                'abertura_propostas': detalhes.get('abertura_propostas'),
                'status': detalhes.get('status') or resultado.status,
                'pasta_local': str(pasta_oportunidade),
                'url_processo': resultado.url_processo,
                'valor_estimado': detalhes.get('valor_estimado') or resultado.valor_estimado,
            }
            
            # Cria a oportunidade
            oportunidade = Oportunidade.criar(dados)
            
            # Marca o resultado como selecionado
            resultado.marcar_selecionado()
            
            print(f"✓ Oportunidade {oportunidade.codigo} criada com sucesso!")
            print(f"  📁 Documentos em: {pasta_oportunidade}")
            print(f"  📄 {len(arquivos)} arquivo(s) baixado(s)")
            
            return oportunidade
            
        except Exception as e:
            print(f"❌ Erro ao criar oportunidade: {e}")
            raise
    
    def listar_oportunidades(self) -> list:
        """Lista todas as oportunidades"""
        return Oportunidade.listar_todas()
    
    def buscar_oportunidade(self, codigo: str) -> Optional[Oportunidade]:
        """Busca oportunidade por código"""
        return Oportunidade.buscar_por_codigo(codigo)
