"""
Serviço de Oportunidades
Gerencia a criação de oportunidades a partir de resultados de pesquisa
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.models.resultado_pesquisa import ResultadoPesquisa
from app.models.oportunidade import Oportunidade
from app.config import DOWNLOADS_DIR


class OportunidadeService:
    """Serviço para criar e gerenciar oportunidades"""
    
    def criar_oportunidade(self, resultado_id: int) -> Optional[Oportunidade]:
        """
        Cria uma oportunidade a partir de um resultado de pesquisa.
        Usa os dados já disponíveis no resultado (vindos da API PNCP).
        
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
        
        print(f"\n🔄 Criando oportunidade para: {resultado.titulo[:50]}...")
        
        try:
            # Gera código da oportunidade
            codigo = Oportunidade.gerar_codigo()
            
            # Cria pasta local para documentos
            pasta_oportunidade = DOWNLOADS_DIR / codigo
            pasta_oportunidade.mkdir(parents=True, exist_ok=True)
            
            # Monta dados da oportunidade usando dados já disponíveis do resultado (API PNCP)
            dados = {
                'resultado_id': resultado_id,
                'numero_processo': resultado.numero_processo,
                'titulo': resultado.titulo,
                'objeto': resultado.objeto,
                'orgao': resultado.orgao,
                'uf': resultado.uf,
                'municipio': resultado.municipio,
                'modalidade': resultado.modalidade,
                'modo_disputa': getattr(resultado, 'modo_disputa', ''),
                'inicio_propostas': resultado.inicio_propostas,
                'limite_recebimento_propostas': resultado.limite_recebimento,
                'abertura_propostas': resultado.abertura_propostas,
                'status': resultado.status,
                'pasta_local': str(pasta_oportunidade),
                'url_processo': resultado.url_processo,
                'valor_estimado': resultado.valor_estimado,
            }
            
            # Cria a oportunidade
            oportunidade = Oportunidade.criar(dados)
            
            # Marca o resultado como selecionado
            resultado.marcar_selecionado()
            
            print(f"✓ Oportunidade {oportunidade.codigo} criada com sucesso!")
            print(f"  📁 Pasta: {pasta_oportunidade}")
            
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
