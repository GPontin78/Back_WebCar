from flask import jsonify
from main import app, con
from funcao import descobre_tipo_usuario
from datetime import date, datetime


@app.route('/dashboard_resumo', methods=['GET'])
def dashboard_resumo():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        hoje = date.today()

        capital_estoque = 0
        receita_total_gerencial = 0
        receita_extra = 0
        despesa_total = 0
        lucro_bruto_vendas = 0
        ticket_medio = 0
        qtd_veiculos_estoque = 0
        qtd_vendas = 0
        qtd_financiamentos = 0
        total_a_receber_financiamento = 0
        qtd_parcelas_atrasadas = 0
        valor_parcelas_atrasadas = 0
        inadimplencia_percentual = 0

        cursor.execute("""
            SELECT preco_custo
            FROM veiculo
            WHERE status = 0
        """)
        veiculos_estoque = cursor.fetchall()

        qtd_veiculos_estoque = len(veiculos_estoque)

        for veiculo in veiculos_estoque:
            capital_estoque += float(veiculo[0] or 0)

        cursor.execute("""
            SELECT valor_venda
            FROM venda
        """)
        vendas = cursor.fetchall()

        qtd_vendas = len(vendas)

        for venda in vendas:
            receita_total_gerencial += float(venda[0] or 0)

        if qtd_vendas > 0:
            ticket_medio = receita_total_gerencial / qtd_vendas

        cursor.execute("""
            SELECT valor
            FROM receita
            WHERE tabela IS NULL OR upper(tabela) <> 'VENDA'
        """)
        receitas = cursor.fetchall()

        for receita in receitas:
            valor_receita = float(receita[0] or 0)
            receita_extra += valor_receita
            receita_total_gerencial += valor_receita

        cursor.execute("""
            SELECT valor
            FROM despesa
        """)
        despesas = cursor.fetchall()

        for despesa in despesas:
            despesa_total += float(despesa[0] or 0)

        cursor.execute("""
            SELECT vd.valor_venda, ve.preco_custo
            FROM venda vd
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
        """)
        vendas_lucro = cursor.fetchall()

        for venda in vendas_lucro:
            valor_venda = float(venda[0] or 0)
            preco_custo = float(venda[1] or 0)
            lucro_bruto_vendas += valor_venda - preco_custo

        cursor.execute("""
            SELECT id_financiamento
            FROM financiamento
        """)
        financiamentos = cursor.fetchall()

        qtd_financiamentos = len(financiamentos)

        cursor.execute("""
            SELECT valor_parcela, data_vencimento, status
            FROM item_financiamento
        """)
        parcelas = cursor.fetchall()

        for parcela in parcelas:
            valor_parcela = float(parcela[0] or 0)
            data_vencimento = parcela[1]
            status = int(parcela[2] or 0)

            if status in(0,3):
                total_a_receber_financiamento += valor_parcela

                if data_vencimento:
                    data_comparar = data_vencimento

                    if isinstance(data_vencimento, datetime):
                        data_comparar = data_vencimento.date()

                    if data_comparar < hoje:
                        qtd_parcelas_atrasadas += 1
                        valor_parcelas_atrasadas += valor_parcela

        if total_a_receber_financiamento > 0:
            inadimplencia_percentual = (valor_parcelas_atrasadas / total_a_receber_financiamento) * 100

        lucro_liquido_estimado = lucro_bruto_vendas + receita_extra - despesa_total

        return jsonify({
            'capital_estoque': round(capital_estoque, 2),
            'receita_total_gerencial': round(receita_total_gerencial, 2),
            'receita_extra': round(receita_extra, 2),
            'despesa_total': round(despesa_total, 2),
            'lucro_liquido_estimado': round(lucro_liquido_estimado, 2),
            'lucro_bruto_vendas': round(lucro_bruto_vendas, 2),
            'ticket_medio': round(ticket_medio, 2),
            'qtd_veiculos_estoque': qtd_veiculos_estoque,
            'qtd_vendas': qtd_vendas,
            'qtd_financiamentos': qtd_financiamentos,
            'total_a_receber_financiamento': round(total_a_receber_financiamento, 2),
            'qtd_parcelas_atrasadas': qtd_parcelas_atrasadas,
            'valor_parcelas_atrasadas': round(valor_parcelas_atrasadas, 2),
            'inadimplencia_percentual': round(inadimplencia_percentual, 2)
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar resumo: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_vendas', methods=['GET'])
def dashboard_vendas():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_vendas = []

        cursor.execute("""
            SELECT
                vd.id_venda,
                cliente.nome,
                m.nome,
                ve.modelo,
                vd.data_venda,
                vd.forma_pagamento,
                vd.valor_venda,
                ve.preco_custo
            FROM venda vd
            LEFT JOIN usuario cliente ON cliente.id_usuario = vd.id_usuario_cliente
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
            INNER JOIN marca m ON m.id_marca = ve.id_marca
            ORDER BY vd.data_venda DESC
        """)

        vendas = cursor.fetchall()

        for venda in vendas:
            forma_pagamento = venda[5]
            nome_forma = 'Não informado'

            if forma_pagamento == 0:
                nome_forma = 'À vista'
            elif forma_pagamento == 1:
                nome_forma = 'Financiamento'
            elif forma_pagamento == 2:
                nome_forma = 'Pix'
            elif forma_pagamento == 3:
                nome_forma = 'Cartão'
            elif forma_pagamento == 4:
                nome_forma = 'Boleto'

            valor_venda = float(venda[6] or 0)
            preco_custo = float(venda[7] or 0)
            lucro_bruto = valor_venda - preco_custo

            lista_vendas.append({
                'id_venda': venda[0],
                'cliente': venda[1] or 'Sem cliente',
                'veiculo': f'{venda[2]} {venda[3]}',
                'data_venda': str(venda[4]) if venda[4] else None,
                'forma_pagamento': nome_forma,
                'valor_venda': round(valor_venda, 2),
                'preco_custo': round(preco_custo, 2),
                'lucro_bruto': round(lucro_bruto, 2)
            })

        return jsonify({'vendas': lista_vendas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar vendas: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_despesas', methods=['GET'])
def dashboard_despesas():
    # funcao da tabela e relatorio de despesas da dashboard
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_despesas = []

        cursor.execute("""
            SELECT
                id_despesa,
                descricao,
                valor,
                data_despesa,
                tabela,
                id_tabela,
                status
            FROM despesa
            ORDER BY data_despesa DESC
        """)

        despesas = cursor.fetchall()

        for despesa in despesas:
            lista_despesas.append({
                'id_despesa': despesa[0],
                'descricao': despesa[1],
                'tabela': despesa[4],
                'id_tabela': despesa[5],
                'valor': float(despesa[2] or 0),
                'data_despesa': str(despesa[3]) if despesa[3] else None,
                'status': int(despesa[6] or 0)
            })

        return jsonify({'despesas': lista_despesas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar despesas: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_receitas', methods=['GET'])
def dashboard_receitas():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'UsuÃ¡rio nÃ£o logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_receitas = []

        cursor.execute("""
            SELECT
                id_receita,
                descricao,
                valor,
                data_receita,
                tabela,
                id_tabela,
                status
            FROM receita
            ORDER BY data_receita DESC
        """)

        receitas = cursor.fetchall()

        for receita in receitas:
            lista_receitas.append({
                'id_receita': receita[0],
                'descricao': receita[1],
                'valor': float(receita[2] or 0),
                'data_receita': str(receita[3]) if receita[3] else None,
                'tabela': receita[4],
                'id_tabela': receita[5],
                'status': int(receita[6] or 0)
            })

        return jsonify({'receitas': lista_receitas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar receitas: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_financiamentos', methods=['GET'])
def dashboard_financiamentos():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        hoje = date.today()
        lista_financiamentos = []

        cursor.execute("""
            SELECT
                f.id_financiamento,
                cliente.nome,
                m.nome,
                ve.modelo,
                f.data_financiamento,
                f.valor_venda,
                f.valor_venda_financiamento
            FROM financiamento f
            INNER JOIN venda vd ON vd.id_venda = f.id_venda
            LEFT JOIN usuario cliente ON cliente.id_usuario = vd.id_usuario_cliente
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
            INNER JOIN marca m ON m.id_marca = ve.id_marca
            ORDER BY f.data_financiamento DESC
        """)

        financiamentos = cursor.fetchall()

        for financiamento in financiamentos:
            id_financiamento = financiamento[0]

            qtd_parcelas = 0
            parcelas_abertas = 0
            parcelas_pagas = 0
            parcelas_atrasadas = 0
            saldo_devedor = 0

            cursor.execute("""
                SELECT valor_parcela, data_vencimento, status
                FROM item_financiamento
                WHERE id_financiamento = ?
            """, (id_financiamento,))

            parcelas = cursor.fetchall()

            for parcela in parcelas:
                qtd_parcelas += 1

                valor_parcela = float(parcela[0] or 0)
                data_vencimento = parcela[1]
                status = int(parcela[2] or 0)

                if status == 1:
                    parcelas_pagas += 1
                else:
                    parcelas_abertas += 1
                    saldo_devedor += valor_parcela

                    if data_vencimento:
                        data_comparar = data_vencimento

                        if isinstance(data_vencimento, datetime):
                            data_comparar = data_vencimento.date()

                        if data_comparar < hoje:
                            parcelas_atrasadas += 1

            lista_financiamentos.append({
                'id_financiamento': id_financiamento,
                'cliente': financiamento[1] or 'Sem cliente',
                'veiculo': f'{financiamento[2]} {financiamento[3]}',
                'data_financiamento': str(financiamento[4]) if financiamento[4] else None,
                'valor_financiado': float(financiamento[6] or 0),
                'saldo_devedor': round(saldo_devedor, 2),
                'qtd_parcelas': qtd_parcelas,
                'parcelas_abertas': parcelas_abertas,
                'parcelas_pagas': parcelas_pagas,
                'parcelas_atrasadas': parcelas_atrasadas
            })

        return jsonify({'financiamentos': lista_financiamentos}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar financiamentos: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_parcelas', methods=['GET'])
def dashboard_parcelas():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        hoje = date.today()
        lista_parcelas = []

        cursor.execute("""
            SELECT
                it.id_item_financiamento,
                it.id_financiamento,
                cliente.nome,
                marca.nome,
                ve.modelo,
                it.numero_parcela,
                it.valor_parcela,
                it.data_vencimento,
                it.data_pagamento,
                it.status
            FROM item_financiamento it
            INNER JOIN financiamento f ON f.id_financiamento = it.id_financiamento
            INNER JOIN venda vd ON vd.id_venda = f.id_venda
            LEFT JOIN usuario cliente ON cliente.id_usuario = vd.id_usuario_cliente
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
            INNER JOIN marca marca ON marca.id_marca = ve.id_marca
            ORDER BY it.data_vencimento
        """)

        parcelas = cursor.fetchall()

        for parcela in parcelas:
            status = int(parcela[9] or 0)
            data_vencimento = parcela[7]
            atrasada = False

            if status == 0 and data_vencimento:
                data_comparar = data_vencimento

                if isinstance(data_vencimento, datetime):
                    data_comparar = data_vencimento.date()

                if data_comparar < hoje:
                    atrasada = True

            lista_parcelas.append({
                'id_item_financiamento': parcela[0],
                'id_financiamento': parcela[1],
                'cliente': parcela[2] or 'Sem cliente',
                'veiculo': f'{parcela[3]} {parcela[4]}',
                'numero_parcela': parcela[5],
                'valor_parcela': float(parcela[6] or 0),
                'data_vencimento': str(parcela[7]) if parcela[7] else None,
                'data_pagamento': str(parcela[8]) if parcela[8] else None,
                'status': status,
                'atrasada': atrasada
            })

        return jsonify({'parcelas': lista_parcelas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar parcelas: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_veiculos', methods=['GET'])
def dashboard_veiculos():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_veiculos = []

        cursor.execute("""
            SELECT
                v.id_veiculo,
                m.nome,
                v.modelo,
                v.placa,
                v.status,
                v.documentacao,
                v.preco_custo,
                v.preco_venda,
                v.data_cadastro
            FROM veiculo v
            INNER JOIN marca m ON m.id_marca = v.id_marca
            ORDER BY v.id_veiculo DESC
        """)

        veiculos = cursor.fetchall()

        for veiculo in veiculos:
            lista_veiculos.append({
                'id_veiculo': veiculo[0],
                'marca': veiculo[1],
                'modelo': veiculo[2],
                'placa': veiculo[3],
                'status': int(veiculo[4] or 0),
                'documentacao': int(veiculo[5] or 0),
                'preco_custo': float(veiculo[6] or 0),
                'preco_venda': float(veiculo[7] or 0),
                'data_cadastro': str(veiculo[8]) if veiculo[8] else None
            })

        return jsonify({'veiculos': lista_veiculos}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar veículos: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_manutencoes', methods=['GET'])
def dashboard_manutencoes():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_manutencoes = []
        lista_itens = []

        cursor.execute("""
            SELECT
                ma.id_manutencao,
                ma.id_veiculo,
                marca.nome,
                ve.modelo,
                ma."DATA",
                ma.valor_total
            FROM manutencao ma
            INNER JOIN veiculo ve ON ve.id_veiculo = ma.id_veiculo
            INNER JOIN marca marca ON marca.id_marca = ve.id_marca
            ORDER BY ma."DATA" DESC
        """)

        manutencoes = cursor.fetchall()

        for manutencao in manutencoes:
            lista_manutencoes.append({
                'id_manutencao': manutencao[0],
                'id_veiculo': manutencao[1],
                'veiculo': f'{manutencao[2]} {manutencao[3]}',
                'data': str(manutencao[4]) if manutencao[4] else None,
                'valor_total': float(manutencao[5] or 0)
            })

        cursor.execute("""
            SELECT
                im.id_item_manutencao,
                im.id_manutencao,
                serv.descricao,
                im.quantidade,
                im.valor_total,
                ma."DATA",
                marca.nome,
                ve.modelo
            FROM item_manutencao im
            INNER JOIN manutencao ma ON ma.id_manutencao = im.id_manutencao
            INNER JOIN servico serv ON serv.id_servico = im.id_servico
            INNER JOIN veiculo ve ON ve.id_veiculo = ma.id_veiculo
            INNER JOIN marca marca ON marca.id_marca = ve.id_marca
            ORDER BY ma."DATA" DESC
        """)

        itens = cursor.fetchall()

        for item in itens:
            lista_itens.append({
                'id_item_manutencao': item[0],
                'id_manutencao': item[1],
                'servico': item[2],
                'quantidade': item[3],
                'valor_total': float(item[4] or 0),
                'data': str(item[5]) if item[5] else None,
                'veiculo': f'{item[6]} {item[7]}'
            })

        return jsonify({
            'manutencoes': lista_manutencoes,
            'itens': lista_itens
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar manutenções: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/dashboard_graficos', methods=['GET'])
def dashboard_graficos():
    # Descobre o tipo do usuário logado pelo token/cookie.
    tipo_usuario = descobre_tipo_usuario()

    # Se não tiver usuário logado, bloqueia.
    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    # Se não for ADM, bloqueia.
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        hoje = date.today()

        # Dicionários usados para juntar dados repetidos.
        # Exemplo: várias vendas no mesmo mês entram no mesmo mês.
        financeiro_mensal = {}
        vendas_por_forma_pagamento = {}
        fluxo_recebimentos = {}

        # Esse dicionário já começa com os 3 status principais.
        # Depois o for vai somando quantidade e valor em cada status.
        parcelas_status = {
            'Pagas': {'status': 'Pagas', 'quantidade': 0, 'valor': 0},
            'Em aberto': {'status': 'Em aberto', 'quantidade': 0, 'valor': 0},
            'Atrasadas': {'status': 'Atrasadas', 'quantidade': 0, 'valor': 0}
        }

        documentacao = {}
        manutencao_por_veiculo = {}
        servicos_mais_usados = {}

        # Esse dicionário guarda o total de manutenção pelo id do veículo.
        # Ele vai ser usado depois para calcular lucro real.
        manutencao_por_id_veiculo = {}

        performance_vendedores = {}
        lucro_real_veiculos = []

        # funcao do grafico receita, despesa e lucro
        # ==========================================================
        # FINANCEIRO MENSAL - VENDAS
        # ==========================================================

        # Busca todas as vendas que têm data.
        cursor.execute("""
            SELECT
                vd.data_venda,
                vd.valor_venda,
                ve.preco_custo
            FROM venda vd
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
            WHERE vd.data_venda IS NOT NULL
        """)
        vendas = cursor.fetchall()

        # Esse for passa venda por venda.
        # Para cada venda, ele descobre o mês e soma o valor no mês certo.
        for venda in vendas:
            data_venda = venda[0]
            valor_venda = float(venda[1] or 0)
            preco_custo = float(venda[2] or 0)

            # Monta uma chave tipo "2026-05".
            chave = str(data_venda.year) + '-' + str(data_venda.month).zfill(2)

            # Se esse mês ainda não existe no dicionário, cria ele.
            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita': 0,
                    'despesas': 0,
                    'custo_vendidos': 0,
                    'manutencao': 0,
                    'lucro_bruto': 0,
                    'lucro': 0
                }

            # Soma o valor da venda na receita daquele mês.
            financeiro_mensal[chave]['receita'] += valor_venda
            financeiro_mensal[chave]['custo_vendidos'] += preco_custo
            financeiro_mensal[chave]['lucro_bruto'] += valor_venda - preco_custo

        # funcao do grafico receita, despesa e lucro
        # ==========================================================
        # FINANCEIRO MENSAL - RECEITAS EXTRAS
        # ==========================================================

        # Busca receitas extras que não são venda.
        cursor.execute("""
            SELECT data_receita, valor
            FROM receita
            WHERE data_receita IS NOT NULL
            AND (tabela IS NULL OR upper(tabela) <> 'VENDA')
        """)
        receitas = cursor.fetchall()

        # Esse for passa receita por receita.
        # Ele soma cada receita extra no mês correspondente.
        for receita in receitas:
            data_receita = receita[0]
            valor = float(receita[1] or 0)

            chave = str(data_receita.year) + '-' + str(data_receita.month).zfill(2)

            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita': 0,
                    'despesas': 0,
                    'custo_vendidos': 0,
                    'manutencao': 0,
                    'lucro_bruto': 0,
                    'lucro': 0
                }

            financeiro_mensal[chave]['receita'] += valor

        # funcao do grafico receita, despesa e lucro
        # ==========================================================
        # FINANCEIRO MENSAL - DESPESAS
        # ==========================================================

        # Busca despesas com data.
        cursor.execute("""
            SELECT data_despesa, valor, tabela
            FROM despesa
            WHERE data_despesa IS NOT NULL
            AND (status IS NULL OR status = 0)
        """)
        despesas = cursor.fetchall()

        # Esse for passa despesa por despesa.
        # Ele soma cada despesa no mês correspondente.
        for despesa in despesas:
            data_despesa = despesa[0]
            valor = float(despesa[1] or 0)
            tabela_despesa = despesa[2] or ''

            chave = str(data_despesa.year) + '-' + str(data_despesa.month).zfill(2)

            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita': 0,
                    'despesas': 0,
                    'custo_vendidos': 0,
                    'manutencao': 0,
                    'lucro_bruto': 0,
                    'lucro': 0
                }

            financeiro_mensal[chave]['despesas'] += valor

            if str(tabela_despesa).upper() == 'ITEM_MANUTENCAO':
                financeiro_mensal[chave]['manutencao'] += valor

        financeiro_mensal_lista = []

        # Aqui transforma o dicionário financeiro_mensal em lista.
        # O front trabalha melhor com lista para montar gráfico.
        for chave in sorted(financeiro_mensal.keys()):
            item = financeiro_mensal[chave]

            # Lucro mensal = receita - despesas.
            item['lucro'] = item['receita'] - item['despesas']

            financeiro_mensal_lista.append({
                'mes': item['mes'],
                'receita': round(item['receita'], 2),
                'despesas': round(item['despesas'], 2),
                'custo_vendidos': round(item['custo_vendidos'], 2),
                'manutencao': round(item['manutencao'], 2),
                'lucro_bruto': round(item['lucro_bruto'], 2),
                'lucro': round(item['lucro'], 2)
            })

        # funcao do grafico vendas por forma de pagamento
        # ==========================================================
        # VENDAS POR FORMA DE PAGAMENTO
        # ==========================================================

        # Busca todas as vendas com a forma de pagamento.
        cursor.execute("""
            SELECT forma_pagamento, valor_venda
            FROM venda
        """)
        formas = cursor.fetchall()

        # Esse for agrupa as vendas pela forma de pagamento.
        # Exemplo: todas as vendas "Pix" vão cair na mesma chave.
        for forma in formas:
            forma_pagamento = forma[0]
            valor_venda = float(forma[1] or 0)

            nome = 'Não informado'

            if forma_pagamento == 0:
                nome = 'À vista'
            elif forma_pagamento == 1:
                nome = 'Financiamento'
            elif forma_pagamento == 2:
                nome = 'Pix'
            elif forma_pagamento == 3:
                nome = 'Cartão'
            elif forma_pagamento == 4:
                nome = 'Boleto'

            if nome not in vendas_por_forma_pagamento:
                vendas_por_forma_pagamento[nome] = {
                    'forma_pagamento': nome,
                    'quantidade': 0,
                    'valor_total': 0
                }

            vendas_por_forma_pagamento[nome]['quantidade'] += 1
            vendas_por_forma_pagamento[nome]['valor_total'] += valor_venda

        vendas_por_forma_pagamento_lista = []

        # Transforma o dicionário de forma de pagamento em lista.
        for chave in vendas_por_forma_pagamento:
            item = vendas_por_forma_pagamento[chave]

            vendas_por_forma_pagamento_lista.append({
                'forma_pagamento': item['forma_pagamento'],
                'quantidade': item['quantidade'],
                'valor_total': round(item['valor_total'], 2)
            })

        # funcao do grafico parcelas por status e fluxo futuro
        # ==========================================================
        # PARCELAS STATUS + FLUXO DE RECEBIMENTOS
        # ==========================================================

        # Busca todas as parcelas de financiamento.
        cursor.execute("""
            SELECT valor_parcela, data_vencimento, status
            FROM item_financiamento
        """)
        parcelas = cursor.fetchall()

        # Esse for passa parcela por parcela.
        # Ele separa parcelas pagas, abertas e atrasadas.
        # Também monta o fluxo futuro de recebimentos por mês.
        for parcela in parcelas:
            valor_parcela = float(parcela[0] or 0)
            data_vencimento = parcela[1]
            status = int(parcela[2] or 0)

            # Status 1 significa paga.
            if status == 1:
                parcelas_status['Pagas']['quantidade'] += 1
                parcelas_status['Pagas']['valor'] += valor_parcela

            # Status 0 significa aberta.
            else:
                parcelas_status['Em aberto']['quantidade'] += 1
                parcelas_status['Em aberto']['valor'] += valor_parcela

                if data_vencimento:
                    data_comparar = data_vencimento

                    # Se vier datetime, transforma em date.
                    if isinstance(data_vencimento, datetime):
                        data_comparar = data_vencimento.date()

                    # Monta a chave do mês de vencimento.
                    chave = str(data_comparar.year) + '-' + str(data_comparar.month).zfill(2)

                    if chave not in fluxo_recebimentos:
                        fluxo_recebimentos[chave] = {
                            'mes': chave,
                            'valor_a_receber': 0
                        }

                    # Soma no mês quanto a empresa tem para receber.
                    fluxo_recebimentos[chave]['valor_a_receber'] += valor_parcela

                    # Se está aberta e já passou da data, conta como atrasada.
                    if data_comparar < hoje:
                        parcelas_status['Atrasadas']['quantidade'] += 1
                        parcelas_status['Atrasadas']['valor'] += valor_parcela

        parcelas_status_lista = []

        # Transforma o dicionário de parcelas em lista.
        for chave in parcelas_status:
            item = parcelas_status[chave]

            parcelas_status_lista.append({
                'status': item['status'],
                'quantidade': item['quantidade'],
                'valor': round(item['valor'], 2)
            })

        fluxo_recebimentos_lista = []

        # Transforma o fluxo de recebimentos em lista ordenada pelo mês.
        for chave in sorted(fluxo_recebimentos.keys()):
            item = fluxo_recebimentos[chave]

            fluxo_recebimentos_lista.append({
                'mes': item['mes'],
                'valor_a_receber': round(item['valor_a_receber'], 2)
            })

        # funcao do grafico documentacao pendente
        # ==========================================================
        # DOCUMENTAÇÃO
        # ==========================================================

        # Busca veículos em estoque e a situação da documentação.
        cursor.execute("""
            SELECT documentacao, preco_custo
            FROM veiculo
            WHERE status = 0
        """)
        docs = cursor.fetchall()

        # Esse for agrupa os veículos por documentação pendente ou regularizada.
        for doc in docs:
            status_doc = doc[0]
            preco_custo = float(doc[1] or 0)

            nome_doc = 'Não informado'

            if status_doc == 0:
                nome_doc = 'Pendente'
            elif status_doc == 1:
                nome_doc = 'Regularizada'

            if nome_doc not in documentacao:
                documentacao[nome_doc] = {
                    'status': nome_doc,
                    'quantidade': 0,
                    'capital': 0
                }

            documentacao[nome_doc]['quantidade'] += 1
            documentacao[nome_doc]['capital'] += preco_custo

        documentacao_lista = []

        # Transforma documentação em lista.
        for chave in documentacao:
            item = documentacao[chave]

            documentacao_lista.append({
                'status': item['status'],
                'quantidade': item['quantidade'],
                'capital': round(item['capital'], 2)
            })

        # funcao do grafico manutencao por veiculo
        # ==========================================================
        # MANUTENÇÃO POR VEÍCULO
        # ==========================================================

        # Busca todos os itens de manutenção ligados aos veículos.
        cursor.execute("""
            SELECT
                ma.id_veiculo,
                marca.nome,
                ve.modelo,
                im.valor_total
            FROM item_manutencao im
            INNER JOIN manutencao ma ON ma.id_manutencao = im.id_manutencao
            INNER JOIN veiculo ve ON ve.id_veiculo = ma.id_veiculo
            INNER JOIN marca marca ON marca.id_marca = ve.id_marca
        """)
        manutencoes = cursor.fetchall()

        # Esse for agrupa o custo de manutenção por veículo.
        # Se o mesmo veículo tiver 3 itens, ele soma tudo no mesmo veículo.
        for manutencao in manutencoes:
            id_veiculo = manutencao[0]
            veiculo = f'{manutencao[1]} {manutencao[2]}'
            valor_total = float(manutencao[3] or 0)

            if id_veiculo not in manutencao_por_veiculo:
                manutencao_por_veiculo[id_veiculo] = {
                    'id_veiculo': id_veiculo,
                    'veiculo': veiculo,
                    'valor_total': 0
                }

            manutencao_por_veiculo[id_veiculo]['valor_total'] += valor_total

            # Esse segundo dicionário é mais simples.
            # Ele guarda só id_veiculo e total.
            # Vai ser usado depois no cálculo de lucro real.
            if id_veiculo not in manutencao_por_id_veiculo:
                manutencao_por_id_veiculo[id_veiculo] = 0

            manutencao_por_id_veiculo[id_veiculo] += valor_total

        manutencao_por_veiculo_lista = []

        # Transforma manutenção por veículo em lista.
        for chave in manutencao_por_veiculo:
            item = manutencao_por_veiculo[chave]

            manutencao_por_veiculo_lista.append({
                'id_veiculo': item['id_veiculo'],
                'veiculo': item['veiculo'],
                'valor_total': round(item['valor_total'], 2),
                'total_manutencao': round(item['valor_total'], 2)
            })

        # Ordenação sem lambda.
        # O primeiro for escolhe uma posição da lista.
        # O segundo for procura se existe algum item maior depois dela.
        # Se existir, troca os dois de lugar.
        # Resultado: lista fica do maior custo de manutenção para o menor.
        for i in range(len(manutencao_por_veiculo_lista)):
            for j in range(i + 1, len(manutencao_por_veiculo_lista)):
                if manutencao_por_veiculo_lista[j]['valor_total'] > manutencao_por_veiculo_lista[i]['valor_total']:
                    auxiliar = manutencao_por_veiculo_lista[i]
                    manutencao_por_veiculo_lista[i] = manutencao_por_veiculo_lista[j]
                    manutencao_por_veiculo_lista[j] = auxiliar

        # funcao do grafico servicos mais usados
        # ==========================================================
        # SERVIÇOS MAIS USADOS
        # ==========================================================

        # Busca serviços usados nas manutenções.
        cursor.execute("""
            SELECT
                serv.id_servico,
                serv.descricao,
                im.quantidade,
                im.valor_total
            FROM item_manutencao im
            INNER JOIN servico serv ON serv.id_servico = im.id_servico
        """)
        servicos = cursor.fetchall()

        # Esse for agrupa por serviço.
        # Se "Troca de óleo" aparece várias vezes, soma quantidade e valor.
        for servico in servicos:
            id_servico = servico[0]
            descricao = servico[1]
            quantidade = int(servico[2] or 0)
            valor_total = float(servico[3] or 0)

            if id_servico not in servicos_mais_usados:
                servicos_mais_usados[id_servico] = {
                    'id_servico': id_servico,
                    'servico': descricao,
                    'quantidade': 0,
                    'valor_total': 0
                }

            servicos_mais_usados[id_servico]['quantidade'] += quantidade
            servicos_mais_usados[id_servico]['valor_total'] += valor_total

        servicos_mais_usados_lista = []

        # Transforma serviços em lista.
        for chave in servicos_mais_usados:
            item = servicos_mais_usados[chave]

            servicos_mais_usados_lista.append({
                'id_servico': item['id_servico'],
                'servico': item['servico'],
                'descricao': item['servico'],
                'quantidade': item['quantidade'],
                'valor_total': round(item['valor_total'], 2),
                'total': round(item['valor_total'], 2),
                'valor': round(item['valor_total'], 2)
            })

        # Ordenação sem lambda.
        # Aqui organiza do serviço mais usado para o menos usado.
        for i in range(len(servicos_mais_usados_lista)):
            for j in range(i + 1, len(servicos_mais_usados_lista)):
                if servicos_mais_usados_lista[j]['quantidade'] > servicos_mais_usados_lista[i]['quantidade']:
                    auxiliar = servicos_mais_usados_lista[i]
                    servicos_mais_usados_lista[i] = servicos_mais_usados_lista[j]
                    servicos_mais_usados_lista[j] = auxiliar

        # funcao do grafico performance dos vendedores
        # ==========================================================
        # PERFORMANCE DOS VENDEDORES
        # ==========================================================

        # Busca as vendas com vendedor, valor de venda e custo do veículo.
        cursor.execute("""
            SELECT
                vendedor.nome,
                vd.valor_venda,
                ve.preco_custo
            FROM venda vd
            LEFT JOIN usuario vendedor ON vendedor.id_usuario = vd.id_usuario_vendedor
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
        """)
        vendas_vendedores = cursor.fetchall()

        # Esse for agrupa os resultados por vendedor.
        # Para cada vendedor, soma:
        # quantidade de vendas,
        # receita total,
        # lucro bruto.
        for venda in vendas_vendedores:
            vendedor = venda[0] or 'Sem vendedor'
            valor_venda = float(venda[1] or 0)
            preco_custo = float(venda[2] or 0)
            lucro_bruto = valor_venda - preco_custo

            if vendedor not in performance_vendedores:
                performance_vendedores[vendedor] = {
                    'vendedor': vendedor,
                    'nome': vendedor,
                    'quantidade_vendas': 0,
                    'receita_vendas': 0,
                    'lucro_bruto': 0
                }

            performance_vendedores[vendedor]['quantidade_vendas'] += 1
            performance_vendedores[vendedor]['receita_vendas'] += valor_venda
            performance_vendedores[vendedor]['lucro_bruto'] += lucro_bruto

        performance_vendedores_lista = []

        # Transforma performance dos vendedores em lista.
        for chave in performance_vendedores:
            item = performance_vendedores[chave]

            ticket_medio = 0

            if item['quantidade_vendas'] > 0:
                ticket_medio = item['receita_vendas'] / item['quantidade_vendas']

            performance_vendedores_lista.append({
                'vendedor': item['vendedor'],
                'nome': item['nome'],
                'quantidade_vendas': item['quantidade_vendas'],
                'receita_vendas': round(item['receita_vendas'], 2),
                'lucro_bruto': round(item['lucro_bruto'], 2),
                'ticket_medio': round(ticket_medio, 2)
            })

        # Ordenação sem lambda.
        # Organiza vendedores pelo maior lucro bruto.
        for i in range(len(performance_vendedores_lista)):
            for j in range(i + 1, len(performance_vendedores_lista)):
                if performance_vendedores_lista[j]['lucro_bruto'] > performance_vendedores_lista[i]['lucro_bruto']:
                    auxiliar = performance_vendedores_lista[i]
                    performance_vendedores_lista[i] = performance_vendedores_lista[j]
                    performance_vendedores_lista[j] = auxiliar

        # funcao do grafico lucro real por veiculo
        # ==========================================================
        # LUCRO REAL APÓS MANUTENÇÃO
        # ==========================================================

        # Busca veículos vendidos com valor de venda e preço de custo.
        cursor.execute("""
            SELECT
                vd.id_venda,
                ve.id_veiculo,
                marca.nome,
                ve.modelo,
                vd.valor_venda,
                ve.preco_custo
            FROM venda vd
            INNER JOIN veiculo ve ON ve.id_veiculo = vd.id_veiculo
            INNER JOIN marca marca ON marca.id_marca = ve.id_marca
        """)
        vendas_lucro_real = cursor.fetchall()

        # Esse for calcula o lucro real de cada venda.
        # lucro_bruto = valor_venda - preco_custo
        # lucro_real = lucro_bruto - total_manutencao
        for venda in vendas_lucro_real:
            id_venda = venda[0]
            id_veiculo = venda[1]
            marca = venda[2] or 'Sem marca'
            modelo = venda[3] or ''
            nome_veiculo = f'{marca} {modelo}'
            valor_venda = float(venda[4] or 0)
            preco_custo = float(venda[5] or 0)

            total_manutencao = 0

            # Se esse veículo teve manutenção, pega o total.
            # Se não teve, fica 0.
            if id_veiculo in manutencao_por_id_veiculo:
                total_manutencao = manutencao_por_id_veiculo[id_veiculo]

            lucro_bruto = valor_venda - preco_custo
            lucro_real = lucro_bruto - total_manutencao

            lucro_real_veiculos.append({
                'id_veiculo': id_veiculo,
                'id_venda': id_venda,
                'nome': nome_veiculo,
                'veiculo': nome_veiculo,
                'valor_venda': round(valor_venda, 2),
                'preco_custo': round(preco_custo, 2),
                'total_manutencao': round(total_manutencao, 2),
                'lucro_bruto': round(lucro_bruto, 2),
                'lucro_real': round(lucro_real, 2)
            })

        # Ordenação sem lambda.
        # Organiza veículos pelo maior lucro real.
        for i in range(len(lucro_real_veiculos)):
            for j in range(i + 1, len(lucro_real_veiculos)):
                if lucro_real_veiculos[j]['lucro_real'] > lucro_real_veiculos[i]['lucro_real']:
                    auxiliar = lucro_real_veiculos[i]
                    lucro_real_veiculos[i] = lucro_real_veiculos[j]
                    lucro_real_veiculos[j] = auxiliar

        # ==========================================================
        # RETORNO FINAL PARA O FRONT
        # ==========================================================

        return jsonify({
            'financeiro_mensal': financeiro_mensal_lista,
            'vendas_por_forma_pagamento': vendas_por_forma_pagamento_lista,
            'fluxo_recebimentos': fluxo_recebimentos_lista,
            'parcelas_status': parcelas_status_lista,
            'documentacao': documentacao_lista,
            'manutencao_por_veiculo': manutencao_por_veiculo_lista,
            'servicos_mais_usados': servicos_mais_usados_lista,
            'lucro_real_veiculos': lucro_real_veiculos,
            'performance_vendedores': performance_vendedores_lista
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar gráficos: {str(e)}'}), 500

    finally:
        cursor.close()
