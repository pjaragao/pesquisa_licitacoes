"""
API Routes - Endpoints da aplicação Flask
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file
import sys
import time
import shutil
import os
import tempfile
from datetime import datetime
from pathlib import Path

# Adiciona o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.palavra_chave import PalavraChave
from app.models.resultado_pesquisa import ResultadoPesquisa
from app.models.oportunidade import Oportunidade
from app.models.configuracao_empresa import ConfiguracaoEmpresa
from app.services.oportunidade_service import OportunidadeService
from app.services.search_manager import search_manager
from app.services.genkit_service import genkit_service

# Blueprint principal
main = Blueprint('main', __name__)


# ==================== PÁGINAS HTML ====================

@main.route('/')
def index():
    """Página inicial - Dashboard"""
    palavras = PalavraChave.listar_todas()
    resultados = ResultadoPesquisa.listar_todos()
    oportunidades = Oportunidade.listar_todas()
    
    stats = {
        'total_palavras': len(palavras),
        'total_resultados': len(resultados),
        'total_oportunidades': len(oportunidades),
        'por_status': ResultadoPesquisa.contar_por_status()
    }
    
    return render_template('index.html', 
                          palavras=palavras,
                          resultados=resultados[:10],  # Últimos 10
                          oportunidades=oportunidades[:10],
                          stats=stats)


@main.route('/pesquisas')
def pagina_pesquisas():
    """Página de gerenciamento de pesquisas e palavras-chave"""
    palavras = PalavraChave.listar_todas(apenas_ativas=False)
    # Tasks não ativas vem pelo front via API, mas podemos inicializar palavras aqui
    return render_template('pesquisas.html', palavras=palavras)


@main.route('/resultados')
def pagina_resultados():
    """Página de resultados de pesquisa"""
    # Filtros
    palavra_id = request.args.get('palavra_id', type=int)
    status = request.args.get('status')
    
    # Filtros Avançados
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    data_de = request.args.get('data_de')
    data_ate = request.args.get('data_ate')
    ufs = request.args.getlist('ufs[]')
    classificacao_ia = request.args.get('classificacao_ia')
    # Ordenação
    ordenar_por = request.args.get('ordenar_por', 'criado_em')
    direcao = request.args.get('direcao', 'desc')
    
    if palavra_id:
        # Nota: Por simplicidade, listar_por_palavra_chave ainda não tem os filtros avançados, 
        # mas podemos usar listar_todos se palavra_id for passado no futuro.
        # Por enquanto, mantemos a lógica mas adicionamos a opção de filtrar tudo.
        resultados = ResultadoPesquisa.listar_por_palavra_chave(palavra_id)
    else:
        resultados = ResultadoPesquisa.listar_todos(
            filtro_status=status,
            valor_min=valor_min,
            valor_max=valor_max,
            data_de=data_de,
            data_ate=data_ate,
            ufs=ufs,
            ordenar_por=ordenar_por,
            direcao=direcao,
            classificacao_ia=classificacao_ia
        )
    
    palavras = PalavraChave.listar_todas()
    
    # Obter configuração da empresa para classificação IA
    configuracao = ConfiguracaoEmpresa.obter()
    
    # Verificar se o servidor GenKit está disponível
    genkit_disponivel = genkit_service.health_check()
    
    return render_template('resultados.html', 
                          resultados=resultados,
                          palavras=palavras,
                          filtro_palavra=palavra_id,
                          filtro_status=status,
                          filtro_valor_min=valor_min,
                          filtro_valor_max=valor_max,
                          filtro_data_de=data_de,
                          filtro_data_ate=data_ate,
                          filtro_ufs=ufs,
                          filtro_classificacao_ia=classificacao_ia,
                          ordenar_por=ordenar_por,
                          direcao=direcao,
                          configuracao=configuracao,
                          genkit_disponivel=genkit_disponivel)


@main.route('/oportunidades')
def pagina_oportunidades():
    """Página de oportunidades"""
    oportunidades = Oportunidade.listar_todas()
    resultados_dict = {}
    for o in oportunidades:
        if o.resultado_id:
            r = ResultadoPesquisa.buscar_por_id(o.resultado_id)
            if r:
                resultados_dict[o.id] = r
                
    return render_template('oportunidades.html', oportunidades=oportunidades, resultados_dict=resultados_dict)


# ==================== API - PALAVRAS-CHAVE ====================

@main.route('/api/palavras-chave', methods=['GET'])
def api_listar_palavras():
    """Lista todas as palavras-chave"""
    palavras = PalavraChave.listar_todas()
    return jsonify([p.to_dict() for p in palavras])


@main.route('/api/palavras-chave', methods=['POST'])
def api_criar_palavra():
    """Cria uma nova palavra-chave"""
    data = request.get_json() or request.form
    termo = data.get('termo', '').strip()
    
    if not termo:
        return jsonify({'error': 'Termo é obrigatório'}), 400
    
    try:
        palavra = PalavraChave.criar(termo)
        return jsonify(palavra.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@main.route('/api/palavras-chave/<int:id>', methods=['DELETE'])
def api_deletar_palavra(id):
    """Deleta uma palavra-chave"""
    palavra = PalavraChave.buscar_por_id(id)
    if not palavra:
        return jsonify({'error': 'Palavra-chave não encontrada'}), 404
    
    palavra.deletar()
    return jsonify({'success': True})


# ==================== API - PESQUISA ====================

@main.route('/api/pesquisar', methods=['POST'])
def api_pesquisar():
    """Executa pesquisa no portal"""
    if request.is_json:
        data = request.get_json()
        palavra_id = data.get('palavra_id')
    else:
        data = request.form
        palavra_id = data.get('palavra_id', type=int)
    
    if palavra_id:
        palavra = PalavraChave.buscar_por_id(int(palavra_id))
        if not palavra:
            return jsonify({'error': 'Palavra-chave não encontrada'}), 404
        termo = palavra.termo
    else:
        termo = data.get('termo', '').strip()
        if not termo:
            return jsonify({'error': 'Termo de pesquisa é obrigatório'}), 400
        # Cria palavra-chave se não existir
        try:
            palavra = PalavraChave.criar(termo)
        except:
            palavras = PalavraChave.listar_todas()
            palavra = next((p for p in palavras if p.termo.lower() == termo.lower()), None)
    
    try:
        # Usa API PNCP via SearchManager (busca por UF + filtro local)
        ufs = data.get('ufs', ['SP', 'RJ', 'MG', 'PR', 'SC', 'RS', 'BA', 'PE', 'CE', 'GO', 'DF'])
        if isinstance(ufs, str):
            ufs = [u.strip() for u in ufs.split(',') if u.strip()]
        
        incremental = data.get('incremental', False)
        if isinstance(incremental, str):
            incremental = incremental.lower() == 'true'
            
        task_id = search_manager.start_search([termo], ufs=ufs, incremental=incremental)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Pesquisa {"incremental" if incremental else "total"} para "{termo}" iniciada.',
            'termo': termo
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/pesquisar-todas', methods=['POST'])
def api_pesquisar_todas():
    """Pesquisa com todas as palavras-chave ativas"""
    palavras = PalavraChave.listar_todas(apenas_ativas=True)
    
    if not palavras:
        return jsonify({'error': 'Nenhuma palavra-chave cadastrada'}), 400
    
    resultados_totais = {
        'palavras_processadas': 0,
        'total_encontrados': 0,
        'novos_salvos': 0,
        'erros': []
    }
    
    try:
        # Usa API PNCP - busca por UFs definidas
        data = request.get_json() if request.is_json else request.form
        ufs = None
        if data:
            ufs = data.get('ufs')
            if isinstance(ufs, str):
                ufs = [u.strip() for u in ufs.split(',') if u.strip()]
        
        incremental = data.get('incremental', False) if data else False
        if isinstance(incremental, str):
            incremental = incremental.lower() == 'true'

        termos = [p.termo for p in palavras]
        task_id = search_manager.start_search(termos, ufs=ufs, incremental=incremental)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Pesquisa {"incremental" if incremental else "total"} para {len(termos)} palavras iniciada.',
            'total_palavras': len(termos)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/pesquisar/status', methods=['GET'])
@main.route('/api/pesquisar/status/<task_id>', methods=['GET'])
def api_pesquisar_status(task_id=None):
    """Retorna o status de uma ou todas as pesquisas"""
    if task_id:
        if isinstance(task_id, str) and task_id.startswith('search_'):
            # Backward compatibility safe ignore
            return jsonify({'error': 'Tarefa legada'}), 404
        try:
            task_id = int(task_id)
            status = search_manager.get_status(task_id)
            if not status:
                return jsonify({'error': 'Tarefa não encontrada'}), 404
            return jsonify(status)
        except ValueError:
            return jsonify({'error': 'ID inválido'}), 400
            
    return jsonify(search_manager.get_all_tasks())

@main.route('/api/pesquisar/<int:task_id>/reiniciar', methods=['POST'])
def api_pesquisar_reiniciar(task_id):
    """Reinicia uma pesquisa que falhou ou travou"""
    try:
        new_id = search_manager.start_search(
            termos=[], incremental=False, task_id_reiniciar=task_id
        )
        return jsonify({'success': True, 'task_id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== API - RESULTADOS ====================

@main.route('/api/resultados', methods=['GET'])
def api_listar_resultados():
    """Lista resultados de pesquisa"""
    palavra_id = request.args.get('palavra_id', type=int)
    status = request.args.get('status')
    
    if palavra_id:
        resultados = ResultadoPesquisa.listar_por_palavra_chave(palavra_id)
    else:
        resultados = ResultadoPesquisa.listar_todos(filtro_status=status)
    
    return jsonify([r.to_dict() for r in resultados])


@main.route('/api/resultados/<int:id>/atualizar', methods=['POST'])
def api_atualizar_resultado(id):
    """Atualiza um resultado individual consultando a API PNCP"""
    resultado = ResultadoPesquisa.buscar_por_id(id)
    if not resultado:
        return jsonify({'error': 'Resultado não encontrado'}), 404
    
    if not resultado.numero_controle_pncp:
        return jsonify({'error': 'Resultado não possui número de controle PNCP'}), 400
        
    try:
        from app.services.pncp_search_service import PncpSearchService
        service = PncpSearchService()
        
        # O número de controle PNCP tem o formato CNPJANOSEQ
        # Mas a API de detalhes precisa deles separados.
        # No entanto, a API PNCP também permite buscar pelo número_controle_pncp em alguns endpoints.
        # Vamos usar o PncpApiClient.buscar_contratacao_detalhes
        
        # Extrai CNPJ, Ano, Sequencial corretamente (formato: CNPJ-1-SEQ/ANO ou similar)
        control = resultado.numero_controle_pncp
        try:
            if "/" in control and "-" in control:
                parts = control.split("/")
                ano = int(parts[1])
                prefix = parts[0] # ex: 82836057000190-1-000007
                cnpj = prefix.split("-")[0].replace(".", "").replace("/", "")
                sequencial = int(prefix.split("-")[-1])
            else:
                cnpj = control[:14]
                ano = int(control[14:18])
                sequencial = int(control[18:])
        except ValueError:
            return jsonify({'error': 'Formato de número de controle PNCP inválido'}), 400
        
        print(f"🔄 Atualizando: {cnpj} / {ano} / {sequencial}")
        
        detalhes_raw = service.client.buscar_contratacao_detalhes(cnpj, ano, sequencial)
        
        if detalhes_raw:
            # Mapeia para o formato do sistema
            dados_mapeados = service._mapear_para_resultado_pesquisa(detalhes_raw)
            updated = resultado.atualizar_dados(dados_mapeados)
            
            if updated:
                return jsonify({
                    'success': True, 
                    'message': 'Resultado atualizado com sucesso!',
                    'novo_status': dados_mapeados.get('status')
                })
        
        return jsonify({'error': 'Não foi possível obter dados atualizados da API'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/resultados/limpar', methods=['POST', 'DELETE'])
def api_limpar_resultados():
    """Limpa todos os resultados de pesquisa"""
    from app import get_db
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM pesquisa_resultados")
        return jsonify({'success': True, 'message': 'Todos os resultados foram removidos'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/resultados/limpar', methods=['POST'])
def form_limpar_resultados():
    """Handler de formulário para limpar resultados"""
    from app import get_db
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM pesquisa_resultados")
            total = cursor.fetchone()['total']
            conn.execute("DELETE FROM pesquisa_resultados")
        flash(f'{total} resultados removidos com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao limpar: {e}', 'error')
    
    return redirect(url_for('main.pagina_resultados'))


# ==================== API - OPORTUNIDADES ====================

@main.route('/api/oportunidades', methods=['GET'])
def api_listar_oportunidades():
    """Lista todas as oportunidades"""
    oportunidades = Oportunidade.listar_todas()
    return jsonify([o.to_dict() for o in oportunidades])


@main.route('/api/oportunidades', methods=['POST'])
def api_criar_oportunidade():
    """Cria uma oportunidade a partir de um resultado"""
    data = request.get_json() or request.form
    resultado_id = data.get('resultado_id')
    
    if not resultado_id:
        return jsonify({'error': 'resultado_id é obrigatório'}), 400
    
    try:
        service = OportunidadeService()
        oportunidade = service.criar_oportunidade(int(resultado_id))
        
        if oportunidade:
            return jsonify(oportunidade.to_dict()), 201
        else:
            return jsonify({'error': 'Falha ao criar oportunidade'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/oportunidades/<codigo>')
def api_obter_oportunidade(codigo):
    """Obtém detalhes de uma oportunidade"""
    oportunidade = Oportunidade.buscar_por_codigo(codigo)
    if not oportunidade:
        return jsonify({'error': 'Oportunidade não encontrada'}), 404
    
    return jsonify(oportunidade.to_dict())


@main.route('/api/oportunidades/limpar', methods=['POST', 'DELETE'])
def api_limpar_oportunidades():
    """Limpa todas as oportunidades"""
    try:
        total = Oportunidade.limpar_todas()
        return jsonify({'success': True, 'message': f'{total} oportunidades removidas'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/oportunidades/limpar', methods=['POST'])
def form_limpar_oportunidades():
    """Handler de formulário para limpar oportunidades"""
    try:
        total = Oportunidade.limpar_todas()
        flash(f'{total} oportunidades removidas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao limpar: {e}', 'error')
    
    return redirect(url_for('main.pagina_oportunidades'))


# ==================== API - DETALHAMENTO PNCP ====================

def _get_pncp_ids(resultado_id):
    """Auxiliar para extrair cnpj, ano e sequencial do resultado"""
    resultado = ResultadoPesquisa.buscar_por_id(resultado_id)
    if not resultado or not resultado.numero_controle_pncp:
        return None, "Resultado não encontrado ou sem controle PNCP"
    
    control = resultado.numero_controle_pncp
    try:
        if "/" in control and "-" in control:
            parts = control.split("/")
            ano = int(parts[1])
            cnpj = parts[0].split("-")[0].replace(".", "").replace("/", "")
            sequencial = int(parts[0].split("-")[-1])
        else:
            cnpj = control[:14]
            ano = int(control[14:18])
            sequencial = int(control[18:])
        return (cnpj, ano, sequencial), None
    except Exception:
        return None, "Formato PNCP inválido"

@main.route('/api/oportunidades/<int:id>/itens', methods=['GET'])
def api_oportunidade_itens(id):
    """Obtém itens da oportunidade (via cache local ou PNCP)"""
    service = OportunidadeService()
    force_refresh = request.args.get('refresh') == 'true'
    
    try:
        itens = service.obter_itens(id, force_refresh=force_refresh)
        return jsonify({'data': itens})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/oportunidades/<int:id>/arquivos', methods=['GET'])
def api_oportunidade_arquivos(id):
    """Obtém arquivos da oportunidade (via cache local ou PNCP)"""
    service = OportunidadeService()
    force_refresh = request.args.get('refresh') == 'true'
    
    try:
        arquivos = service.obter_arquivos(id, force_refresh=force_refresh)
        return jsonify({'data': arquivos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/oportunidades/<int:id>/historico', methods=['GET'])
def api_oportunidade_historico(id):
    """Obtém histórico da oportunidade (via cache local ou PNCP)"""
    service = OportunidadeService()
    force_refresh = request.args.get('refresh') == 'true'
    
    try:
        historico = service.obter_historico(id, force_refresh=force_refresh)
        return jsonify({'data': historico})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/oportunidades/<int:id>/download-zip', methods=['GET'])
def api_oportunidade_download_zip(id):
    """Gera um arquivo ZIP com todos os documentos baixados da oportunidade"""
    oportunidade = Oportunidade.buscar_por_id(id)
    if not oportunidade:
        return jsonify({'error': 'Oportunidade não encontrada'}), 404
        
    service = OportunidadeService()
    pasta_local = Path(oportunidade.pasta_local)
    
    # Garante que a pasta_local seja absoluta e limpa
    pasta_local = Path(str(oportunidade.pasta_local).strip())
    
    # Se estiver fora do docker, tenta converter o caminho /app para o caminho local
    if not pasta_local.exists() and "/app/" in str(pasta_local):
        pasta_local = Path(str(pasta_local).replace("/app/", "/home/paulojr/pesquisa_licitacoes/"))
        
    # Se a pasta não existe ou está vazia, tenta baixar agora (sincronamente)
    resultado = ResultadoPesquisa.buscar_por_id(oportunidade.resultado_id)
    if not pasta_local.exists() or not any(pasta_local.iterdir()):
        if resultado and resultado.numero_controle_pncp:
            print(f"🔄 [ZIP] Iniciando download síncrono para {resultado.numero_controle_pncp}")
            service._baixar_arquivos_background(resultado.numero_controle_pncp, pasta_local)
            
    # Verifica final se baixou algo
    if not pasta_local.exists() or not any(pasta_local.iterdir()):
        # Agora resultado está definido e disponível para a mensagem abaixo
        control_msg = resultado.numero_controle_pncp if resultado else "ID desconhecido"
        return jsonify({
            'error': 'Arquivos não encontrados no servidor.',
            'detalhes': f'Tentamos baixar de {control_msg} mas a pasta {pasta_local} continua vazia.'
        }), 404
        
    try:
        # Cria diretório temporário para o ZIP
        temp_dir = tempfile.mkdtemp()
        zip_base_name = os.path.join(temp_dir, f"Arquivos_{oportunidade.codigo}")
        
        # Cria o arquivo ZIP usando shutil.make_archive
        zip_path_full = shutil.make_archive(zip_base_name, 'zip', str(pasta_local))
        
        return send_file(
            zip_path_full,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"Arquivos_{oportunidade.codigo}.zip"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== FORM HANDLERS ====================

@main.route('/palavras-chave/adicionar', methods=['POST'])
def form_adicionar_palavra():
    """Handler de formulário para adicionar palavra-chave"""
    termo = request.form.get('termo', '').strip()
    
    if termo:
        try:
            PalavraChave.criar(termo)
            flash(f'Palavra-chave "{termo}" adicionada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao adicionar: {e}', 'error')
    else:
        flash('O termo não pode estar vazio', 'error')
    
    return redirect(url_for('main.pagina_pesquisas'))


@main.route('/palavras-chave/deletar/<int:id>', methods=['POST'])
def form_deletar_palavra(id):
    """Handler de formulário para deletar palavra-chave"""
    palavra = PalavraChave.buscar_por_id(id)
    if palavra:
        palavra.deletar()
        flash(f'Palavra-chave "{palavra.termo}" removida', 'success')
    else:
        flash('Palavra-chave não encontrada', 'error')
    
    return redirect(url_for('main.pagina_pesquisas'))


@main.route('/pesquisar', methods=['POST'])
def form_pesquisar():
    """Handler de formulário para pesquisar via API PNCP"""
    palavra_id = request.form.get('palavra_id')
    termo = request.form.get('termo', '').strip()
    
    try:
        # Pega os termos
        termos_busca = []
        if palavra_id:
            palavra = PalavraChave.buscar_por_id(int(palavra_id))
            if palavra:
                termos_busca.append(palavra.termo)
        elif termo:
            termos_busca.append(termo)
            
        if not termos_busca:
            flash('Nenhum termo para pesquisar', 'error')
            return redirect(url_for('main.pagina_resultados'))

        # Obtém UFs do formulário (usa padrão se não especificado)
        ufs = request.form.getlist('ufs') or None
        
        # Inicia em background via API PNCP
        search_manager.start_search(termos_busca, ufs=ufs)
        
        flash(f'Pesquisa iniciada via API PNCP para: {", ".join(termos_busca)}. Acompanhe o progresso na página de Palavras-Chave.', 'success')
        
    except Exception as e:
        flash(f'Erro ao iniciar pesquisa: {e}', 'error')
    
    return redirect(url_for('main.pagina_pesquisas'))


@main.route('/criar-oportunidade/<int:resultado_id>', methods=['POST'])
def form_criar_oportunidade(resultado_id):
    """Handler de formulário para criar oportunidade"""
    try:
        service = OportunidadeService()
        oportunidade = service.criar_oportunidade(resultado_id)
        
        if oportunidade:
            flash(f'Oportunidade {oportunidade.codigo} criada com sucesso!', 'success')
        else:
            flash('Falha ao criar oportunidade', 'error')
            
    except Exception as e:
        flash(f'Erro: {e}', 'error')
    
    return redirect(url_for('main.pagina_oportunidades'))


@main.route('/api/oportunidade/criar/<int:resultado_id>', methods=['POST'])
def api_criar_oportunidade_by_id(resultado_id):
    """API para criar oportunidade em background (AJAX)"""
    try:
        service = OportunidadeService()
        oportunidade = service.criar_oportunidade(resultado_id)
        
        if oportunidade:
            return jsonify({
                'success': True,
                'codigo': oportunidade.codigo,
                'message': f'Oportunidade {oportunidade.codigo} criada com sucesso!'
            })
        else:
            return jsonify({'success': False, 'error': 'Falha ao criar oportunidade'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API - CLASSIFICAÇÃO IA ====================

@main.route('/api/configuracao-empresa', methods=['GET'])
def api_obter_configuracao():
    """Obtém a configuração da empresa"""
    config = ConfiguracaoEmpresa.obter()
    if config:
        return jsonify(config.to_dict())
    return jsonify({'prompt_empresa': None})


@main.route('/api/configuracao-empresa', methods=['POST'])
def api_salvar_configuracao():
    """Salva a configuração da empresa"""
    data = request.get_json() or request.form
    prompt_empresa = data.get('prompt_empresa', '').strip()
    
    if not prompt_empresa:
        return jsonify({'error': 'O prompt da empresa é obrigatório'}), 400
    
    try:
        config = ConfiguracaoEmpresa.salvar(prompt_empresa)
        return jsonify(config.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/ia/otimizar-prompt', methods=['POST'])
def api_otimizar_prompt():
    """Otimiza o prompt da empresa usando IA"""
    data = request.get_json() or request.form
    prompt_atual = data.get('prompt_atual', '').strip()
    
    if not prompt_atual:
        return jsonify({'error': 'O prompt atual é obrigatório'}), 400
    
    try:
        # Verifica se GenKit está disponível
        if not genkit_service.health_check():
            return jsonify({'error': 'Servidor GenKit não está disponível. Inicie o servidor com: cd genkit-server && npm run dev'}), 503
        
        resultado = genkit_service.otimizar_prompt(prompt_atual)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/ia/classificar', methods=['POST'])
def api_classificar_resultados():
    """Classifica resultados de licitação usando IA em lotes de 20"""
    data = request.get_json() or {}
    resultado_ids = data.get('resultado_ids', [])
    tamanho_lote = data.get('tamanho_lote', 20)
    model = data.get('model')  # Pega o modelo do request
    
    # Obtém configuração da empresa
    config = ConfiguracaoEmpresa.obter()
    if not config or not config.prompt_empresa:
        return jsonify({'error': 'Configure o prompt da empresa antes de classificar'}), 400
    
    try:
        # Verifica se GenKit está disponível
        if not genkit_service.health_check():
            return jsonify({'error': 'Servidor GenKit não está disponível. Inicie o servidor com: cd genkit-server && npm run dev'}), 503
        
        # Se não especificou IDs, pega TODOS os resultados sem classificação
        if not resultado_ids:
            from app import get_db
            with get_db() as db:
                rows = db.execute('''
                    SELECT id FROM pesquisa_resultados 
                    WHERE classificacao_ia IS NULL
                    ORDER BY criado_em DESC
                ''').fetchall()
                resultado_ids = [row['id'] for row in rows]
        
        if not resultado_ids:
            return jsonify({'message': 'Nenhum resultado para classificar', 'classificados': 0, 'total': 0})
        
        total_para_classificar = len(resultado_ids)
        total_classificados = 0
        todas_classificacoes = []
        
        # Processa em lotes de 20
        for i in range(0, len(resultado_ids), tamanho_lote):
            lote_ids = resultado_ids[i:i + tamanho_lote]
            
            # Busca os resultados do lote
            resultados = []
            for rid in lote_ids:
                r = ResultadoPesquisa.buscar_por_id(rid)
                if r:
                    resultados.append(r.to_dict())
            
            if not resultados:
                continue
            
            # Classifica o lote
            classificacoes = genkit_service.classificar_lote(config.prompt_empresa, resultados, model=model)
            
            # Salva as classificações no banco
            from app import get_db
            with get_db() as db:
                for c in classificacoes:
                    db.execute('''
                        UPDATE pesquisa_resultados 
                        SET classificacao_ia = ?, explicacao_ia = ?, classificado_em = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (c.get('classificacao'), c.get('explicacao'), c.get('id')))
                db.commit()
            
            total_classificados += len(classificacoes)
            todas_classificacoes.extend(classificacoes)
            
            # Pequeno delay entre lotes para evitar 429
            if i + tamanho_lote < len(resultado_ids):
                time.sleep(1.5)
        
        return jsonify({
            'success': True,
            'total': total_para_classificar,
            'classificados': total_classificados,
            'classificacoes': todas_classificacoes
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/ia/classificar-manual/<int:id>', methods=['POST'])
def api_classificar_manual(id):
    """Atualiza manualmente a classificação de um resultado"""
    data = request.get_json() or {}
    classificacao = data.get('classificacao')
    explicacao = data.get('explicacao', 'Classificado manualmente pelo usuário.')
    
    if not classificacao or classificacao not in ['ADEQUADO', 'NAO_ADEQUADO', 'INCERTO']:
        return jsonify({'error': 'Classificação inválida'}), 400
        
    resultado = ResultadoPesquisa.buscar_por_id(id)
    if not resultado:
        return jsonify({'error': 'Resultado não encontrado'}), 404
        
    if resultado.salvar_classificacao_manual(classificacao, explicacao):
        return jsonify({
            'success': True, 
            'message': 'Classificação atualizada com sucesso!',
            'classificacao': classificacao
        })
    else:
        return jsonify({'error': 'Erro ao atualizar classificação'}), 500


@main.route('/api/ia/estatisticas', methods=['GET'])
def api_ia_estatisticas():
    """Retorna estatísticas de classificação"""
    try:
        from app import get_db
        with get_db() as db:
            stats = {}
            
            # Total de resultados
            stats['total'] = db.execute('SELECT COUNT(*) as c FROM pesquisa_resultados').fetchone()['c']
            
            # Por classificação
            stats['adequado'] = db.execute(
                "SELECT COUNT(*) as c FROM pesquisa_resultados WHERE classificacao_ia = 'ADEQUADO'"
            ).fetchone()['c']
            
            stats['nao_adequado'] = db.execute(
                "SELECT COUNT(*) as c FROM pesquisa_resultados WHERE classificacao_ia = 'NAO_ADEQUADO'"
            ).fetchone()['c']
            
            stats['incerto'] = db.execute(
                "SELECT COUNT(*) as c FROM pesquisa_resultados WHERE classificacao_ia = 'INCERTO'"
            ).fetchone()['c']
            
            stats['nao_classificado'] = db.execute(
                "SELECT COUNT(*) as c FROM pesquisa_resultados WHERE classificacao_ia IS NULL"
            ).fetchone()['c']
            
            return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/ia/limpar-classificacoes', methods=['POST'])
def api_limpar_classificacoes():
    """Limpa todas as classificações de IA"""
    try:
        from app import get_db
        with get_db() as db:
            cursor = db.execute('''
                UPDATE pesquisa_resultados 
                SET classificacao_ia = NULL, explicacao_ia = NULL, classificado_em = NULL
            ''')
            db.commit()
            return jsonify({'success': True, 'limpos': cursor.rowcount})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/ia/status', methods=['GET'])
def api_ia_status():
    """Verifica o status do servidor GenKit"""
    disponivel = genkit_service.health_check()
    return jsonify({
        'disponivel': disponivel,
        'url': genkit_service.base_url
    })

@main.route('/api/ia/modelos', methods=['GET'])
def api_ia_modelos():
    """Retorna os modelos disponíveis no GenKit"""
    modelos = genkit_service.listar_modelos()
    return jsonify(modelos)
