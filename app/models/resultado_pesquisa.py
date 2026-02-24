"""
Model: Resultado de Pesquisa (resumido)
Expandido com campos da API PNCP
"""
from datetime import datetime
from app import get_db


class ResultadoPesquisa:
    """Classe para gerenciar resultados de pesquisa"""
    
    def __init__(self, id=None, palavra_chave_id=None, numero_processo=None,
                 titulo=None, objeto=None, orgao=None, uf=None, municipio=None,
                 modalidade=None, status=None, data_realizacao=None,
                 url_processo=None, valor_estimado=None, inicio_propostas=None,
                 limite_recebimento=None, abertura_propostas=None,
                 selecionado_detalhe=False, criado_em=None,
                 classificacao_ia=None, explicacao_ia=None, classificado_em=None,
                 # Novos campos API PNCP
                 numero_controle_pncp=None, processo=None, valor_estimado_numerico=None,
                 valor_homologado=None, cnpj_orgao=None, codigo_ibge=None,
                 modalidade_id=None, modo_disputa=None, srp=False,
                 amparo_legal=None, data_publicacao_pncp=None,
                 informacao_complementar=None,                 link_processo_eletronico=None,
                 data_atualizacao_api=None,
                 atualizado_em=None):
        self.id = id
        self.palavra_chave_id = palavra_chave_id
        self.numero_processo = numero_processo
        self.titulo = titulo
        self.objeto = objeto
        self.orgao = orgao
        self.uf = uf
        self.municipio = municipio
        self.modalidade = modalidade
        self.status = status
        self.data_realizacao = data_realizacao
        self.url_processo = url_processo
        self.valor_estimado = valor_estimado
        self.inicio_propostas = inicio_propostas
        self.limite_recebimento = limite_recebimento
        self.abertura_propostas = abertura_propostas
        self.selecionado_detalhe = selecionado_detalhe
        self.criado_em = criado_em or datetime.now()
        # Campos de classificação IA
        self.classificacao_ia = classificacao_ia
        self.explicacao_ia = explicacao_ia
        self.classificado_em = classificado_em
        # Novos campos API PNCP
        self.numero_controle_pncp = numero_controle_pncp
        self.processo = processo
        self.valor_estimado_numerico = valor_estimado_numerico
        self.valor_homologado = valor_homologado
        self.cnpj_orgao = cnpj_orgao
        self.codigo_ibge = codigo_ibge
        self.modalidade_id = modalidade_id
        self.modo_disputa = modo_disputa
        self.srp = srp
        self.amparo_legal = amparo_legal
        self.data_publicacao_pncp = data_publicacao_pncp
        self.informacao_complementar = informacao_complementar
        self.link_processo_eletronico = link_processo_eletronico
        self.data_atualizacao_api = data_atualizacao_api
        self.atualizado_em = atualizado_em
    
    @staticmethod
    def criar(dados: dict) -> 'ResultadoPesquisa':
        """Cria um novo resultado de pesquisa (ou ignora se já existir)"""
        with get_db() as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO pesquisa_resultados 
                    (palavra_chave_id, numero_processo, titulo, objeto, orgao, 
                     uf, municipio, modalidade, status, data_realizacao, 
                     url_processo, valor_estimado, inicio_propostas, 
                     limite_recebimento, abertura_propostas,
                     numero_controle_pncp, processo, valor_estimado_numerico,
                     valor_homologado, cnpj_orgao, codigo_ibge, modalidade_id,
                     modo_disputa, srp, amparo_legal, data_publicacao_pncp,
                     informacao_complementar, link_processo_eletronico, data_atualizacao_api)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dados.get('palavra_chave_id'),
                    dados.get('numero_processo'),
                    dados.get('titulo'),
                    dados.get('objeto'),
                    dados.get('orgao'),
                    dados.get('uf'),
                    dados.get('municipio'),
                    dados.get('modalidade'),
                    dados.get('status'),
                    dados.get('data_realizacao'),
                    dados.get('url_processo'),
                    dados.get('valor_estimado'),
                    dados.get('inicio_propostas'),
                    dados.get('limite_recebimento'),
                    dados.get('abertura_propostas'),
                    # Novos campos
                    dados.get('numero_controle_pncp'),
                    dados.get('processo'),
                    dados.get('valor_estimado_numerico'),
                    dados.get('valor_homologado'),
                    dados.get('cnpj_orgao'),
                    dados.get('codigo_ibge'),
                    dados.get('modalidade_id'),
                    dados.get('modo_disputa'),
                    1 if dados.get('srp') else 0,
                    dados.get('amparo_legal'),
                    dados.get('data_publicacao_pncp'),
                    dados.get('informacao_complementar'),
                    dados.get('link_processo_eletronico'),
                    dados.get('data_atualizacao_api')
                ))
                return ResultadoPesquisa(id=cursor.lastrowid, **dados)
            except Exception as e:
                # Provavelmente registro duplicado (UNIQUE constraint)
                if "UNIQUE constraint" in str(e):
                    return None
                raise
    
    @staticmethod
    def listar_por_palavra_chave(palavra_chave_id: int) -> list:
        """Lista resultados de uma palavra-chave específica"""
        with get_db() as conn:
            cursor = conn.execute(
                """SELECT * FROM pesquisa_resultados 
                   WHERE palavra_chave_id = ? 
                   ORDER BY criado_em DESC""",
                (palavra_chave_id,)
            )
            return [ResultadoPesquisa._from_row(row) for row in cursor.fetchall()]
    
    @staticmethod
    def listar_todos(filtro_status: str = None, apenas_nao_selecionados: bool = False, 
                     valor_min: float = None, valor_max: float = None, 
                     data_de: str = None, data_ate: str = None, ufs: list = None,
                     ordenar_por: str = 'criado_em', direcao: str = 'desc',
                     classificacao_ia: str = None) -> list:
        """Lista todos os resultados com filtros opcionais avançados e ordenação"""
        with get_db() as conn:
            query = "SELECT * FROM pesquisa_resultados WHERE 1=1"
            params = []
            
            if filtro_status:
                query += " AND status = ?"
                params.append(filtro_status)
            
            if apenas_nao_selecionados:
                query += " AND selecionado_detalhe = 0"
            
            if ufs:
                placeholders = ', '.join(['?'] * len(ufs))
                query += f" AND uf IN ({placeholders})"
                params.extend(ufs)
            
            # Filtro de classificação IA
            if classificacao_ia:
                if classificacao_ia == 'NAO_CLASSIFICADO':
                    query += " AND classificacao_ia IS NULL"
                else:
                    query += " AND classificacao_ia = ?"
                    params.append(classificacao_ia)
            
            # Ordenação inicial via SQL apenas para criado_em
            if ordenar_por == 'criado_em':
                query += f" ORDER BY criado_em {direcao.upper()}"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            resultados = [ResultadoPesquisa._from_row(row) for row in rows]
            
            # Filtros que exigem processamento de string (Python-side filtering)
            if valor_min is not None or valor_max is not None or data_de or data_ate:
                filtered = []
                for r in resultados:
                    keep = True
                    
                    # Filtro de Valor
                    if valor_min is not None or valor_max is not None:
                        val = r.get_valor_numerico()
                        if val is not None:
                            if valor_min is not None and val < valor_min:
                                keep = False
                            if valor_max is not None and val > valor_max:
                                keep = False
                        elif valor_min is not None: 
                             keep = False
                    
                    # Filtro de Data (Abertura Propostas)
                    if keep and (data_de or data_ate):
                        dt_abertura = r.get_data_abertura_objeto()
                        if not dt_abertura:
                            keep = False
                        else:
                            try:
                                if data_de:
                                    limite_de = datetime.strptime(data_de, '%Y-%m-%d')
                                    if dt_abertura < limite_de:
                                        keep = False
                                if keep and data_ate:
                                    limite_ate = datetime.strptime(data_ate, '%Y-%m-%d')
                                    if dt_abertura > limite_ate:
                                        keep = False
                            except:
                                pass
                            
                    if keep:
                        filtered.append(r)
                resultados = filtered

            # Ordenação avançada (Python-side sorting)
            if ordenar_por in ['valor', 'data']:
                reverse = (direcao.lower() == 'desc')
                
                if ordenar_por == 'valor':
                    resultados.sort(key=lambda x: x.get_valor_numerico() or 0, reverse=reverse)
                elif ordenar_por == 'data':
                    # Para datas vazias, colocamos no final
                    resultados.sort(key=lambda x: x.get_data_abertura_objeto() or datetime(1900, 1, 1), reverse=reverse)
                
            return resultados

    def get_valor_numerico(self) -> float:
        """Converte a string de valor para float"""
        if not self.valor_estimado:
            return None
        try:
            # Remove "R$", pontos de milhar e troca vírgula por ponto
            limpo = self.valor_estimado.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return float(limpo)
        except:
            return None

    def get_data_abertura_objeto(self) -> datetime:
        """Converte a string de abertura_propostas para datetime"""
        if not self.abertura_propostas:
            return None
        try:
            # Padrão esperado: 03/02/2026 às 10:00 ou similar
            import re
            match = re.search(r'(\d{2}/\d{2}/\d{4})', self.abertura_propostas)
            if match:
                return datetime.strptime(match.group(1), '%d/%m/%Y')
        except:
            pass
        return None
    
    @staticmethod
    def buscar_por_controle_pncp(numero_controle_pncp: str) -> 'ResultadoPesquisa':
        """Busca resultado pelo número de controle do PNCP"""
        if not numero_controle_pncp:
            return None
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM pesquisa_resultados WHERE numero_controle_pncp = ?", 
                (numero_controle_pncp,)
            )
            row = cursor.fetchone()
            return ResultadoPesquisa._from_row(row) if row else None
            
    def atualizar_dados(self, dados: dict) -> bool:
        """Atualiza múltiplos campos do resultado no banco de dados"""
        with get_db() as conn:
            try:
                # Mapeia campos do dict para colunas do banco
                mapping = {
                    'status': 'status',
                    'data_realizacao': 'data_realizacao',
                    'valor_estimado': 'valor_estimado',
                    'valor_estimado_numerico': 'valor_estimado_numerico',
                    'valor_homologado': 'valor_homologado',
                    'data_atualizacao_api': 'data_atualizacao_api',
                    'objeto': 'objeto',
                    'limite_recebimento': 'limite_recebimento',
                    'abertura_propostas': 'abertura_propostas'
                }
                
                updates = []
                params = []
                for key, col in mapping.items():
                    if key in dados and dados[key] is not None:
                        updates.append(f"{col} = ?")
                        params.append(dados[key])
                
                if not updates:
                    return False
                
                # Adiciona timestamp de atualização
                updates.append("atualizado_em = CURRENT_TIMESTAMP")
                
                query = f"UPDATE pesquisa_resultados SET {', '.join(updates)} WHERE id = ?"
                params.append(self.id)
                
                conn.execute(query, params)
                return True
            except Exception as e:
                print(f"Erro ao atualizar resultado {self.id}: {e}")
                return False

    @staticmethod
    def buscar_por_id(id: int) -> 'ResultadoPesquisa':
        """Busca resultado por ID"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM pesquisa_resultados WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            return ResultadoPesquisa._from_row(row) if row else None
    
    def marcar_selecionado(self):
        """Marca o resultado como selecionado para detalhamento"""
        with get_db() as conn:
            conn.execute(
                "UPDATE pesquisa_resultados SET selecionado_detalhe = 1 WHERE id = ?",
                (self.id,)
            )
            self.selecionado_detalhe = True
    
    def atualizar_valor(self, valor: str):
        """Atualiza o valor estimado do resultado"""
        with get_db() as conn:
            conn.execute(
                "UPDATE pesquisa_resultados SET valor_estimado = ? WHERE id = ?",
                (valor, self.id)
            )
            self.valor_estimado = valor
    
    @staticmethod
    def contar_por_status() -> dict:
        """Retorna contagem de resultados por status"""
        with get_db() as conn:
            cursor = conn.execute(
                """SELECT status, COUNT(*) as total 
                   FROM pesquisa_resultados 
                   GROUP BY status"""
            )
            return {row['status']: row['total'] for row in cursor.fetchall()}
    
    @staticmethod
    def _from_row(row) -> 'ResultadoPesquisa':
        """Converte uma linha do banco para objeto ResultadoPesquisa"""
        if not row:
            return None
        
        def get_col(name, default=None):
            return row[name] if name in row.keys() else default
        
        return ResultadoPesquisa(
            id=row['id'],
            palavra_chave_id=row['palavra_chave_id'],
            numero_processo=row['numero_processo'],
            titulo=row['titulo'],
            objeto=row['objeto'],
            orgao=row['orgao'],
            uf=row['uf'],
            municipio=row['municipio'],
            modalidade=row['modalidade'],
            status=row['status'],
            data_realizacao=row['data_realizacao'],
            url_processo=row['url_processo'],
            valor_estimado=get_col('valor_estimado'),
            inicio_propostas=get_col('inicio_propostas'),
            limite_recebimento=get_col('limite_recebimento'),
            abertura_propostas=get_col('abertura_propostas'),
            selecionado_detalhe=bool(row['selecionado_detalhe']),
            criado_em=row['criado_em'],
            # Campos de IA
            classificacao_ia=get_col('classificacao_ia'),
            explicacao_ia=get_col('explicacao_ia'),
            classificado_em=get_col('classificado_em'),
            # Novos campos API PNCP
            numero_controle_pncp=get_col('numero_controle_pncp'),
            processo=get_col('processo'),
            valor_estimado_numerico=get_col('valor_estimado_numerico'),
            valor_homologado=get_col('valor_homologado'),
            cnpj_orgao=get_col('cnpj_orgao'),
            codigo_ibge=get_col('codigo_ibge'),
            modalidade_id=get_col('modalidade_id'),
            modo_disputa=get_col('modo_disputa'),
            srp=bool(get_col('srp', 0)),
            amparo_legal=get_col('amparo_legal'),
            data_publicacao_pncp=get_col('data_publicacao_pncp'),
            informacao_complementar=get_col('informacao_complementar'),
            link_processo_eletronico=get_col('link_processo_eletronico'),
            data_atualizacao_api=get_col('data_atualizacao_api'),
            atualizado_em=get_col('atualizado_em')
        )
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'palavra_chave_id': self.palavra_chave_id,
            'numero_processo': self.numero_processo,
            'titulo': self.titulo,
            'objeto': self.objeto,
            'orgao': self.orgao,
            'uf': self.uf,
            'municipio': self.municipio,
            'modalidade': self.modalidade,
            'status': self.status,
            'data_realizacao': self.data_realizacao,
            'url_processo': self.url_processo,
            'valor_estimado': self.valor_estimado,
            'inicio_propostas': self.inicio_propostas,
            'limite_recebimento': self.limite_recebimento,
            'abertura_propostas': self.abertura_propostas,
            'selecionado_detalhe': self.selecionado_detalhe,
            'criado_em': str(self.criado_em) if self.criado_em else None,
            # Campos de IA
            'classificacao_ia': self.classificacao_ia,
            'explicacao_ia': self.explicacao_ia,
            'classificado_em': str(self.classificado_em) if self.classificado_em else None,
            # Novos campos API PNCP
            'numero_controle_pncp': self.numero_controle_pncp,
            'processo': self.processo,
            'valor_estimado_numerico': self.valor_estimado_numerico,
            'valor_homologado': self.valor_homologado,
            'cnpj_orgao': self.cnpj_orgao,
            'codigo_ibge': self.codigo_ibge,
            'modalidade_id': self.modalidade_id,
            'modo_disputa': self.modo_disputa,
            'srp': self.srp,
            'amparo_legal': self.amparo_legal,
            'data_publicacao_pncp': self.data_publicacao_pncp,
            'informacao_complementar': self.informacao_complementar,
            'link_processo_eletronico': self.link_processo_eletronico,
            'data_atualizacao_api': self.data_atualizacao_api
        }

    def salvar_classificacao_manual(self, classificacao: str, explicacao: str = None) -> bool:
        """Salva a classificação definida manualmente pelo usuário"""
        with get_db() as conn:
            try:
                conn.execute('''
                    UPDATE pesquisa_resultados 
                    SET classificacao_ia = ?, 
                        explicacao_ia = ?, 
                        classificado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (classificacao, explicacao, self.id))
                self.classificacao_ia = classificacao
                self.explicacao_ia = explicacao
                return True
            except Exception as e:
                print(f"Erro ao salvar classificação manual: {e}")
                return False
