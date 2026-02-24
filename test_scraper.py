"""
Teste do scraper v5
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.scrapers.pesquisa_scraper import PesquisaScraper

print("=" * 60)
print("TESTE DO SCRAPER v5 - Paginação Numérica")
print("=" * 60)

scraper = PesquisaScraper(headless=False)
resultados = scraper.pesquisar("esgoto", max_resultados=50, max_paginas=5)

print(f"\n{'='*60}")
print(f"TOTAL: {len(resultados)} resultados")
print('='*60)

for i, r in enumerate(resultados, 1):
    print(f"\n{i}. {r.get('numero_processo', 'N/A')}")
    print(f"   {r.get('titulo', 'N/A')[:60]}...")
    print(f"   Órgão: {r.get('orgao', 'N/A')}")
    print(f"   Status: {r.get('status', 'N/A')}")
