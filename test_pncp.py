"""Teste de persistência dos novos campos da API PNCP"""
import sys
sys.path.insert(0, '.')

from app.services.pncp_search_service import PncpSearchService
from app.models.resultado_pesquisa import ResultadoPesquisa

print("=" * 60)
print("TESTE DE PERSISTÊNCIA - NOVOS CAMPOS API PNCP")
print("=" * 60)

service = PncpSearchService()

# Busca 2 licitações de saneamento em SP
print("\n🔍 Buscando licitações com 'saneamento' em SP...")
resultados = service.pesquisar(
    termos=['saneamento'],
    ufs=['SP'],
    max_resultados=2,
    palavra_chave_id=1  # Assumindo que existe palavra-chave com ID 1
)

print(f"\n📊 Encontrados: {len(resultados)} resultados")

if resultados:
    r = resultados[0]
    print("\n" + "=" * 60)
    print("CAMPOS DO PRIMEIRO RESULTADO:")
    print("=" * 60)
    
    campos_novos = [
        'numero_controle_pncp', 'processo', 'valor_estimado_numerico',
        'valor_homologado', 'cnpj_orgao', 'codigo_ibge', 'modalidade_id',
        'modo_disputa', 'srp', 'amparo_legal', 'data_publicacao_pncp',
        'informacao_complementar', 'link_processo_eletronico', 'data_atualizacao_api'
    ]
    
    print(f"\n📋 Campos Originais:")
    print(f"   numero_processo: {r.get('numero_processo')}")
    print(f"   titulo: {r.get('titulo', '')[:60]}...")
    print(f"   valor_estimado: {r.get('valor_estimado')}")
    print(f"   modalidade: {r.get('modalidade')}")
    print(f"   status: {r.get('status')}")
    
    print(f"\n✨ Novos Campos API PNCP:")
    for campo in campos_novos:
        valor = r.get(campo)
        if valor is not None and valor != "":
            print(f"   {campo}: {valor}")
        else:
            print(f"   {campo}: (vazio)")
    
    # Tenta salvar no banco
    print("\n" + "=" * 60)
    print("SALVANDO NO BANCO...")
    print("=" * 60)
    
    resultado_db = ResultadoPesquisa.criar(r)
    if resultado_db:
        print(f"✅ Resultado salvo com ID: {resultado_db.id}")
        print(f"   valor_estimado_numerico: {resultado_db.valor_estimado_numerico}")
        print(f"   cnpj_orgao: {resultado_db.cnpj_orgao}")
        print(f"   modo_disputa: {resultado_db.modo_disputa}")
    else:
        print("⏭️  Resultado já existia no banco (duplicata)")
