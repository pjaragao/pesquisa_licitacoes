"""Script para descobrir todos os campos da API PNCP"""
import sys
import json
sys.path.insert(0, '.')

from app.services.pncp_api_client import PncpApiClient

client = PncpApiClient()

# Busca um item para ver a estrutura
res = client.buscar_contratacoes_propostas_abertas(uf='SP', tamanho_pagina=1)

items = res.get('data', [])
if items:
    item = items[0]
    print("=" * 60)
    print("ESTRUTURA COMPLETA DE UM ITEM DA API")
    print("=" * 60)
    print(json.dumps(item, indent=2, ensure_ascii=False, default=str))
    
    print("\n\n" + "=" * 60)
    print("CAMPOS DISPONÍVEIS:")
    print("=" * 60)
    
    def listar_campos(obj, prefixo=""):
        for key, value in obj.items():
            if isinstance(value, dict):
                print(f"{prefixo}{key}: (objeto)")
                listar_campos(value, prefixo + "  ")
            else:
                tipo = type(value).__name__
                print(f"{prefixo}{key}: {tipo}")
    
    listar_campos(item)
else:
    print("Nenhum item retornado")
