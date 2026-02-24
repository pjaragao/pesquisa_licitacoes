"""
Analisa o que foi salvo no banco e o HTML capturado
"""
import sqlite3

conn = sqlite3.connect('database/licitacoes.db')
conn.row_factory = sqlite3.Row

print("=" * 70)
print("RESULTADOS NO BANCO DE DADOS")
print("=" * 70)

cur = conn.execute('SELECT numero_processo, titulo, orgao, url_processo FROM pesquisa_resultados')
for r in cur.fetchall():
    print(f"\nProcesso: {r['numero_processo']}")
    print(f"Título: {r['titulo'][:80]}...")
    print(f"Órgão: {r['orgao']}")
    print(f"URL: {r['url_processo'][:70] if r['url_processo'] else 'N/A'}...")

conn.close()

# Analisa o HTML salvo
print("\n" + "=" * 70)
print("ANÁLISE DO HTML SALVO (debug_page.html)")
print("=" * 70)

try:
    from bs4 import BeautifulSoup
    import re
    
    with open('debug_page.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Procura todos os links de processos
    links = soup.find_all('a', href=re.compile(r'/processos/'))
    print(f"\nTotal de links /processos/: {len(links)}")
    
    # Veja os primeiros 5
    for i, link in enumerate(links[:10]):
        href = link.get('href', '')
        texto = link.get_text(strip=True)[:50]
        print(f"  {i+1}. {href[:60]} -> '{texto}'")
    
    # Procura elementos com "ACESSAR PROCESSO"
    acessar = soup.find_all(string=re.compile(r'ACESSAR\s*PROCESSO', re.IGNORECASE))
    print(f"\nElementos com 'ACESSAR PROCESSO': {len(acessar)}")
    
    # Procura por cards/divs que parecem licitações
    cards = soup.find_all('div', class_=re.compile(r'card|processo|item', re.IGNORECASE))
    print(f"Divs com class card/processo/item: {len(cards)}")
    
    # Procura texto "Receba alertas" para identificar banners
    alertas = soup.find_all(string=re.compile(r'Receba alertas', re.IGNORECASE))
    print(f"\nTextos 'Receba alertas' (banners): {len(alertas)}")
    
    # Mostra estrutura de um card real se existir
    print("\n--- ESTRUTURA DE UM CARD REAL (se existir) ---")
    for card in cards[:3]:
        card_text = card.get_text(separator=' | ', strip=True)[:200]
        print(f"Card: {card_text}...")
        print()
        
except FileNotFoundError:
    print("Arquivo debug_page.html não encontrado")
except Exception as e:
    print(f"Erro: {e}")
