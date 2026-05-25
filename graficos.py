from flask import jsonify
from main import app, con
from funcao import descobre_tipo_usuario
from datetime import date


@app.route('/graficos_adm', methods=['GET'])
def graficos_adm():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode acessar os gráficos'}), 403

    cursor = con.cursor()

    try:
        hoje = date.today()
        etapa = "inicio"

        # ==========================================================
        # CONFIGURAÇÕES DA EMPRESA
        # ==========================================================

        etapa = "configuracoes_empresa"

        cursor.execute("""
            SELECT FIRST 1
                PORCENTAGEM_LUCRO,
                PORCENTAGEM_JURO,
                DESCONTO_A_VISTA
            FROM EMPRESA
            ORDER BY ID_EMPRESA
        """)

        empresa = cursor.fetchone()

        porcentagem_lucro = 0
        porcentagem_juro = 0
        desconto_a_vista = 0

        if empresa:
            porcentagem_lucro = float(empresa[0] or 0)
            porcentagem_juro = float(empresa[1] or 0)
            desconto_a_vista = float(empresa[2] or 0)

        # ==========================================================
        # RESUMO GERAL
        # ==========================================================

        etapa = "resumo_qtd_veiculos_total"

        cursor.execute("""
            SELECT COUNT(*)
            FROM VEICULO
        """)
        qtd_veiculos_total = cursor.fetchone()[0] or 0

        etapa = "resumo_qtd_veiculos_estoque"

        cursor.execute("""
            SELECT COUNT(*)
            FROM VEICULO
            WHERE STATUS = 0
        """)
        qtd_veiculos_estoque = cursor.fetchone()[0] or 0

        etapa = "resumo_qtd_vendas"

        cursor.execute("""
            SELECT COUNT(*)
            FROM VENDA
        """)
        qtd_vendas = cursor.fetchone()[0] or 0

        etapa = "resumo_capital_estoque"

        cursor.execute("""
            SELECT PRECO_CUSTO
            FROM VEICULO
            WHERE STATUS = 0
        """)

        valores_capital = cursor.fetchall()
        capital_estoque = 0

        for item in valores_capital:
            capital_estoque += float(item[0] or 0)

        etapa = "resumo_preco_venda_estoque"

        cursor.execute("""
            SELECT PRECO_VENDA
            FROM VEICULO
            WHERE STATUS = 0
        """)

        valores_preco_venda = cursor.fetchall()
        preco_venda_estoque = 0

        for item in valores_preco_venda:
            preco_venda_estoque += float(item[0] or 0)

        etapa = "resumo_receita_vendas"

        cursor.execute("""
            SELECT VALOR_VENDA
            FROM VENDA
        """)

        valores_vendas = cursor.fetchall()
        receita_vendas = 0

        for item in valores_vendas:
            receita_vendas += float(item[0] or 0)

        etapa = "resumo_receita_extra"

        cursor.execute("""
            SELECT VALOR
            FROM RECEITA
            WHERE TABELA IS NULL OR UPPER(TABELA) <> 'VENDA'
        """)

        valores_receitas = cursor.fetchall()
        receita_extra = 0

        for item in valores_receitas:
            receita_extra += float(item[0] or 0)

        etapa = "resumo_despesa_total"

        cursor.execute("""
            SELECT VALOR
            FROM DESPESA
        """)

        valores_despesas = cursor.fetchall()
        despesa_total = 0

        for item in valores_despesas:
            despesa_total += float(item[0] or 0)

        etapa = "resumo_lucro_bruto_vendas"

        cursor.execute("""
            SELECT
                vd.VALOR_VENDA,
                ve.PRECO_CUSTO
            FROM VENDA vd
            JOIN VEICULO ve ON ve.ID_VEICULO = vd.ID_VEICULO
        """)

        valores_lucro = cursor.fetchall()
        lucro_bruto_vendas = 0

        for item in valores_lucro:
            valor_venda = float(item[0] or 0)
            preco_custo = float(item[1] or 0)
            lucro_bruto_vendas += valor_venda - preco_custo

        etapa = "resumo_total_manutencao"

        cursor.execute("""
            SELECT VALOR_TOTAL
            FROM ITEM_MANUTENCAO
        """)

        valores_manutencao = cursor.fetchall()
        total_manutencao = 0

        for item in valores_manutencao:
            total_manutencao += float(item[0] or 0)

        lucro_liquido_estimado = lucro_bruto_vendas + receita_extra - despesa_total - total_manutencao

        ticket_medio = 0

        if qtd_vendas > 0:
            ticket_medio = receita_vendas / qtd_vendas

        etapa = "resumo_qtd_financiamentos"

        cursor.execute("""
            SELECT COUNT(*)
            FROM FINANCIAMENTO
        """)
        qtd_financiamentos = cursor.fetchone()[0] or 0

        etapa = "resumo_total_pago_financiamento"

        cursor.execute("""
            SELECT VALOR_PARCELA
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 1
        """)

        valores_pago_financiamento = cursor.fetchall()
        total_pago_financiamento = 0

        for item in valores_pago_financiamento:
            total_pago_financiamento += float(item[0] or 0)

        etapa = "resumo_total_a_receber_financiamento"

        cursor.execute("""
            SELECT VALOR_PARCELA
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 0
        """)

        valores_a_receber_financiamento = cursor.fetchall()
        total_a_receber_financiamento = 0

        for item in valores_a_receber_financiamento:
            total_a_receber_financiamento += float(item[0] or 0)

        etapa = "resumo_total_parcelas_atrasadas"

        cursor.execute("""
            SELECT VALOR_PARCELA
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 0
            AND DATA_VENCIMENTO < CURRENT_DATE
        """)

        valores_parcelas_atrasadas = cursor.fetchall()
        total_parcelas_atrasadas = 0

        for item in valores_parcelas_atrasadas:
            total_parcelas_atrasadas += float(item[0] or 0)

        etapa = "resumo_qtd_parcelas_pagas"

        cursor.execute("""
            SELECT COUNT(*)
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 1
        """)
        qtd_parcelas_pagas = cursor.fetchone()[0] or 0

        etapa = "resumo_qtd_parcelas_abertas"

        cursor.execute("""
            SELECT COUNT(*)
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 0
        """)
        qtd_parcelas_abertas = cursor.fetchone()[0] or 0

        etapa = "resumo_qtd_parcelas_atrasadas"

        cursor.execute("""
            SELECT COUNT(*)
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 0
            AND DATA_VENCIMENTO < CURRENT_DATE
        """)
        qtd_parcelas_atrasadas = cursor.fetchone()[0] or 0

        inadimplencia_percentual = 0

        if total_a_receber_financiamento > 0:
            inadimplencia_percentual = (total_parcelas_atrasadas / total_a_receber_financiamento) * 100

        etapa = "resumo_documentacao_pendente"

        cursor.execute("""
            SELECT PRECO_CUSTO
            FROM VEICULO
            WHERE STATUS = 0
            AND DOCUMENTACAO = 0
        """)

        valores_doc_pendente = cursor.fetchall()
        capital_documentacao_pendente = 0

        for item in valores_doc_pendente:
            capital_documentacao_pendente += float(item[0] or 0)

        # ==========================================================
        # GRÁFICO FINANCEIRO MENSAL
        # ==========================================================

        financeiro_mensal = {}

        etapa = "financeiro_mensal_vendas"

        cursor.execute("""
            SELECT
                DATA_VENDA,
                VALOR_VENDA
            FROM VENDA
            WHERE DATA_VENDA IS NOT NULL
        """)

        vendas_mes = cursor.fetchall()

        for item in vendas_mes:
            data_venda = item[0]
            valor_venda = float(item[1] or 0)

            ano = data_venda.year
            mes = data_venda.month
            chave = str(ano) + '-' + str(mes).zfill(2)

            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita_vendas': 0,
                    'receita_extra': 0,
                    'despesa': 0,
                    'receita_total': 0,
                    'lucro': 0
                }

            financeiro_mensal[chave]['receita_vendas'] += valor_venda

        etapa = "financeiro_mensal_receitas"

        cursor.execute("""
            SELECT
                DATA_RECEITA,
                VALOR
            FROM RECEITA
            WHERE DATA_RECEITA IS NOT NULL
            AND (TABELA IS NULL OR UPPER(TABELA) <> 'VENDA')
        """)

        receitas_mes = cursor.fetchall()

        for item in receitas_mes:
            data_receita = item[0]
            valor = float(item[1] or 0)

            ano = data_receita.year
            mes = data_receita.month
            chave = str(ano) + '-' + str(mes).zfill(2)

            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita_vendas': 0,
                    'receita_extra': 0,
                    'despesa': 0,
                    'receita_total': 0,
                    'lucro': 0
                }

            financeiro_mensal[chave]['receita_extra'] += valor

        etapa = "financeiro_mensal_despesas"

        cursor.execute("""
            SELECT
                DATA_DESPESA,
                VALOR
            FROM DESPESA
            WHERE DATA_DESPESA IS NOT NULL
        """)

        despesas_mes = cursor.fetchall()

        for item in despesas_mes:
            data_despesa = item[0]
            valor = float(item[1] or 0)

            ano = data_despesa.year
            mes = data_despesa.month
            chave = str(ano) + '-' + str(mes).zfill(2)

            if chave not in financeiro_mensal:
                financeiro_mensal[chave] = {
                    'mes': chave,
                    'receita_vendas': 0,
                    'receita_extra': 0,
                    'despesa': 0,
                    'receita_total': 0,
                    'lucro': 0
                }

            financeiro_mensal[chave]['despesa'] += valor

        financeiro_mensal_lista = []

        for chave in sorted(financeiro_mensal.keys()):
            item = financeiro_mensal[chave]

            item['receita_total'] = item['receita_vendas'] + item['receita_extra']
            item['lucro'] = item['receita_total'] - item['despesa']

            item['receita_vendas'] = round(item['receita_vendas'], 2)
            item['receita_extra'] = round(item['receita_extra'], 2)
            item['despesa'] = round(item['despesa'], 2)
            item['receita_total'] = round(item['receita_total'], 2)
            item['lucro'] = round(item['lucro'], 2)

            financeiro_mensal_lista.append(item)

        # ==========================================================
        # VEÍCULOS: COMPRA X VENDA / PRECIFICAÇÃO / ESTOQUE PARADO
        # ==========================================================

        etapa = "veiculos_compra_venda"

        cursor.execute("""
            SELECT
                v.ID_VEICULO,
                m.NOME,
                v.MODELO,
                v.PRECO_CUSTO,
                v.PRECO_VENDA,
                v.STATUS,
                v.DOCUMENTACAO,
                v.COMBUSTIVEL,
                v.CAMBIO,
                v.DATA_CADASTRO
            FROM VEICULO v
            LEFT JOIN MARCA m ON m.ID_MARCA = v.ID_MARCA
            ORDER BY v.ID_VEICULO
        """)

        veiculos = cursor.fetchall()

        compra_venda_veiculo = []
        precificacao_recomendada = []

        estoque_0_30_qtd = 0
        estoque_31_60_qtd = 0
        estoque_61_90_qtd = 0
        estoque_mais_90_qtd = 0
        estoque_sem_data_qtd = 0

        estoque_0_30_capital = 0
        estoque_31_60_capital = 0
        estoque_61_90_capital = 0
        estoque_mais_90_capital = 0
        estoque_sem_data_capital = 0

        capital_estoque_mais_90_dias = 0
        soma_margem_percentual = 0
        qtd_margem = 0

        for item in veiculos:
            id_veiculo = item[0]
            marca = item[1] or 'Sem marca'
            modelo = item[2] or ''
            preco_custo = float(item[3] or 0)
            preco_venda = float(item[4] or 0)
            status = item[5] or 0
            documentacao = item[6] or 0
            combustivel = item[7]
            cambio = item[8]
            data_cadastro = item[9]

            margem_valor = preco_venda - preco_custo

            margem_percentual = 0

            if preco_custo > 0:
                margem_percentual = (margem_valor / preco_custo) * 100
                soma_margem_percentual += margem_percentual
                qtd_margem += 1

            preco_recomendado = preco_custo + (preco_custo * porcentagem_lucro / 100)
            diferenca = preco_venda - preco_recomendado

            situacao = 'dentro_recomendado'

            if diferenca < -1:
                situacao = 'abaixo_recomendado'

            if diferenca > 1:
                situacao = 'acima_recomendado'

            dias_estoque = None

            if data_cadastro:
                dias_estoque = (hoje - data_cadastro).days

            if status == 0:
                if dias_estoque is None:
                    estoque_sem_data_qtd += 1
                    estoque_sem_data_capital += preco_custo
                elif dias_estoque <= 30:
                    estoque_0_30_qtd += 1
                    estoque_0_30_capital += preco_custo
                elif dias_estoque <= 60:
                    estoque_31_60_qtd += 1
                    estoque_31_60_capital += preco_custo
                elif dias_estoque <= 90:
                    estoque_61_90_qtd += 1
                    estoque_61_90_capital += preco_custo
                else:
                    estoque_mais_90_qtd += 1
                    estoque_mais_90_capital += preco_custo
                    capital_estoque_mais_90_dias += preco_custo

            compra_venda_veiculo.append({
                'id_veiculo': id_veiculo,
                'nome': marca + ' ' + modelo,
                'marca': marca,
                'modelo': modelo,
                'preco_custo': round(preco_custo, 2),
                'preco_venda': round(preco_venda, 2),
                'margem_valor': round(margem_valor, 2),
                'margem_percentual': round(margem_percentual, 2),
                'status': status,
                'documentacao': documentacao,
                'combustivel': combustivel,
                'cambio': cambio,
                'data_cadastro': str(data_cadastro) if data_cadastro else None,
                'dias_estoque': dias_estoque
            })

            precificacao_recomendada.append({
                'id_veiculo': id_veiculo,
                'nome': marca + ' ' + modelo,
                'preco_custo': round(preco_custo, 2),
                'preco_recomendado': round(preco_recomendado, 2),
                'preco_cadastrado': round(preco_venda, 2),
                'diferenca': round(diferenca, 2),
                'situacao': situacao
            })

        margem_media_percentual = 0

        if qtd_margem > 0:
            margem_media_percentual = soma_margem_percentual / qtd_margem

        margem_veiculos_top_lucro = sorted(
            compra_venda_veiculo,
            key=lambda x: x['margem_valor'],
            reverse=True
        )[:10]

        margem_veiculos_top_percentual = sorted(
            compra_venda_veiculo,
            key=lambda x: x['margem_percentual'],
            reverse=True
        )[:10]

        estoque_parado = [
            {
                'faixa': '0-30 dias',
                'quantidade': estoque_0_30_qtd,
                'capital': round(estoque_0_30_capital, 2)
            },
            {
                'faixa': '31-60 dias',
                'quantidade': estoque_31_60_qtd,
                'capital': round(estoque_31_60_capital, 2)
            },
            {
                'faixa': '61-90 dias',
                'quantidade': estoque_61_90_qtd,
                'capital': round(estoque_61_90_capital, 2)
            },
            {
                'faixa': '+90 dias',
                'quantidade': estoque_mais_90_qtd,
                'capital': round(estoque_mais_90_capital, 2)
            },
            {
                'faixa': 'Sem data',
                'quantidade': estoque_sem_data_qtd,
                'capital': round(estoque_sem_data_capital, 2)
            }
        ]

        # ==========================================================
        # ANÁLISE POR MARCA
        # ==========================================================

        etapa = "analise_marcas"

        cursor.execute("""
            SELECT
                m.NOME,
                v.STATUS,
                v.PRECO_CUSTO,
                v.PRECO_VENDA
            FROM VEICULO v
            LEFT JOIN MARCA m ON m.ID_MARCA = v.ID_MARCA
        """)

        marcas_raw = cursor.fetchall()
        marcas_dict = {}

        for item in marcas_raw:
            marca = item[0] or 'Sem marca'
            status = item[1] or 0
            preco_custo = float(item[2] or 0)
            preco_venda = float(item[3] or 0)

            if marca not in marcas_dict:
                marcas_dict[marca] = {
                    'marca': marca,
                    'qtd_total': 0,
                    'qtd_estoque': 0,
                    'capital_estoque': 0,
                    'preco_venda_estoque': 0,
                    'soma_margem': 0,
                    'qtd_margem': 0
                }

            marcas_dict[marca]['qtd_total'] += 1

            if preco_custo > 0:
                marcas_dict[marca]['soma_margem'] += ((preco_venda - preco_custo) / preco_custo) * 100
                marcas_dict[marca]['qtd_margem'] += 1

            if status == 0:
                marcas_dict[marca]['qtd_estoque'] += 1
                marcas_dict[marca]['capital_estoque'] += preco_custo
                marcas_dict[marca]['preco_venda_estoque'] += preco_venda

        analise_marcas = []

        for chave in marcas_dict:
            item = marcas_dict[chave]

            margem_media = 0

            if item['qtd_margem'] > 0:
                margem_media = item['soma_margem'] / item['qtd_margem']

            analise_marcas.append({
                'marca': item['marca'],
                'qtd_total': item['qtd_total'],
                'qtd_estoque': item['qtd_estoque'],
                'capital_estoque': round(item['capital_estoque'], 2),
                'preco_venda_estoque': round(item['preco_venda_estoque'], 2),
                'margem_media_percentual': round(margem_media, 2)
            })

        analise_marcas = sorted(
            analise_marcas,
            key=lambda x: x['capital_estoque'],
            reverse=True
        )

        # ==========================================================
        # VENDAS POR FORMA DE PAGAMENTO
        # ==========================================================

        etapa = "vendas_por_forma_pagamento"

        cursor.execute("""
            SELECT
                FORMA_PAGAMENTO,
                VALOR_VENDA
            FROM VENDA
        """)

        formas_raw = cursor.fetchall()
        formas_dict = {}

        for item in formas_raw:
            forma_pagamento = item[0]
            valor_venda = float(item[1] or 0)

            if forma_pagamento not in formas_dict:
                formas_dict[forma_pagamento] = {
                    'forma_pagamento': forma_pagamento,
                    'quantidade': 0,
                    'valor_total': 0
                }

            formas_dict[forma_pagamento]['quantidade'] += 1
            formas_dict[forma_pagamento]['valor_total'] += valor_venda

        vendas_por_forma_pagamento = []

        for chave in formas_dict:
            item = formas_dict[chave]

            forma_pagamento = item['forma_pagamento']
            nome_forma = 'Não informado'

            if forma_pagamento == 0:
                nome_forma = 'À vista'
            elif forma_pagamento == 1:
                nome_forma = 'Financiado'
            elif forma_pagamento == 2:
                nome_forma = 'Pix'
            elif forma_pagamento == 3:
                nome_forma = 'Cartão'
            elif forma_pagamento == 4:
                nome_forma = 'Boleto'
            elif forma_pagamento is not None:
                nome_forma = 'Forma ' + str(forma_pagamento)

            ticket = 0

            if item['quantidade'] > 0:
                ticket = item['valor_total'] / item['quantidade']

            vendas_por_forma_pagamento.append({
                'forma_pagamento': forma_pagamento,
                'nome': nome_forma,
                'quantidade': item['quantidade'],
                'valor_total': round(item['valor_total'], 2),
                'ticket_medio': round(ticket, 2)
            })

        vendas_por_forma_pagamento = sorted(
            vendas_por_forma_pagamento,
            key=lambda x: x['valor_total'],
            reverse=True
        )

        # ==========================================================
        # PERFORMANCE DOS VENDEDORES
        # ==========================================================

        etapa = "performance_vendedores"

        cursor.execute("""
            SELECT
                u.NOME,
                vd.VALOR_VENDA,
                ve.PRECO_CUSTO
            FROM VENDA vd
            LEFT JOIN USUARIO u ON u.ID_USUARIO = vd.ID_USUARIO_VENDEDOR
            LEFT JOIN VEICULO ve ON ve.ID_VEICULO = vd.ID_VEICULO
        """)

        vendedores_raw = cursor.fetchall()
        vendedores_dict = {}

        for item in vendedores_raw:
            vendedor = item[0] or 'Sem vendedor'
            valor_venda = float(item[1] or 0)
            preco_custo = float(item[2] or 0)
            lucro = valor_venda - preco_custo

            if vendedor not in vendedores_dict:
                vendedores_dict[vendedor] = {
                    'vendedor': vendedor,
                    'quantidade_vendas': 0,
                    'receita_vendas': 0,
                    'lucro_bruto': 0
                }

            vendedores_dict[vendedor]['quantidade_vendas'] += 1
            vendedores_dict[vendedor]['receita_vendas'] += valor_venda
            vendedores_dict[vendedor]['lucro_bruto'] += lucro

        performance_vendedores = []

        for chave in vendedores_dict:
            item = vendedores_dict[chave]
            ticket = 0

            if item['quantidade_vendas'] > 0:
                ticket = item['receita_vendas'] / item['quantidade_vendas']

            performance_vendedores.append({
                'vendedor': item['vendedor'],
                'quantidade_vendas': item['quantidade_vendas'],
                'receita_vendas': round(item['receita_vendas'], 2),
                'lucro_bruto': round(item['lucro_bruto'], 2),
                'ticket_medio': round(ticket, 2)
            })

        performance_vendedores = sorted(
            performance_vendedores,
            key=lambda x: x['lucro_bruto'],
            reverse=True
        )

        # ==========================================================
        # MANUTENÇÃO POR VEÍCULO
        # ==========================================================

        etapa = "manutencao_por_veiculo"

        cursor.execute("""
            SELECT
                ve.ID_VEICULO,
                m.NOME,
                ve.MODELO,
                im.VALOR_TOTAL
            FROM VEICULO ve
            LEFT JOIN MARCA m ON m.ID_MARCA = ve.ID_MARCA
            LEFT JOIN MANUTENCAO ma ON ma.ID_VEICULO = ve.ID_VEICULO
            LEFT JOIN ITEM_MANUTENCAO im ON im.ID_MANUTENCAO = ma.ID_MANUTENCAO
        """)

        manutencoes_raw = cursor.fetchall()
        manutencoes_dict = {}

        for item in manutencoes_raw:
            id_veiculo = item[0]
            marca = item[1] or 'Sem marca'
            modelo = item[2] or ''
            valor_total = float(item[3] or 0)

            if id_veiculo not in manutencoes_dict:
                manutencoes_dict[id_veiculo] = {
                    'id_veiculo': id_veiculo,
                    'nome': marca + ' ' + modelo,
                    'marca': marca,
                    'modelo': modelo,
                    'total_manutencao': 0
                }

            manutencoes_dict[id_veiculo]['total_manutencao'] += valor_total

        manutencao_por_veiculo = []

        for chave in manutencoes_dict:
            item = manutencoes_dict[chave]

            manutencao_por_veiculo.append({
                'id_veiculo': item['id_veiculo'],
                'nome': item['nome'],
                'marca': item['marca'],
                'modelo': item['modelo'],
                'total_manutencao': round(item['total_manutencao'], 2)
            })

        manutencao_por_veiculo = sorted(
            manutencao_por_veiculo,
            key=lambda x: x['total_manutencao'],
            reverse=True
        )

        # ==========================================================
        # SERVIÇOS MAIS USADOS
        # ==========================================================

        etapa = "servicos_mais_usados"

        cursor.execute("""
            SELECT
                s.ID_SERVICO,
                s.DESCRICAO,
                im.QUANTIDADE,
                im.VALOR_TOTAL
            FROM SERVICO s
            LEFT JOIN ITEM_MANUTENCAO im ON im.ID_SERVICO = s.ID_SERVICO
        """)

        servicos_raw = cursor.fetchall()
        servicos_dict = {}

        for item in servicos_raw:
            id_servico = item[0]
            descricao = item[1]
            quantidade = item[2] or 0
            valor_total = float(item[3] or 0)

            if id_servico not in servicos_dict:
                servicos_dict[id_servico] = {
                    'id_servico': id_servico,
                    'descricao': descricao,
                    'quantidade': 0,
                    'total': 0
                }

            servicos_dict[id_servico]['quantidade'] += quantidade
            servicos_dict[id_servico]['total'] += valor_total

        servicos_mais_usados = []

        for chave in servicos_dict:
            item = servicos_dict[chave]

            servicos_mais_usados.append({
                'id_servico': item['id_servico'],
                'descricao': item['descricao'],
                'quantidade': item['quantidade'],
                'total': round(item['total'], 2)
            })

        servicos_mais_usados = sorted(
            servicos_mais_usados,
            key=lambda x: x['quantidade'],
            reverse=True
        )

        # ==========================================================
        # LUCRO REAL POR VEÍCULO VENDIDO
        # ==========================================================

        etapa = "lucro_real_veiculos"

        cursor.execute("""
            SELECT
                vd.ID_VENDA,
                ve.ID_VEICULO,
                m.NOME,
                ve.MODELO,
                vd.VALOR_VENDA,
                ve.PRECO_CUSTO
            FROM VENDA vd
            JOIN VEICULO ve ON ve.ID_VEICULO = vd.ID_VEICULO
            LEFT JOIN MARCA m ON m.ID_MARCA = ve.ID_MARCA
        """)

        vendas_lucro = cursor.fetchall()
        lucro_real_veiculos = []

        for item in vendas_lucro:
            id_venda = item[0]
            id_veiculo = item[1]
            marca = item[2] or 'Sem marca'
            modelo = item[3] or ''
            valor_venda = float(item[4] or 0)
            preco_custo = float(item[5] or 0)

            total_manutencao_veiculo = 0

            if id_veiculo in manutencoes_dict:
                total_manutencao_veiculo = manutencoes_dict[id_veiculo]['total_manutencao']

            lucro_bruto = valor_venda - preco_custo
            lucro_real = lucro_bruto - total_manutencao_veiculo

            lucro_real_veiculos.append({
                'id_venda': id_venda,
                'id_veiculo': id_veiculo,
                'nome': marca + ' ' + modelo,
                'marca': marca,
                'modelo': modelo,
                'valor_venda': round(valor_venda, 2),
                'preco_custo': round(preco_custo, 2),
                'total_manutencao': round(total_manutencao_veiculo, 2),
                'lucro_bruto': round(lucro_bruto, 2),
                'lucro_real': round(lucro_real, 2)
            })

        lucro_real_veiculos = sorted(
            lucro_real_veiculos,
            key=lambda x: x['lucro_real'],
            reverse=True
        )[:10]

        # ==========================================================
        # FLUXO FUTURO DE RECEBIMENTOS
        # ==========================================================

        etapa = "fluxo_recebimentos"

        cursor.execute("""
            SELECT
                DATA_VENCIMENTO,
                VALOR_PARCELA
            FROM ITEM_FINANCIAMENTO
            WHERE STATUS = 0
            AND DATA_VENCIMENTO IS NOT NULL
        """)

        recebimentos_raw = cursor.fetchall()
        recebimentos_dict = {}

        for item in recebimentos_raw:
            data_vencimento = item[0]
            valor_parcela = float(item[1] or 0)

            ano = data_vencimento.year
            mes = data_vencimento.month
            chave = str(ano) + '-' + str(mes).zfill(2)

            if chave not in recebimentos_dict:
                recebimentos_dict[chave] = 0

            recebimentos_dict[chave] += valor_parcela

        fluxo_recebimentos = []

        for chave in sorted(recebimentos_dict.keys()):
            fluxo_recebimentos.append({
                'mes': chave,
                'valor_a_receber': round(recebimentos_dict[chave], 2)
            })

        parcelas_status = [
            {
                'status': 'Pagas',
                'quantidade': qtd_parcelas_pagas,
                'valor': round(total_pago_financiamento, 2)
            },
            {
                'status': 'Em aberto',
                'quantidade': qtd_parcelas_abertas,
                'valor': round(total_a_receber_financiamento, 2)
            },
            {
                'status': 'Atrasadas',
                'quantidade': qtd_parcelas_atrasadas,
                'valor': round(total_parcelas_atrasadas, 2)
            }
        ]

        # ==========================================================
        # FUNIL COMERCIAL SEM RESERVA
        # ==========================================================

        etapa = "funil_comercial"

        funil_comercial = [
            {
                'etapa': 'Veículos cadastrados',
                'quantidade': qtd_veiculos_total
            },
            {
                'etapa': 'Veículos em estoque',
                'quantidade': qtd_veiculos_estoque
            },
            {
                'etapa': 'Vendas realizadas',
                'quantidade': qtd_vendas
            }
        ]

        # ==========================================================
        # DOCUMENTAÇÃO
        # ==========================================================

        etapa = "documentacao"

        cursor.execute("""
            SELECT
                DOCUMENTACAO,
                PRECO_CUSTO
            FROM VEICULO
            WHERE STATUS = 0
        """)

        docs_raw = cursor.fetchall()
        docs_dict = {}

        for item in docs_raw:
            status_doc = item[0]
            preco_custo = float(item[1] or 0)

            if status_doc not in docs_dict:
                docs_dict[status_doc] = {
                    'status': status_doc,
                    'quantidade': 0,
                    'capital': 0
                }

            docs_dict[status_doc]['quantidade'] += 1
            docs_dict[status_doc]['capital'] += preco_custo

        documentacao = []

        for chave in docs_dict:
            item = docs_dict[chave]
            status_doc = item['status']
            nome_doc = 'Não informado'

            if status_doc == 0:
                nome_doc = 'Pendente'
            elif status_doc == 1:
                nome_doc = 'Regularizada'
            elif status_doc is not None:
                nome_doc = 'Status ' + str(status_doc)

            documentacao.append({
                'status': status_doc,
                'nome': nome_doc,
                'quantidade': item['quantidade'],
                'capital': round(item['capital'], 2)
            })

        # ==========================================================
        # COMBUSTÍVEL
        # ==========================================================

        etapa = "analise_combustivel"

        cursor.execute("""
            SELECT
                COMBUSTIVEL,
                PRECO_CUSTO,
                PRECO_VENDA
            FROM VEICULO
        """)

        combustiveis_raw = cursor.fetchall()
        combustivel_dict = {}

        for item in combustiveis_raw:
            combustivel = str(item[0]) if item[0] is not None else 'Não informado'
            preco_custo = float(item[1] or 0)
            preco_venda = float(item[2] or 0)

            if combustivel not in combustivel_dict:
                combustivel_dict[combustivel] = {
                    'combustivel': combustivel,
                    'quantidade': 0,
                    'soma_margem': 0,
                    'qtd_margem': 0
                }

            combustivel_dict[combustivel]['quantidade'] += 1

            if preco_custo > 0:
                combustivel_dict[combustivel]['soma_margem'] += ((preco_venda - preco_custo) / preco_custo) * 100
                combustivel_dict[combustivel]['qtd_margem'] += 1

        analise_combustivel = []

        for chave in combustivel_dict:
            item = combustivel_dict[chave]
            margem_media = 0

            if item['qtd_margem'] > 0:
                margem_media = item['soma_margem'] / item['qtd_margem']

            analise_combustivel.append({
                'combustivel': item['combustivel'],
                'quantidade': item['quantidade'],
                'margem_media': round(margem_media, 2)
            })

        # ==========================================================
        # CÂMBIO
        # ==========================================================

        etapa = "analise_cambio"

        cursor.execute("""
            SELECT
                CAMBIO,
                PRECO_CUSTO,
                PRECO_VENDA
            FROM VEICULO
        """)

        cambios_raw = cursor.fetchall()
        cambio_dict = {}

        for item in cambios_raw:
            cambio = str(item[0]) if item[0] is not None else 'Não informado'
            preco_custo = float(item[1] or 0)
            preco_venda = float(item[2] or 0)

            if cambio not in cambio_dict:
                cambio_dict[cambio] = {
                    'cambio': cambio,
                    'quantidade': 0,
                    'soma_margem': 0,
                    'qtd_margem': 0
                }

            cambio_dict[cambio]['quantidade'] += 1

            if preco_custo > 0:
                cambio_dict[cambio]['soma_margem'] += ((preco_venda - preco_custo) / preco_custo) * 100
                cambio_dict[cambio]['qtd_margem'] += 1

        analise_cambio = []

        for chave in cambio_dict:
            item = cambio_dict[chave]
            margem_media = 0

            if item['qtd_margem'] > 0:
                margem_media = item['soma_margem'] / item['qtd_margem']

            analise_cambio.append({
                'cambio': item['cambio'],
                'quantidade': item['quantidade'],
                'margem_media': round(margem_media, 2)
            })

        # ==========================================================
        # CURVA ABC DO ESTOQUE
        # ==========================================================

        etapa = "curva_abc"

        veiculos_abc = []

        for item in compra_venda_veiculo:
            if item['status'] == 0:
                veiculos_abc.append({
                    'id_veiculo': item['id_veiculo'],
                    'nome': item['nome'],
                    'preco_custo': item['preco_custo']
                })

        veiculos_abc = sorted(
            veiculos_abc,
            key=lambda x: x['preco_custo'],
            reverse=True
        )

        curva_abc = []
        acumulado = 0

        for item in veiculos_abc:
            id_veiculo = item['id_veiculo']
            nome = item['nome']
            preco_custo = float(item['preco_custo'] or 0)

            participacao = 0

            if capital_estoque > 0:
                participacao = (preco_custo / capital_estoque) * 100

            acumulado += participacao

            classe = 'C'

            if acumulado <= 80:
                classe = 'A'
            elif acumulado <= 95:
                classe = 'B'

            curva_abc.append({
                'id_veiculo': id_veiculo,
                'nome': nome,
                'preco_custo': round(preco_custo, 2),
                'participacao_percentual': round(participacao, 2),
                'participacao_acumulada': round(acumulado, 2),
                'classe': classe
            })

        # ==========================================================
        # RELATÓRIO DE VENDAS
        # ==========================================================

        etapa = "relatorio_vendas"

        cursor.execute("""
            SELECT
                vd.ID_VENDA,
                vd.DATA_VENDA,
                vd.VALOR_VENDA,
                vd.FORMA_PAGAMENTO,
                vendedor.NOME,
                cliente.NOME,
                m.NOME,
                ve.MODELO,
                ve.PRECO_CUSTO
            FROM VENDA vd
            LEFT JOIN USUARIO vendedor ON vendedor.ID_USUARIO = vd.ID_USUARIO_VENDEDOR
            LEFT JOIN USUARIO cliente ON cliente.ID_USUARIO = vd.ID_USUARIO_CLIENTE
            LEFT JOIN VEICULO ve ON ve.ID_VEICULO = vd.ID_VEICULO
            LEFT JOIN MARCA m ON m.ID_MARCA = ve.ID_MARCA
            ORDER BY vd.DATA_VENDA DESC
        """)

        vendas = cursor.fetchall()
        relatorio_vendas = []

        for item in vendas:
            valor_venda = float(item[2] or 0)
            preco_custo = float(item[8] or 0)
            lucro = valor_venda - preco_custo

            marca = item[6] or 'Sem marca'
            modelo = item[7] or ''

            relatorio_vendas.append({
                'id_venda': item[0],
                'data_venda': str(item[1]) if item[1] else None,
                'valor_venda': round(valor_venda, 2),
                'forma_pagamento': item[3],
                'vendedor': item[4] or 'Sem vendedor',
                'cliente': item[5] or 'Sem cliente',
                'veiculo': marca + ' ' + modelo,
                'preco_custo': round(preco_custo, 2),
                'lucro_bruto': round(lucro, 2)
            })

        # ==========================================================
        # RELATÓRIO DE FINANCIAMENTOS
        # ==========================================================

        etapa = "relatorio_financiamentos"

        cursor.execute("""
            SELECT
                f.ID_FINANCIAMENTO,
                f.ID_VENDA,
                f.DATA_FINANCIAMENTO,
                f.VALOR_VENDA,
                f.VALOR_VENDA_FINANCIAMENTO,
                c.NOME,
                m.NOME,
                ve.MODELO
            FROM FINANCIAMENTO f
            LEFT JOIN VENDA vd ON vd.ID_VENDA = f.ID_VENDA
            LEFT JOIN USUARIO c ON c.ID_USUARIO = vd.ID_USUARIO_CLIENTE
            LEFT JOIN VEICULO ve ON ve.ID_VEICULO = vd.ID_VEICULO
            LEFT JOIN MARCA m ON m.ID_MARCA = ve.ID_MARCA
            ORDER BY f.DATA_FINANCIAMENTO DESC
        """)

        financs = cursor.fetchall()
        relatorio_financiamentos = []

        for item in financs:
            marca = item[6] or 'Sem marca'
            modelo = item[7] or ''

            relatorio_financiamentos.append({
                'id_financiamento': item[0],
                'id_venda': item[1],
                'data_financiamento': str(item[2]) if item[2] else None,
                'valor_original': round(float(item[3] or 0), 2),
                'valor_total_financiado': round(float(item[4] or 0), 2),
                'cliente': item[5] or 'Sem cliente',
                'veiculo': marca + ' ' + modelo
            })

        # ==========================================================
        # RESPOSTA FINAL
        # ==========================================================

        etapa = "resposta_final"

        return jsonify({
            'parametros_empresa': {
                'porcentagem_lucro': round(porcentagem_lucro, 2),
                'porcentagem_juro': round(porcentagem_juro, 2),
                'desconto_a_vista': round(desconto_a_vista, 2)
            },
            'resumo': {
                'qtd_veiculos_total': qtd_veiculos_total,
                'qtd_veiculos_estoque': qtd_veiculos_estoque,
                'qtd_vendas': qtd_vendas,
                'qtd_financiamentos': qtd_financiamentos,

                'capital_estoque': round(capital_estoque, 2),
                'preco_venda_estoque': round(preco_venda_estoque, 2),

                'receita_vendas': round(receita_vendas, 2),
                'receita_extra': round(receita_extra, 2),
                'receita_total_gerencial': round(receita_vendas + receita_extra, 2),
                'despesa_total': round(despesa_total, 2),

                'lucro_bruto_vendas': round(lucro_bruto_vendas, 2),
                'total_manutencao': round(total_manutencao, 2),
                'lucro_liquido_estimado': round(lucro_liquido_estimado, 2),

                'ticket_medio': round(ticket_medio, 2),
                'margem_media_percentual': round(margem_media_percentual, 2),

                'total_pago_financiamento': round(total_pago_financiamento, 2),
                'total_a_receber_financiamento': round(total_a_receber_financiamento, 2),
                'total_parcelas_atrasadas': round(total_parcelas_atrasadas, 2),
                'qtd_parcelas_pagas': qtd_parcelas_pagas,
                'qtd_parcelas_abertas': qtd_parcelas_abertas,
                'qtd_parcelas_atrasadas': qtd_parcelas_atrasadas,
                'inadimplencia_percentual': round(inadimplencia_percentual, 2),

                'capital_documentacao_pendente': round(capital_documentacao_pendente, 2),
                'capital_estoque_mais_90_dias': round(capital_estoque_mais_90_dias, 2)
            },
            'graficos': {
                'financeiro_mensal': financeiro_mensal_lista,
                'compra_venda_veiculo': compra_venda_veiculo,
                'margem_veiculos_top_lucro': margem_veiculos_top_lucro,
                'margem_veiculos_top_percentual': margem_veiculos_top_percentual,
                'precificacao_recomendada': precificacao_recomendada,
                'estoque_parado': estoque_parado,
                'analise_marcas': analise_marcas,
                'vendas_por_forma_pagamento': vendas_por_forma_pagamento,
                'performance_vendedores': performance_vendedores,
                'manutencao_por_veiculo': manutencao_por_veiculo[:10],
                'servicos_mais_usados': servicos_mais_usados[:10],
                'lucro_real_veiculos': lucro_real_veiculos,
                'fluxo_recebimentos': fluxo_recebimentos,
                'parcelas_status': parcelas_status,
                'funil_comercial': funil_comercial,
                'documentacao': documentacao,
                'analise_combustivel': analise_combustivel,
                'analise_cambio': analise_cambio,
                'curva_abc': curva_abc
            },
            'relatorios': {
                'vendas': relatorio_vendas,
                'financiamentos': relatorio_financiamentos,
                'veiculos': compra_venda_veiculo,
                'manutencao_por_veiculo': manutencao_por_veiculo,
                'servicos_mais_usados': servicos_mais_usados
            }
        }), 200

    except Exception as e:
        print("ERRO GRAFICOS ADM NA ETAPA:", etapa)
        print("ERRO:", e)

        return jsonify({
            'mensagem': 'Erro ao carregar gráficos',
            'etapa': etapa,
            'erro': str(e)
        }), 500

    finally:
        cursor.close()