"""
Model: Oportunidade (após detalhamento completo)
"""
from datetime import datetime
from app import get_db


class Oportunidade:
    """Classe para gerenciar oportunidades de licitação"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.codigo = kwargs.get('codigo')
        self.resultado_id = kwargs.get('resultado_id')
        
        # Dados básicos
        self.numero_processo = kwargs.get('numero_processo')
        self.titulo = kwargs.get('titulo')
        self.objeto = kwargs.get('objeto')
        
        # Órgão/Local
        self.orgao = kwargs.get('orgao')
        self.uf = kwargs.get('uf')
        self.municipio = kwargs.get('municipio')
        
        # Tipo/Modalidade
        self.tipo = kwargs.get('tipo')
        self.modalidade = kwargs.get('modalidade')
        self.tratamento_fase_lances = kwargs.get('tratamento_fase_lances')
        self.operacao = kwargs.get('operacao')
        self.modo_disputa = kwargs.get('modo_disputa')
        
        # Pessoas envolvidas
        self.pregoeiro = kwargs.get('pregoeiro')
        self.autoridade_competente = kwargs.get('autoridade_competente')
        self.apoio = kwargs.get('apoio')
        
        # Recursos e Legislação
        self.origem_recursos = kwargs.get('origem_recursos')
        self.legislacao_aplicavel = kwargs.get('legislacao_aplicavel')
        
        # Datas importantes
        self.data_publicacao = kwargs.get('data_publicacao')
        self.inicio_propostas = kwargs.get('inicio_propostas')
        self.limite_impugnacoes = kwargs.get('limite_impugnacoes')
        self.limite_esclarecimentos = kwargs.get('limite_esclarecimentos')
        self.limite_recebimento_propostas = kwargs.get('limite_recebimento_propostas')
        self.abertura_propostas = kwargs.get('abertura_propostas')
        
        # Status
        self.status = kwargs.get('status')
        
        # URL e Valor
        self.url_processo = kwargs.get('url_processo')
        self.valor_estimado = kwargs.get('valor_estimado')
        
        # Documentos
        self.pasta_local = kwargs.get('pasta_local')
        self.pasta_google_drive = kwargs.get('pasta_google_drive')
        
        # Análise
        self.analisado_ia = kwargs.get('analisado_ia', False)
        self.resultado_analise = kwargs.get('resultado_analise')
        
        # Timestamps
        self.criado_em = kwargs.get('criado_em')
        self.atualizado_em = kwargs.get('atualizado_em')
    
    @staticmethod
    def gerar_codigo() -> str:
        """
        Gera código no formato OPXXYYY
        XX = Ano (2 dígitos, ex: 26 para 2026)
        YYY = Número sequencial (001, 002, ...)
        """
        ano_atual = datetime.now().strftime('%y')
        
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT codigo FROM oportunidades WHERE codigo LIKE ? ORDER BY codigo DESC LIMIT 1",
                (f"OP{ano_atual}%",)
            )
            row = cursor.fetchone()
            
            if row:
                ultimo_numero = int(row['codigo'][4:])  # Pega os 3 últimos dígitos
                numero = ultimo_numero + 1
            else:
                numero = 1
            
            return f"OP{ano_atual}{numero:03d}"
    
    @staticmethod
    def criar(dados: dict) -> 'Oportunidade':
        """Cria uma nova oportunidade"""
        codigo = Oportunidade.gerar_codigo()
        
        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO oportunidades 
                (codigo, resultado_id, numero_processo, titulo, objeto, orgao, uf, municipio,
                 tipo, modalidade, tratamento_fase_lances, operacao, modo_disputa,
                 pregoeiro, autoridade_competente, apoio, origem_recursos, legislacao_aplicavel,
                 data_publicacao, inicio_propostas, limite_impugnacoes, limite_esclarecimentos,
                 limite_recebimento_propostas, abertura_propostas, status, pasta_local, url_processo, valor_estimado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                codigo,
                dados.get('resultado_id'),
                dados.get('numero_processo'),
                dados.get('titulo'),
                dados.get('objeto'),
                dados.get('orgao'),
                dados.get('uf'),
                dados.get('municipio'),
                dados.get('tipo'),
                dados.get('modalidade'),
                dados.get('tratamento_fase_lances'),
                dados.get('operacao'),
                dados.get('modo_disputa'),
                dados.get('pregoeiro'),
                dados.get('autoridade_competente'),
                dados.get('apoio'),
                dados.get('origem_recursos'),
                dados.get('legislacao_aplicavel'),
                dados.get('data_publicacao'),
                dados.get('inicio_propostas'),
                dados.get('limite_impugnacoes'),
                dados.get('limite_esclarecimentos'),
                dados.get('limite_recebimento_propostas'),
                dados.get('abertura_propostas'),
                dados.get('status'),
                dados.get('pasta_local'),
                dados.get('url_processo'),
                dados.get('valor_estimado')
            ))
            
            return Oportunidade(id=cursor.lastrowid, codigo=codigo, **dados)
    
    @staticmethod
    def listar_todas() -> list:
        """Lista todas as oportunidades"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM oportunidades ORDER BY criado_em DESC"
            )
            return [Oportunidade._from_row(row) for row in cursor.fetchall()]
    
    @staticmethod
    def buscar_por_id(id: int) -> 'Oportunidade':
        """Busca oportunidade por ID"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM oportunidades WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            return Oportunidade._from_row(row) if row else None
    
    @staticmethod
    def buscar_por_codigo(codigo: str) -> 'Oportunidade':
        """Busca oportunidade por código"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM oportunidades WHERE codigo = ?", (codigo,)
            )
            row = cursor.fetchone()
            return Oportunidade._from_row(row) if row else None
            
    @staticmethod
    def buscar_por_resultado_id(resultado_id: int) -> 'Oportunidade':
        """Busca oportunidade por ID do resultado original"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM oportunidades WHERE resultado_id = ?", (resultado_id,)
            )
            row = cursor.fetchone()
            return Oportunidade._from_row(row) if row else None
    
    def deletar(self):
        """Deleta a oportunidade do banco"""
        with get_db() as conn:
            conn.execute("DELETE FROM oportunidades WHERE id = ?", (self.id,))
    
    @staticmethod
    def limpar_todas():
        """Remove todas as oportunidades"""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM oportunidades")
            total = cursor.fetchone()['total']
            conn.execute("DELETE FROM oportunidades")
            return total
    
    def atualizar_pasta_drive(self, url: str):
        """Atualiza a URL da pasta no Google Drive"""
        with get_db() as conn:
            conn.execute(
                "UPDATE oportunidades SET pasta_google_drive = ?, atualizado_em = ? WHERE id = ?",
                (url, datetime.now().isoformat(), self.id)
            )
            self.pasta_google_drive = url
    
    @staticmethod
    def _from_row(row) -> 'Oportunidade':
        """Converte uma linha do banco para objeto Oportunidade"""
        if not row:
            return None
        return Oportunidade(**dict(row))
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'codigo': self.codigo,
            'resultado_id': self.resultado_id,
            'numero_processo': self.numero_processo,
            'titulo': self.titulo,
            'objeto': self.objeto,
            'orgao': self.orgao,
            'uf': self.uf,
            'municipio': self.municipio,
            'tipo': self.tipo,
            'modalidade': self.modalidade,
            'tratamento_fase_lances': self.tratamento_fase_lances,
            'operacao': self.operacao,
            'modo_disputa': self.modo_disputa,
            'pregoeiro': self.pregoeiro,
            'autoridade_competente': self.autoridade_competente,
            'apoio': self.apoio,
            'origem_recursos': self.origem_recursos,
            'legislacao_aplicavel': self.legislacao_aplicavel,
            'data_publicacao': self.data_publicacao,
            'inicio_propostas': self.inicio_propostas,
            'limite_impugnacoes': self.limite_impugnacoes,
            'limite_esclarecimentos': self.limite_esclarecimentos,
            'limite_recebimento_propostas': self.limite_recebimento_propostas,
            'abertura_propostas': self.abertura_propostas,
            'status': self.status,
            'url_processo': self.url_processo,
            'valor_estimado': self.valor_estimado,
            'pasta_local': self.pasta_local,
            'pasta_google_drive': self.pasta_google_drive,
            'analisado_ia': self.analisado_ia,
            'resultado_analise': self.resultado_analise,
            'criado_em': str(self.criado_em) if self.criado_em else None,
            'atualizado_em': str(self.atualizado_em) if self.atualizado_em else None
        }

    # ==================== MÉTODOS DE CACHE LOCAL ====================

    def salvar_itens_cache(self, itens: list):
        """Salva a lista de itens no cache local"""
        with get_db() as conn:
            conn.execute("DELETE FROM oportunidade_itens WHERE oportunidade_id = ?", (self.id,))
            for i in itens:
                conn.execute('''
                    INSERT INTO oportunidade_itens 
                    (oportunidade_id, numero_item, descricao, quantidade, unidade_medida, valor_unitario_estimado, valor_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.id,
                    i.get('numeroItem'),
                    i.get('descricao') or i.get('materialOuServicoNome'),
                    i.get('quantidade'),
                    i.get('unidadeMedida'),
                    i.get('valorUnitarioEstimado'),
                    i.get('valorTotal')
                ))

    def salvar_arquivos_cache(self, arquivos: list):
        """Salva a lista de arquivos no cache local"""
        with get_db() as conn:
            conn.execute("DELETE FROM oportunidade_arquivos WHERE oportunidade_id = ?", (self.id,))
            for a in arquivos:
                conn.execute('''
                    INSERT INTO oportunidade_arquivos 
                    (oportunidade_id, titulo, url, tipo_documento, data_publicacao)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    self.id,
                    a.get('titulo') or a.get('tituloArquivo') or a.get('nomeArquivo'),
                    a.get('url') or a.get('linkArquivo') or a.get('href'),
                    a.get('tipoDocumentoNome'),
                    a.get('dataPublicacaoPncp')
                ))

    def salvar_historico_cache(self, historico: list):
        """Salva a lista de histórico no cache local"""
        with get_db() as conn:
            conn.execute("DELETE FROM oportunidade_historico WHERE oportunidade_id = ?", (self.id,))
            for h in historico:
                conn.execute('''
                    INSERT INTO oportunidade_historico 
                    (oportunidade_id, situacao, categoria, nome_arquivo, data_hora, observacao, usuario)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.id,
                    h.get('tipoLogManutencaoNome') or h.get('nomeSituacaoCompra') or h.get('status') or h.get('situacaoNome') or 'Inclusão',
                    h.get('categoriaLogManutencaoNome') or h.get('categoriaNome') or h.get('tipoLogManutencaoItemNome'),
                    h.get('documentoTitulo') or h.get('nomeArquivo') or h.get('arquivoNome') or h.get('documentoNome') or h.get('nomeDocumento'),
                    h.get('logManutencaoDataInclusao') or h.get('dataHoraRegistro') or h.get('dataHoraAcao') or h.get('dataInclusao') or h.get('dataPublicacaoPncp'),
                    h.get('justificativa') or h.get('justificativaJustificativa') or h.get('motivo') or h.get('observacao') or h.get('descricaoJustificativa') or h.get('informacaoComplementar') or h.get('itemJustificativa'),
                    h.get('usuarioNome') or h.get('logManutencaoUsuarioNome') or h.get('usuarioResponsavel') or h.get('nomeUsuario')
                ))

    def obter_itens_cache(self) -> list:
        """Obtém itens do cache local"""
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM oportunidade_itens WHERE oportunidade_id = ? ORDER BY numero_item", (self.id,))
            return [dict(row) for row in cursor.fetchall()]

    def obter_arquivos_cache(self) -> list:
        """Obtém arquivos do cache local"""
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM oportunidade_arquivos WHERE oportunidade_id = ? ORDER BY id", (self.id,))
            return [dict(row) for row in cursor.fetchall()]

    def obter_historico_cache(self) -> list:
        """Obtém histórico do cache local"""
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM oportunidade_historico WHERE oportunidade_id = ? ORDER BY data_hora DESC", (self.id,))
            return [dict(row) for row in cursor.fetchall()]
