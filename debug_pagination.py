"""
Script de debug para analisar a paginação do portal
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Configura driver
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    url = "https://www.portaldecompraspublicas.com.br/processos?objeto=esgoto"
    print(f"Acessando: {url}")
    driver.get(url)
    
    # Aguarda carregamento
    time.sleep(8)
    
    # Salva HTML para análise
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("HTML salvo em debug_page.html")
    
    # Conta elementos importantes
    print("\n=== ANÁLISE DA PÁGINA ===")
    
    # Links de processos
    links = driver.find_elements(By.XPATH, "//a[contains(@href, '/processos/')]")
    print(f"Links /processos/: {len(links)}")
    
    # Botões ACESSAR
    botoes = driver.find_elements(By.XPATH, "//*[contains(text(), 'ACESSAR')]")
    print(f"Botões ACESSAR: {len(botoes)}")
    
    # Elementos de paginação
    paginacao = driver.find_elements(By.CSS_SELECTOR, ".pagination, [class*='paginat'], [class*='page'], nav")
    print(f"Elementos paginação: {len(paginacao)}")
    for p in paginacao[:5]:
        print(f"  - {p.tag_name}.{p.get_attribute('class')}")
    
    # Botões numerados
    numeros = driver.find_elements(By.XPATH, "//button[contains(@class, 'page')] | //a[contains(@class, 'page')]")
    print(f"Botões de página: {len(numeros)}")
    for n in numeros[:10]:
        print(f"  - {n.text}")
    
    # Procura por qualquer número de página ou navegação
    navs = driver.find_elements(By.XPATH, "//*[contains(@class, 'pagination') or contains(@class, 'pager')]")
    print(f"Navegação encontrada: {len(navs)}")
    
    # Total de registros - procura texto
    texto_body = driver.find_element(By.TAG_NAME, "body").text
    import re
    match = re.search(r'(\d+)\s*registro', texto_body, re.IGNORECASE)
    if match:
        print(f"Total registros: {match.group(1)}")
    
    match = re.search(r'Página\s*(\d+)\s*de\s*(\d+)', texto_body, re.IGNORECASE)
    if match:
        print(f"Paginação: Página {match.group(1)} de {match.group(2)}")
    
    # Procura por ">" ou "Próxima"
    proxima = driver.find_elements(By.XPATH, "//button[contains(text(), '>') or contains(text(), 'Próxima') or contains(text(), 'próxima')]")
    print(f"Botões próxima: {len(proxima)}")
    
    print("\n=== TESTANDO SCROLL ===")
    
    # Conta links antes do scroll
    links_antes = len(driver.find_elements(By.XPATH, "//a[contains(@href, '/processos/')]"))
    print(f"Links antes do scroll: {links_antes}")
    
    # Faz scroll
    for i in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        links_depois = len(driver.find_elements(By.XPATH, "//a[contains(@href, '/processos/')]"))
        print(f"Scroll {i+1}: {links_depois} links")
    
    print("\n=== PROCURANDO PAGINAÇÃO MANUAL ===")
    
    # Procura todos os botões
    all_buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"Total de botões: {len(all_buttons)}")
    for btn in all_buttons:
        txt = btn.text.strip()
        if txt and len(txt) < 20:
            print(f"  Botão: '{txt}'")
    
    # Procura nav com números
    page_nums = driver.find_elements(By.XPATH, "//*[text()='1'] | //*[text()='2'] | //*[text()='3']")
    print(f"Elementos com números 1,2,3: {len(page_nums)}")
    
    # Screenshot final (se possível)
    driver.save_screenshot("debug_screenshot.png")
    print("Screenshot salvo em debug_screenshot.png")
    
finally:
    driver.quit()
    print("\nDriver fechado")
