"""
Service: GenKit Integration
Serviço para comunicação com o servidor GenKit via HTTP
"""
import requests
import time
import logging
from typing import List, Dict, Any, Optional
import os


class GenkitService:
    """Serviço para integração com o servidor GenKit"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('GENKIT_URL', 'http://localhost:3400')
    
    def _post(self, endpoint: str, data: dict, retries: int = 3, backoff_factor: float = 2.0) -> dict:
        """
        Faz uma requisição POST para o GenKit com lógica de retentativa para erros 429.
        """
        for i in range(retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    timeout=120  # 2 minutos de timeout
                )
                
                # Se for 429 (Too Many Requests), esperamos e tentamos novamente
                if response.status_code == 429 and i < retries:
                    wait_time = backoff_factor * (2 ** i)
                    print(f"⚠️ Limite de cota atingido (429). Tentando novamente em {wait_time}s... ({i+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.ConnectionError:
                if i < retries:
                    time.sleep(1)
                    continue
                raise Exception("Não foi possível conectar ao servidor GenKit. Verifique se ele está rodando.")
            except requests.exceptions.Timeout:
                if i < retries:
                    continue
                raise Exception("Timeout na requisição ao GenKit. Tente novamente.")
            except requests.exceptions.RequestException as e:
                # Se o erro contiver 429 na mensagem (caso o GenKit retorne 500 mas com erro 429 interno)
                if "429" in str(e) and i < retries:
                    wait_time = backoff_factor * (2 ** i)
                    print(f"⚠️ Erro 429 detectado na mensagem. Tentando novamente em {wait_time}s... ({i+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                
                raise Exception(f"Erro na comunicação com GenKit: {str(e)}")
        
        raise Exception("Limite de requisições excedido após múltiplas tentativas.")
    
    def health_check(self) -> bool:
        """Verifica se o servidor GenKit está rodando"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def classificar_resultado(self, prompt_empresa: str, resultado: dict, model: str = None) -> dict:
        """
        Classifica um único resultado de licitação.
        """
        data = {
            'promptEmpresa': prompt_empresa,
            'resultado': {
                'id': resultado.get('id'),
                'titulo': resultado.get('titulo'),
                'objeto': resultado.get('objeto'),
                'orgao': resultado.get('orgao'),
                'uf': resultado.get('uf'),
                'modalidade': resultado.get('modalidade'),
                'status': resultado.get('status'),
                'valorEstimado': resultado.get('valor_estimado'),
            }
        }
        
        if model:
            data['model'] = model
            
        return self._post('/api/classificar', data)
    
    def classificar_lote(self, prompt_empresa: str, resultados: List[dict], model: str = None) -> List[dict]:
        """
        Classifica múltiplos resultados de licitação em lote.
        """
        data = {
            'promptEmpresa': prompt_empresa,
            'resultados': [
                {
                    'id': r.get('id'),
                    'titulo': r.get('titulo'),
                    'objeto': r.get('objeto'),
                    'orgao': r.get('orgao'),
                    'uf': r.get('uf'),
                    'modalidade': r.get('modalidade'),
                    'status': r.get('status'),
                    'valorEstimado': r.get('valor_estimado'),
                }
                for r in resultados
            ]
        }
        
        if model:
            data['model'] = model
            
        response = self._post('/api/classificar-lote', data)
        return response.get('classificacoes', [])
    
    def listar_modelos(self) -> List[dict]:
        """Lista modelos disponíveis no GenKit"""
        try:
            response = requests.get(f"{self.base_url}/api/modelos", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao listar modelos: {e}")
            return [
                {'id': 'gemini-2.0-flash', 'name': 'Gemini 2.0 Flash (Default)'}
            ]
    
    def otimizar_prompt(self, prompt_atual: str) -> dict:
        """
        Otimiza/melhora o prompt da empresa.
        """
        data = {
            'promptAtual': prompt_atual
        }
        
        return self._post('/api/otimizar-prompt', data)


# Instância singleton do serviço
genkit_service = GenkitService()
