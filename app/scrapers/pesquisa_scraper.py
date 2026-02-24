"""
Scraper de Pesquisa - Etapa 1: Busca Resumida
Versão 6.0: Filtros rigorosos e extração melhorada
"""
import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from app.config import PORTAL_BASE_URL, PORTAL_SEARCH_URL, SELENIUM_HEADLESS, SELENIUM_TIMEOUT


class PesquisaScraper:
    """Scraper para página de pesquisa do Portal de Compras Públicas"""
    
    # Frases que indicam que NÃO é uma licitação real (são banners/propagandas)
    TEXTOS_BANNERS = [
        "Receba alertas de licitações",
        "Receba alertas do seu Estado",
        "área de interesse",
        "CENTRAL DE ATENDIMENTO",
        "0800 730 5455",
        "3003-5455",
        "FAZER LOGIN",
        "CADASTRE-SE",
        "(61) 3120-3700",
        "(61) 3142-4887",
        "Buscar no Portal",
        "Parceiros",
        "Faça parte",
        "Cadastre sua empresa",
    ]
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else SELENIUM_HEADLESS
        self.driver = None
        self.wait = None
    
    def _iniciar_driver(self):
        """Inicializa o driver do Chrome"""
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
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)
        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(5)
    
    def _fechar_driver(self):
        """Fecha o driver do Chrome"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _e_texto_de_banner(self, texto: str) -> bool:
        """Verifica se o texto é de um banner/propaganda do site"""
        if not texto:
            return True
            
        texto_upper = texto.upper()
        for banner in self.TEXTOS_BANNERS:
            if banner.upper() in texto_upper:
                return True
        
        return False
    
    def _e_licitacao_valida(self, titulo: str, url: str) -> bool:
        """Verifica se é uma licitação real, não um banner"""
        if not titulo or not url:
            return False
        
        # Banner não tem URL de processo real
        if '/processos/' not in url:
            return False
            
        # Banners típicos
        if self._e_texto_de_banner(titulo):
            return False
        
        # Título muito curto provavelmente não é licitação
        if len(titulo) < 30:
            return False
            
        # Licitações reais geralmente começam com verbo ou substantivo técnico
        palavras_validas = [
            'contrat', 'aquisição', 'prestação', 'serviço', 'fornecimento',
            'compra', 'obra', 'execução', 'implantação', 'manutenção',
            'locação', 'construção', 'reforma', 'registro', 'sistema',
            'material', 'equipamento', 'veículo', 'alimentos', 'medicamento',
        ]
        
        titulo_lower = titulo.lower()
        tem_palavra_valida = any(p in titulo_lower for p in palavras_validas)
        
        return tem_palavra_valida
    
    def pesquisar(self, termo: str, max_resultados: int = 200, max_paginas: int = 10, status_filtro: str = "12") -> List[Dict]:
        """
        Pesquisa por um termo no portal e navega pelas páginas de resultados.
        
        Args:
            termo: Termo de busca
            max_resultados: Máximo de resultados a coletar
            max_paginas: Máximo de páginas a navegar
            status_filtro: Código do status (12=Recebendo Propostas, 1=Em Andamento, etc.)
        """
        resultados = []
        urls_processadas = set()
        
        try:
            self._iniciar_driver()
            print(f"🔍 Pesquisando por: '{termo}' (status: {status_filtro})")
            
            # Monta URL com filtro de status
            url_pesquisa = f"{PORTAL_SEARCH_URL}?objeto={termo}"
            if status_filtro:
                url_pesquisa += f"&status={status_filtro}"
            
            print(f"📡 Acessando: {url_pesquisa}")
            self.driver.get(url_pesquisa)
            
            time.sleep(3)
            self._fechar_popup_cookies()
            
            time.sleep(4)
            self._aguardar_carregamento()
            
            total_registros = self._obter_total_registros()
            print(f"📊 Total de registros no site: {total_registros}")
            
            pagina_atual = 1
            
            while len(resultados) < max_resultados and pagina_atual <= max_paginas:
                print(f"\n📄 Página {pagina_atual} - coletados: {len(resultados)}")
                
                # Extrai resultados da página atual
                novos = self._extrair_resultados_pagina(urls_processadas)
                
                for r in novos:
                    if len(resultados) >= max_resultados:
                        break
                    url = r.get('url_processo', '')
                    if url and url not in urls_processadas:
                        urls_processadas.add(url)
                        resultados.append(r)
                        print(f"   ✓ {len(resultados)}: {r.get('numero_processo', 'N/A')} - {r.get('titulo', '')[:50]}...")
                
                # Navega para próxima página
                if len(resultados) < max_resultados and pagina_atual < max_paginas:
                    if not self._ir_proxima_pagina(pagina_atual):
                        print("   Não há mais páginas")
                        break
                    pagina_atual += 1
                    time.sleep(3)
                else:
                    break
            
            print(f"\n✅ Total: {len(resultados)} resultados válidos encontrados")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._fechar_driver()
        
        return resultados
    
    def _fechar_popup_cookies(self):
        """Fecha popup de cookies se existir"""
        try:
            seletores = [
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(text(), 'aceitar')]",
                "//a[contains(text(), 'Aceitar')]",
            ]
            for seletor in seletores:
                try:
                    botao = self.driver.find_element(By.XPATH, seletor)
                    if botao.is_displayed():
                        self.driver.execute_script("arguments[0].click();", botao)
                        print("   Fechou popup de cookies")
                        time.sleep(1)
                        return
                except:
                    continue
        except:
            pass
        
        try:
            self.driver.execute_script("""
                var cookieBars = document.querySelectorAll('[class*="cookie"], [id*="cookie"], .privacy-banner');
                cookieBars.forEach(function(el) { el.remove(); });
            """)
        except:
            pass
    
    def _obter_total_registros(self) -> int:
        """Obtém total de registros"""
        try:
            texto = self.driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r'(\d+)\s*registro', texto, re.IGNORECASE)
            if match:
                return int(match.group(1))
        except:
            pass
        return 0
    
    def _aguardar_carregamento(self):
        """Aguarda carregamento"""
        try:
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href, '/processos/')]")
            ))
        except:
            time.sleep(3)
    
    def _ir_proxima_pagina(self, pagina_atual: int) -> bool:
        """Navega para a próxima página"""
        try:
            proxima_pagina = pagina_atual + 1
            
            # Tenta clicar no número
            try:
                botao_num = self.driver.find_element(By.XPATH, 
                    f"//a[normalize-space(text())='{proxima_pagina}'] | //button[normalize-space(text())='{proxima_pagina}']"
                )
                if botao_num.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_num)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", botao_num)
                    print(f"   Clicou na página {proxima_pagina}")
                    time.sleep(2)
                    self._aguardar_carregamento()
                    return True
            except NoSuchElementException:
                pass
            
            # Tenta seta >
            try:
                seta = self.driver.find_element(By.XPATH, 
                    "//a[normalize-space(text())='>'] | //button[normalize-space(text())='>']"
                )
                if seta.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", seta)
                    print("   Clicou na seta >")
                    time.sleep(2)
                    self._aguardar_carregamento()
                    return True
            except NoSuchElementException:
                pass
            
            # Tenta via paginação
            try:
                paginacao = self.driver.find_element(By.CSS_SELECTOR, ".pagination-default")
                links = paginacao.find_elements(By.TAG_NAME, "a")
                for link in links:
                    texto = link.text.strip()
                    if texto == str(proxima_pagina) or texto == '>':
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", link)
                        print(f"   Navegou via paginação para: {texto}")
                        time.sleep(2)
                        self._aguardar_carregamento()
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"   Erro ao navegar: {e}")
            return False
    
    def _extrair_resultados_pagina(self, urls_ja_vistas: set) -> List[Dict]:
        """Extrai resultados da página atual, abrindo cada link para buscar detalhes extras"""
        resultados = []
        
        try:
            # Procura todos os cards de licitação
            items = self.driver.find_elements(By.CSS_SELECTOR, "div.item")
            print(f"   Encontrados {len(items)} cards 'div.item'")
            
            # Guarda a janela principal
            janela_principal = self.driver.current_window_handle
            
            for item in items:
                try:
                    links = item.find_elements(By.XPATH, ".//a[contains(@href, '/processos/')]")
                    if not links:
                        continue
                        
                    url = None
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/processos/' in href and 'processos?' not in href:
                            url = href
                            break
                    
                    if not url or url in urls_ja_vistas:
                        continue
                    
                    # Extração básica do card
                    texto_card = item.text
                    resultado = self._extrair_dados_item(texto_card, url)
                    
                    if not (resultado and self._e_licitacao_valida(resultado.get('titulo', ''), url)):
                        continue

                    # --- BUSCA PROFUNDA (Valor e Início Propostas) ---
                    # Abre em nova aba para não perder a posição na lista
                    self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                    time.sleep(1) # Pequena pausa para abrir
                    
                    janelas = self.driver.window_handles
                    self.driver.switch_to.window(janelas[-1])
                    
                    try:
                        # Espera carregar e extrai o corpo do texto
                        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        texto_profundo = self.driver.find_element(By.TAG_NAME, "body").text
                        
                        # Valor (Busca mais agressiva)
                        padroes_valor = [
                            r'Valor\s+(?:Estimado|Total|Global|Referência)[:\s]*R\$\s*([\d\.,]+)',
                            r'Valor[:\s]+R\$\s*([\d\.,]+)',
                            r'R\$\s*([\d\.,]+(?:[.,]\d{2})?)'
                        ]
                        for padrao in padroes_valor:
                            match_v = re.search(padrao, texto_profundo, re.IGNORECASE)
                            if match_v:
                                valor_str = match_v.group(1).strip().strip('.')
                                # Verifica se parece um valor real (tem vírgula ou é longo)
                                if ',' in valor_str or len(valor_str) > 5:
                                    resultado['valor_estimado'] = f"R$ {valor_str}"
                                    break
                        
                        # Datas (Novos campos)
                        regex_datas = {
                            'inicio_propostas': r'Início\s+das\s+Propostas[:\s]+([\d/\s:às]+)',
                            'limite_recebimento': r'Limite\s+p/\s+Recebimento[^<\n]*?[:\s]+([\d/\s:às]+)',
                            'abertura_propostas': r'Abertura\s+das\s+Propostas[:\s]+([\d/\s:às]+)',
                        }
                        
                        for campo, rgx in regex_datas.items():
                            match_d = re.search(rgx, texto_profundo, re.IGNORECASE)
                            if match_d:
                                resultado[campo] = match_d.group(1).strip()
                            else:
                                resultado[campo] = ""
                            
                    except Exception as e:
                        print(f"      ⚠️ Erro na busca profunda para {url}: {e}")
                    finally:
                        # Fecha a aba e volta para a principal
                        self.driver.close()
                        self.driver.switch_to.window(janela_principal)
                    
                    resultados.append(resultado)
                    print(f"      ✓ Coletado: {resultado.get('numero_processo', 'N/A')} - {resultado.get('valor_estimado') or 'Sem Valor'}")
                        
                except Exception as e:
                    print(f"      ⚠️ Erro ao processar item: {e}")
                    # Garante que volta para a janela principal em caso de erro
                    if len(self.driver.window_handles) > 1:
                        try: self.driver.close()
                        except: pass
                        self.driver.switch_to.window(janela_principal)
                    continue
                    
        except Exception as e:
            print(f"   Erro ao extrair resultados da página: {e}")
        
        return resultados
    
    def _extrair_dados_item(self, texto: str, url: str) -> Optional[Dict]:
        """Extrai dados estruturados do texto de um item"""
        resultado = {}
        
        linhas = [l.strip() for l in texto.split('\n') if l.strip()]
        
        # Número do processo - geralmente no formato XX/YYYY
        for linha in linhas:
            match = re.search(r'(\d{1,6}[/\-]\d{4})', linha)
            if match:
                resultado['numero_processo'] = match.group(1)
                break
        else:
            resultado['numero_processo'] = ""
        
        # Título - texto entre aspas ou primeira linha longa sem número de telefone
        titulo = ""
        for linha in linhas:
            # Tenta encontrar texto entre aspas (geralmente é o objeto)
            match_aspas = re.search(r'"([^"]{30,})"', linha)
            if match_aspas:
                titulo = match_aspas.group(1)
                break
        
        if not titulo:
            for linha in linhas:
                if (len(linha) > 40 
                    and not self._e_texto_de_banner(linha)
                    and not re.search(r'\d{4}[-\s]\d{4}', linha)  # Não é telefone
                    and 'ACESSAR' not in linha.upper()
                    and not linha.startswith('Recebe')):  # Não é "Recebendo propostas"
                    titulo = linha
                    break
        
        resultado['titulo'] = titulo
        resultado['objeto'] = titulo
        
        # Data
        match_data = re.search(r'(\d{2}/\d{2}/\d{4})\s*(?:às?\s*)?(\d{2}:\d{2})?', texto)
        if match_data:
            resultado['data_realizacao'] = f"{match_data.group(1)} {match_data.group(2) or ''}".strip()
        else:
            resultado['data_realizacao'] = ""
        
        # Modalidade
        texto_lower = texto.lower()
        modalidades = ['pregão eletrônico', 'pregão presencial', 'concorrência', 'dispensa', 
                      'registro de preços', 'tomada de preços', 'inexigibilidade']
        for m in modalidades:
            if m in texto_lower:
                resultado['modalidade'] = m.title()
                break
        else:
            resultado['modalidade'] = ""
        
        # Status
        status_map = [('recebendo propostas', 'Recebendo propostas'),
                      ('aguardando início', 'Aguardando Início'),
                      ('processo finalizado', 'Finalizado'),
                      ('em andamento', 'Em andamento'),
                      ('homologado', 'Homologado')]
        for termo, status in status_map:
            if termo in texto_lower:
                resultado['status'] = status
                break
        else:
            resultado['status'] = ""
        
        # Órgão - procura padrões comuns
        padroes_orgao = [
            r'Serviço\s+Autônomo[^\n,]{0,80}',
            r'Prefeitura\s+Municipal[^\n,]{0,80}',
            r'SAMAE[^\n,]{0,60}',
            r'SAAE[^\n,]{0,60}',
            r'Secretaria[^\n,]{0,80}',
            r'Câmara\s+Municipal[^\n,]{0,80}',
            r'Instituto[^\n,]{0,80}',
        ]
        for p in padroes_orgao:
            match = re.search(p, texto, re.IGNORECASE)
            if match:
                resultado['orgao'] = match.group().strip()[:150]
                break
        else:
            resultado['orgao'] = ""
        
        # UF
        match_uf = re.search(r'\s-\s([A-Z]{2})(?:\s|$|[,\.])', texto)
        resultado['uf'] = match_uf.group(1) if match_uf else ""
        resultado['municipio'] = ""
        resultado['url_processo'] = url
        
        # Valor
        # Procura por "R$ 1.234,56" ou "R$ 1234.56"
        # O valor geralmente vem após "Valor Estimado" ou similar no texto do card
        match_valor = re.search(r'R\$\s*([\d\.,]+)', texto)
        if match_valor:
            valor_str = match_valor.group(1).strip()
            # Garante que termina com dígito
            valor_str = re.sub(r'[\.,]$', '', valor_str)
            resultado['valor_estimado'] = f"R$ {valor_str}"
        else:
            # Tenta encontrar apenas o número se houver "Valor" por perto
            match_valor_num = re.search(r'(?:Valor|estimado|total)[:\s]*([\d\.,]+)', texto, re.IGNORECASE)
            if match_valor_num:
                valor_str = match_valor_num.group(1).strip()
                if len(valor_str) > 3 and ',' in valor_str:
                    resultado['valor_estimado'] = f"R$ {valor_str}"
                else:
                    resultado['valor_estimado'] = ""
            else:
                resultado['valor_estimado'] = ""
        
        return resultado


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO SCRAPER v6 - Filtros Rigorosos")
    print("=" * 60)
    
    scraper = PesquisaScraper(headless=False)
    resultados = scraper.pesquisar("esgoto", max_resultados=50, max_paginas=5)
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(resultados)} resultados")
    print('='*60)
    
    for i, r in enumerate(resultados, 1):
        print(f"\n{i}. {r.get('numero_processo', 'N/A')}")
        print(f"   Título: {r.get('titulo', 'N/A')[:70]}...")
        print(f"   Órgão: {r.get('orgao', 'N/A')}")
        print(f"   Status: {r.get('status', 'N/A')}")
