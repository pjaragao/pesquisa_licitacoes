from app.models.palavra_chave import PalavraChave
try:
    print("Tentando criar palavra...")
    p = PalavraChave.criar("esgoto")
    print("Palavra criada:", p.id)
except Exception as e:
    print("Erro esperado (unique constraint):", type(e))
    palavras = PalavraChave.listar_todas()
    print("Palavras ativas:", [p.termo for p in palavras])
