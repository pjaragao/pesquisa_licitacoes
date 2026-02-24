"""
Model: Configuração da Empresa
Gerencia o prompt que descreve o ramo de atividade da empresa
"""
from datetime import datetime
from app import get_db


class ConfiguracaoEmpresa:
    """Classe para gerenciar a configuração do prompt da empresa"""
    
    def __init__(self, id=None, prompt_empresa=None, criado_em=None, atualizado_em=None):
        self.id = id
        self.prompt_empresa = prompt_empresa
        self.criado_em = criado_em
        self.atualizado_em = atualizado_em
    
    @staticmethod
    def obter():
        """Obtém a configuração atual (sempre retorna a primeira/única)"""
        with get_db() as db:
            row = db.execute(
                'SELECT * FROM configuracao_empresa ORDER BY id LIMIT 1'
            ).fetchone()
            
            if row:
                return ConfiguracaoEmpresa._from_row(row)
            return None
    
    @staticmethod
    def salvar(prompt_empresa: str):
        """Salva ou atualiza a configuração"""
        with get_db() as db:
            # Verifica se já existe uma configuração
            existente = db.execute(
                'SELECT id FROM configuracao_empresa ORDER BY id LIMIT 1'
            ).fetchone()
            
            if existente:
                # Atualiza existente
                db.execute('''
                    UPDATE configuracao_empresa 
                    SET prompt_empresa = ?, atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (prompt_empresa, existente['id']))
            else:
                # Cria nova
                db.execute('''
                    INSERT INTO configuracao_empresa (prompt_empresa)
                    VALUES (?)
                ''', (prompt_empresa,))
            
            db.commit()
        
        return ConfiguracaoEmpresa.obter()
    
    @staticmethod
    def _from_row(row):
        """Converte uma linha do banco para objeto ConfiguracaoEmpresa"""
        if not row:
            return None
        return ConfiguracaoEmpresa(
            id=row['id'],
            prompt_empresa=row['prompt_empresa'],
            criado_em=row['criado_em'],
            atualizado_em=row['atualizado_em']
        )
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'prompt_empresa': self.prompt_empresa,
            'criado_em': self.criado_em,
            'atualizado_em': self.atualizado_em
        }
