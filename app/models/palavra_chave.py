"""
Model: Palavra-Chave para pesquisa de licitações
"""
from datetime import datetime
from app import get_db


class PalavraChave:
    """Classe para gerenciar palavras-chave de pesquisa"""
    
    def __init__(self, id=None, termo=None, ativo=True, criado_em=None, ultima_pesquisa=None):
        self.id = id
        self.termo = termo
        self.ativo = ativo
        self.criado_em = criado_em or datetime.now()
        self.ultima_pesquisa = ultima_pesquisa
    
    @staticmethod
    def criar(termo: str) -> 'PalavraChave':
        """Cria uma nova palavra-chave"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO palavras_chave (termo) VALUES (?)",
                (termo.strip(),)
            )
            return PalavraChave(id=cursor.lastrowid, termo=termo.strip())
    
    @staticmethod
    def listar_todas(apenas_ativas: bool = True) -> list:
        """Lista todas as palavras-chave"""
        with get_db() as conn:
            if apenas_ativas:
                cursor = conn.execute(
                    "SELECT * FROM palavras_chave WHERE ativo = 1 ORDER BY termo"
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM palavras_chave ORDER BY termo"
                )
            return [PalavraChave._from_row(row) for row in cursor.fetchall()]
    
    @staticmethod
    def buscar_por_id(id: int) -> 'PalavraChave':
        """Busca palavra-chave por ID"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM palavras_chave WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            return PalavraChave._from_row(row) if row else None
    
    def atualizar_ultima_pesquisa(self):
        """Atualiza a data da última pesquisa"""
        with get_db() as conn:
            conn.execute(
                "UPDATE palavras_chave SET ultima_pesquisa = ? WHERE id = ?",
                (datetime.now().isoformat(), self.id)
            )
            self.ultima_pesquisa = datetime.now()
    
    def desativar(self):
        """Desativa a palavra-chave"""
        with get_db() as conn:
            conn.execute(
                "UPDATE palavras_chave SET ativo = 0 WHERE id = ?", (self.id,)
            )
            self.ativo = False
    
    def deletar(self):
        """Remove a palavra-chave do banco"""
        with get_db() as conn:
            conn.execute(
                "DELETE FROM palavras_chave WHERE id = ?", (self.id,)
            )
    
    @staticmethod
    def _from_row(row) -> 'PalavraChave':
        """Converte uma linha do banco para objeto PalavraChave"""
        if not row:
            return None
        return PalavraChave(
            id=row['id'],
            termo=row['termo'],
            ativo=bool(row['ativo']),
            criado_em=row['criado_em'],
            ultima_pesquisa=row['ultima_pesquisa']
        )
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'termo': self.termo,
            'ativo': self.ativo,
            'criado_em': str(self.criado_em) if self.criado_em else None,
            'ultima_pesquisa': str(self.ultima_pesquisa) if self.ultima_pesquisa else None
        }
