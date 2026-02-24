"""
Scraper de Detalhes - Etapa 2: Busca Completa
Responsável por acessar a página de cada processo e extrair todas as informações
"""
import os
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests

from app.config import SELENIUM_HEADLESS, SELENIUM_TIMEOUT, DOWNLOADS_DIR


class DetalheScraper:
    """Scraper para página de detalhes do processo"""
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else SELENIUM_HEADLESS
        self.driver = None
        self.wait = None
    
    def _limpar_html(self, texto: str) -> str:
        """Remove tags HTML e limpa espaços extras de um texto"""
        if not texto:
            return ""
        # Remove tags HTML
        texto = re.sub(r'<[^>]+>', ' ', texto)
        # Remove &nbsp; e entidades HTML
        texto = re.sub(r'&nbsp;', ' ', texto)
        texto = re.sub(r'&[a-zA-Z]+;', ' ', texto)
        # Remove espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
    
    def _iniciar_driver(self):
        """Inicializa o driver do Chrome com configurações para download"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configurações de download
        prefs = {
            "download.default_directory": str(DOWNLOADS_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)
    
    def _fechar_driver(self):
        """Fecha o driver do Chrome"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def extrair_detalhes(self, url_processo: str) -> Dict:
        """
        Extrai todas as informações detalhadas de um processo
        
        Args:
            url_processo: URL da página do processo
        
        Returns:
            Dicionário com todas as informações extraídas
        """
        dados = {}
        
        try:
            self._iniciar_driver()
            print(f"📄 Acessando processo: {url_processo}")
            
            self.driver.get(url_processo)
            time.sleep(3)
            
            # Extrai informações básicas
            dados.update(self._extrair_info_basica())
            
            # Extrai informações detalhadas
            dados.update(self._extrair_informacoes())
            
            # Extrai datas
            dados.update(self._extrair_datas())
            
            print(f"✓ Detalhes extraídos com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao extrair detalhes: {e}")
            raise
        finally:
            self._fechar_driver()
        
        return dados
    
    def _extrair_info_basica(self) -> Dict:
        """Extrai informações básicas (título, número, status, órgão)"""
        dados = {}
        
        try:
            # Número do processo
            elem = self.driver.find_element(By.CSS_SELECTOR, "[class*='processo'], h2, .numero-processo")
            texto = elem.text
            match = re.search(r'(?:Nº\s*do\s*Processo:|P\.?E\.?)\s*([^\n]+)', texto, re.IGNORECASE)
            if match:
                dados['numero_processo'] = match.group(1).strip()
        except:
            dados['numero_processo'] = ""
        
        try:
            # Título/Objeto
            titulo = self.driver.find_element(By.CSS_SELECTOR, "h1, h2.titulo, .objeto-titulo")
            dados['titulo'] = titulo.text.strip()
            dados['objeto'] = dados['titulo']
        except:
            dados['titulo'] = ""
            dados['objeto'] = ""
        
        try:
            # Status
            status = self.driver.find_element(By.CSS_SELECTOR, "[class*='status'], .badge, .tag")
            dados['status'] = status.text.strip()
        except:
            dados['status'] = ""
        
        try:
            # Órgão
            orgao = self.driver.find_element(By.CSS_SELECTOR, "[class*='orgao'], [class*='comprador'], .entidade")
            dados['orgao'] = orgao.text.strip()
        except:
            dados['orgao'] = ""
        
        try:
            # Modalidade
            modalidade = self.driver.find_element(By.CSS_SELECTOR, "[class*='modalidade'], .tipo-licitacao")
            dados['modalidade'] = modalidade.text.strip()
        except:
            dados['modalidade'] = ""
        
        return dados
    
    def _extrair_informacoes(self) -> Dict:
        """Extrai a seção de Informações"""
        dados = {}
        
        try:
            # Pega o texto limpo da página inteira para garantir que temos tudo
            # Mas foca na seção Informações se possível
            try:
                secao = self.driver.find_element(By.XPATH, "//div[contains(@class, 'container')]//h2[contains(text(), 'Informações')]/ancestor::div[1]")
                texto_base = secao.text
            except:
                texto_base = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Extrai campos específicos com regex não-ganancioso e parando no início do próximo campo
            # Usamos lookahead para garantir que não pegamos o rótulo do campo seguinte
            campos = {
                'tipo': r'Tipo[:\s]+(.*?)(?=\s+(?:Tratamento|Operação|Presidente|Autoridade|Apoio|Origem|Modo|Legislação|Data|$))',
                'tratamento_fase_lances': r'Tratamento\s+da\s+Fase\s+de\s+Lances[:\s]+(.*?)(?=\s+(?:Operação|Presidente|Autoridade|Apoio|Origem|Modo|Legislação|Data|$))',
                'operacao': r'Operação[:\s]+(.*?)(?=\s+(?:Presidente|Autoridade|Apoio|Origem|Modo|Legislação|Data|$))',
                'pregoeiro': r'(?:Pregoeiro|Presidente\s+de\s+Comissão)[:\s]+(.*?)(?=\s+(?:Autoridade|Apoio|Origem|Modo|Legislação|Data|$))',
                'autoridade_competente': r'Autoridade\s+Competente[:\s]+(.*?)(?=\s+(?:Apoio|Origem|Modo|Legislação|Data|$))',
                'apoio': r'Apoio[:\s]+(.*?)(?=\s+(?:Origem|Modo|Legislação|Data|$))',
                'origem_recursos': r'Origem\s+dos\s+Recursos[:\s]+(.*?)(?=\s+(?:Modo|Legislação|Data|$))',
                'modo_disputa': r'(?:Modo\s+de\s+Disputa[^\n]*?)[:\s]+(.*?)(?=\s+(?:Legislação|Data|$))',
                'legislacao_aplicavel': r'Legislação\s+Aplicável[:\s]+(.*?)(?=\s+(?:Data|$))',
            }
            
            for campo, padrao in campos.items():
                match = re.search(padrao, texto_base, re.IGNORECASE | re.DOTALL)
                if match:
                    dados[campo] = self._limpar_html(match.group(1).strip())
                else:
                    dados[campo] = ""
            
            # Se pregoeiro ainda estiver vazio, tenta uma busca mais genérica
            if not dados.get('pregoeiro'):
                match = re.search(r'Presidente.*?[:\s]+([^\n]+)', texto_base, re.IGNORECASE)
                if match:
                    dados['pregoeiro'] = self._limpar_html(match.group(1).strip())
            
            # Extrai valor estimado
            padroes_valor = [
                r'Valor\s+(?:Estimado|Total|Global|Referência)[:\s]*R\$\s*([\d.,]+)',
                r'R\$\s*([\d.,]+(?:[.,]\d{2})?)',
                r'Valor[:\s]+R\$\s*([\d.,]+)',
            ]
            
            for padrao in padroes_valor:
                match = re.search(padrao, texto_base, re.IGNORECASE)
                if match:
                    valor = match.group(1).strip()
                    # Valida que o valor é significativo (maior que R$ 100)
                    try:
                        valor_num = float(valor.replace('.', '').replace(',', '.'))
                        if valor_num > 100:
                            dados['valor_estimado'] = f"R$ {valor}"
                            break
                    except:
                        pass
            
            if 'valor_estimado' not in dados:
                dados['valor_estimado'] = ""
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair informações: {e}")
        
        return dados
    
    def _extrair_datas(self) -> Dict:
        """Extrai a seção de Datas"""
        dados = {}
        
        try:
            try:
                secao = self.driver.find_element(By.XPATH, "//div[contains(@class, 'container')]//h2[contains(text(), 'Datas')]/ancestor::div[1]")
                texto_base = secao.text
            except:
                texto_base = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Regex específicos para datas, parando no próximo rótulo
            campos_data = {
                'data_publicacao': r'Data\s+de\s+Publicação[:\s]+(.*?)(?=\s+(?:Início|Limite|Abertura|Encerramento|Edital|Participação|$))',
                'inicio_propostas': r'Início\s+das\s+Propostas[:\s]+(.*?)(?=\s+(?:Limite|Abertura|Encerramento|Edital|Participação|$))',
                'limite_impugnacoes': r'Limite\s+para\s+Impugnações[:\s]+(.*?)(?=\s+(?:Limite|Abertura|Encerramento|Edital|Participação|$))',
                'limite_esclarecimentos': r'Limite\s+para\s+Esclarecimentos[:\s]+(.*?)(?=\s+(?:Limite|Abertura|Encerramento|Edital|Participação|$))',
                'limite_recebimento_propostas': r'Limite\s+p/\s+Recebimento[^\n]*?[:\s]+(.*?)(?=\s+(?:Abertura|Encerramento|Edital|Participação|$))',
                'abertura_propostas': r'Abertura\s+das\s+Propostas[:\s]+(.*?)(?=\s+(?:Encerramento|Edital|Participação|$))',
            }
            
            for campo, padrao in campos_data.items():
                match = re.search(padrao, texto_base, re.IGNORECASE | re.DOTALL)
                if match:
                    dados[campo] = self._limpar_html(match.group(1).strip())
                else:
                    dados[campo] = ""
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair datas: {e}")
        
        return dados
    
    def baixar_documentos(self, url_processo: str, pasta_destino: Path) -> List[str]:
        """
        Baixa todos os documentos do edital
        
        Args:
            url_processo: URL da página do processo
            pasta_destino: Pasta onde salvar os documentos
        
        Returns:
            Lista de caminhos dos arquivos baixados
        """
        arquivos_baixados = []
        
        try:
            self._iniciar_driver()
            print(f"📥 Baixando documentos de: {url_processo}")
            
            self.driver.get(url_processo)
            time.sleep(3)
            
            # Clica no botão/aba de Documentos
            try:
                btn_documentos = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'DOCUMENTOS')] | //a[contains(text(), 'DOCUMENTOS')]"))
                )
                btn_documentos.click()
                time.sleep(2)
            except:
                print("⚠️ Botão DOCUMENTOS não encontrado, tentando localizar links diretos")
            
            # Encontra todos os links de documentos
            links_docs = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "a[href*='.pdf'], a[href*='.doc'], a[href*='.zip'], a[href*='download'], a[class*='download']"
            )
            
            # Cria pasta de destino
            pasta_edital = pasta_destino / "Edital"
            pasta_edital.mkdir(parents=True, exist_ok=True)
            
            for link in links_docs:
                try:
                    url_doc = link.get_attribute('href')
                    if not url_doc or url_doc.startswith('javascript:'):
                        # Tenta clicar no link para ver se o download inicia
                        print(f"  🔗 Link dinâmico detectado, tentando clicar...")
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(2)
                        continue

                    nome_arquivo = link.text.strip() or url_doc.split('/')[-1]
                    
                    # Limpa o nome do arquivo
                    nome_arquivo = re.sub(r'[<>:"/\\|?*]', '_', nome_arquivo)
                    if not nome_arquivo.endswith(('.pdf', '.doc', '.docx', '.zip', '.xls', '.xlsx')):
                        # Tenta descobrir o nome real se o link for dinâmico
                        nome_arquivo += '.pdf'
                    
                    # Baixa o arquivo
                    arquivo_path = pasta_edital / nome_arquivo
                    
                    # Usa cookies da sessão do Selenium para o request
                    cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
                    headers = {
                        "User-Agent": self.driver.execute_script("return navigator.userAgent;")
                    }
                    
                    response = requests.get(url_doc, timeout=60, cookies=cookies, headers=headers)
                    if response.status_code == 200:
                        with open(arquivo_path, 'wb') as f:
                            f.write(response.content)
                        arquivos_baixados.append(str(arquivo_path))
                        print(f"  ✓ {nome_arquivo}")
                    else:
                        print(f"  ⚠️ Erro HTTP {response.status_code} ao baixar {nome_arquivo}")
                        # Tenta clicar como fallback
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(2)
                    
                except Exception as e:
                    print(f"  ⚠️ Erro ao baixar documento: {e}")
            
            print(f"✓ {len(arquivos_baixados)} documentos baixados")
            
        except Exception as e:
            print(f"❌ Erro ao baixar documentos: {e}")
        finally:
            self._fechar_driver()
        
        return arquivos_baixados


# Teste
if __name__ == "__main__":
    scraper = DetalheScraper(headless=False)
    
    # URL de exemplo
    url_teste = "https://www.portaldecompraspublicas.com.br/processos/..."
    
    detalhes = scraper.extrair_detalhes(url_teste)
    print("\n--- Detalhes extraídos ---")
    for k, v in detalhes.items():
        print(f"{k}: {v}")
