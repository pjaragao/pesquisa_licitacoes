import sys
from pathlib import Path

# Adiciona o diretório raiz
sys.path.insert(0, str(Path(__file__).parent))

from app.models.historico_pesquisa import HistoricoPesquisa

# Criando um de teste
h = HistoricoPesquisa.criar(["saneamento"], ["SP", "RJ"])
print("ID Criado:", h.id)
h.log("Teste de conexao bem sucedido!")
h.atualizar_progresso(50, "SP (1/2)")
h.set_status('concluido')

historicos = HistoricoPesquisa.listar_recentes(5)
print("Recentes no DB:", len(historicos))
for x in historicos:
    print(f"[{x.id}] Status: {x.status} | Logs: {len(x.logs_auditoria)}")
