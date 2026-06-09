from flask import jsonify, request
from main import app, con
from funcao import gerar_pix
from datetime import datetime


@app.route('/amortizar/<int:id_financiamento>', methods=['PUT'])
def amortizar(id_financiamento):
    dados = request.get_json()

    tipo_amortizacao = dados.get('tipo_amortizacao')
    valor_amortizado = dados.get('valor_amortizado')

    if not tipo_amortizacao:
        return jsonify({'mensagem': 'Informe o tipo de amortização'}), 400

    if not valor_amortizado:
        return jsonify({'mensagem': 'Informe o valor amortizado'}), 400

    tipo_amortizacao = int(tipo_amortizacao)
    valor_amortizado = round(float(valor_amortizado), 2)

    if tipo_amortizacao != 1 and tipo_amortizacao != 2:
        return jsonify({'mensagem': 'Tipo de amortização inválido'}), 400

    if valor_amortizado <= 0:
        return jsonify({'mensagem': 'Valor amortizado inválido'}), 400

    cursor = con.cursor()

    try:
        cursor.execute("""
            SELECT
                f.saldo_devedor,
                f.porcentagem_juro_financiamento,
                e.chave_pix,
                e.nome_fantasia,
                e.cidade
            FROM financiamento f
            INNER JOIN venda v ON f.id_venda = v.id_venda
            INNER JOIN veiculo ve ON v.id_veiculo = ve.id_veiculo
            INNER JOIN empresa e ON ve.id_empresa = e.id_empresa
            WHERE f.id_financiamento = ?
        """, (id_financiamento,))

        financiamento = cursor.fetchone()

        if not financiamento:
            return jsonify({'mensagem': 'Financiamento não encontrado'}), 404

        saldo_devedor = round(float(financiamento[0] or 0), 2)
        porcentagem_juro_financiamento = round(float(financiamento[1] or 0), 2)
        chave_pix = financiamento[2]
        nome_empresa = financiamento[3]
        cidade_empresa = financiamento[4]

        if saldo_devedor <= 0:
            return jsonify({'mensagem': 'Este financiamento já está quitado'}), 400

        if valor_amortizado > saldo_devedor:
            return jsonify({
                'mensagem': 'O valor amortizado não pode ser maior que o saldo devedor'
            }), 400

        novo_saldo_devedor = round(saldo_devedor - valor_amortizado, 2)
        juro = porcentagem_juro_financiamento / 100

        cursor.execute("""
            SELECT
                id_item_financiamento,
                numero_parcela
            FROM item_financiamento
            WHERE id_financiamento = ?
              AND status IN (0, 3)
            ORDER BY numero_parcela
        """, (id_financiamento,))

        parcelas_abertas = cursor.fetchall()

        if not parcelas_abertas:
            return jsonify({'mensagem': 'Não existem parcelas em aberto'}), 400

        quantidade_parcelas_abertas = len(parcelas_abertas)

        # =====================================================
        # QUITAÇÃO TOTAL
        # =====================================================
        if novo_saldo_devedor == 0:
            data_pagamento = datetime.now().date()

            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]

                cursor.execute("""
                    UPDATE item_financiamento
                    SET
                        valor_parcela = 0,
                        juros_parcela = 0,
                        amortizacao_parcela = 0,
                        saldo_devedor_parcela = 0,
                        status = ?,
                        data_pagamento = ?
                    WHERE id_item_financiamento = ?
                """, (
                    2,
                    data_pagamento,
                    id_item_financiamento
                ))

            cursor.execute("""
                UPDATE financiamento
                SET valor_restante_financiamento = ?
                WHERE id_financiamento = ?
            """, (
                0,
                id_financiamento
            ))

            con.commit()

            return jsonify({
                'mensagem': 'Financiamento quitado com sucesso por amortização',
                'tipo_amortizacao': tipo_amortizacao,
                'valor_amortizado': valor_amortizado,
                'saldo_anterior': saldo_devedor,
                'novo_saldo_devedor': 0,
                'valor_restante_financiamento': 0
            }), 200

        # =====================================================
        # TIPO 1: DIMINUIR VALOR DAS PARCELAS
        # Recalcula a Tabela Price.
        # Aqui sim recalcula juros, amortização e saldo.
        # =====================================================
        if tipo_amortizacao == 1:
            if juro == 0:
                nova_parcela = round(novo_saldo_devedor / quantidade_parcelas_abertas, 2)
            else:
                nova_parcela = round(
                    novo_saldo_devedor * juro / (1 - (1 + juro) ** -quantidade_parcelas_abertas),
                    2
                )

            saldo_recalculo = novo_saldo_devedor
            contador = 1

            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]

                valor_parcela_atual = nova_parcela

                juros_parcela = round(saldo_recalculo * juro, 2)
                amortizacao_parcela = round(valor_parcela_atual - juros_parcela, 2)

                if contador == quantidade_parcelas_abertas:
                    amortizacao_parcela = round(saldo_recalculo, 2)
                    juros_parcela = round(valor_parcela_atual - amortizacao_parcela, 2)
                    saldo_devedor_parcela = 0.00
                else:
                    saldo_devedor_parcela = round(saldo_recalculo - amortizacao_parcela, 2)

                cursor.execute("""
                    UPDATE item_financiamento
                    SET
                        valor_parcela = ?,
                        juros_parcela = ?,
                        amortizacao_parcela = ?,
                        porcentagem_juro_parcela = ?,
                        saldo_devedor_parcela = ?,
                        status = ?,
                        data_pagamento = NULL
                    WHERE id_item_financiamento = ?
                """, (
                    valor_parcela_atual,
                    juros_parcela,
                    amortizacao_parcela,
                    porcentagem_juro_financiamento,
                    saldo_devedor_parcela,
                    0,
                    id_item_financiamento
                ))

                gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa,
                    valor=valor_parcela_atual,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}"
                )

                saldo_recalculo = saldo_devedor_parcela
                contador = contador + 1

            cursor.execute("""
                SELECT valor_parcela
                FROM item_financiamento
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
            """, (id_financiamento,))

            parcelas_soma = cursor.fetchall()

            soma_parcelas = 0

            for parcela_soma in parcelas_soma:
                soma_parcelas = round(soma_parcelas + float(parcela_soma[0] or 0), 2)

            cursor.execute("""
                UPDATE financiamento
                SET valor_restante_financiamento = ?
                WHERE id_financiamento = ?
            """, (
                soma_parcelas,
                id_financiamento
            ))

            con.commit()

            return jsonify({
                'mensagem': 'Amortização concluída com sucesso',
                'tipo_amortizacao': tipo_amortizacao,
                'valor_amortizado': valor_amortizado,
                'saldo_anterior': saldo_devedor,
                'novo_saldo_devedor': novo_saldo_devedor,
                'nova_parcela': nova_parcela,
                'quantidade_parcelas_abertas': quantidade_parcelas_abertas,
                'valor_restante_financiamento': soma_parcelas
            }), 200

        # =====================================================
        # TIPO 2: DIMINUIR QUANTIDADE DE PARCELAS
        # Não recalcula juros.
        # Abate somente da AMORTIZACAO_PARCELA de trás para frente.
        # Juros de parcela quitada por amortização deixam de existir.
        # =====================================================
        if tipo_amortizacao == 2:
            valor_para_amortizar = valor_amortizado
            data_pagamento = datetime.now().date()

            cursor.execute("""
                SELECT
                    id_item_financiamento,
                    numero_parcela,
                    valor_parcela,
                    juros_parcela,
                    amortizacao_parcela
                FROM item_financiamento
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
                ORDER BY numero_parcela DESC
            """, (id_financiamento,))

            parcelas_de_tras_para_frente = cursor.fetchall()

            parcelas_quitadas = 0
            parcela_parcial = None

            for parcela in parcelas_de_tras_para_frente:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]
                juros_parcela = round(float(parcela[3] or 0), 2)
                amortizacao_parcela = round(float(parcela[4] or 0), 2)

                if valor_para_amortizar > 0:
                    if valor_para_amortizar >= amortizacao_parcela:
                        valor_para_amortizar = round(valor_para_amortizar - amortizacao_parcela, 2)

                        cursor.execute("""
                            UPDATE item_financiamento
                            SET
                                valor_parcela = 0,
                                juros_parcela = 0,
                                amortizacao_parcela = 0,
                                saldo_devedor_parcela = 0,
                                status = ?,
                                data_pagamento = ?
                            WHERE id_item_financiamento = ?
                        """, (
                            2,
                            data_pagamento,
                            id_item_financiamento
                        ))

                        parcelas_quitadas = parcelas_quitadas + 1

                    else:
                        nova_amortizacao = round(amortizacao_parcela - valor_para_amortizar, 2)

                        juros_centavos = int(round(juros_parcela * 100))
                        amortizacao_centavos = int(round(nova_amortizacao * 100))
                        novo_valor_parcela = (juros_centavos + amortizacao_centavos) / 100

                        cursor.execute("""
                            UPDATE item_financiamento
                            SET
                                valor_parcela = ?,
                                juros_parcela = ?,
                                amortizacao_parcela = ?,
                                porcentagem_juro_parcela = ?,
                                status = ?,
                                data_pagamento = NULL
                            WHERE id_item_financiamento = ?
                        """, (
                            novo_valor_parcela,
                            juros_parcela,
                            nova_amortizacao,
                            porcentagem_juro_financiamento,
                            3,
                            id_item_financiamento
                        ))

                        parcela_parcial = numero_parcela
                        valor_para_amortizar = 0

            # Depois de abater, recalcula apenas o SALDO_DEVEDOR_PARCELA
            # das parcelas que continuam abertas.
            cursor.execute("""
                SELECT
                    id_item_financiamento,
                    amortizacao_parcela
                FROM item_financiamento
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
                ORDER BY numero_parcela
            """, (id_financiamento,))

            parcelas_restantes = cursor.fetchall()

            saldo_atual = 0

            for parcela in parcelas_restantes:
                saldo_atual = round(saldo_atual + float(parcela[1] or 0), 2)

            for parcela in parcelas_restantes:
                id_item_financiamento = parcela[0]
                amortizacao_parcela = round(float(parcela[1] or 0), 2)

                saldo_atual = round(saldo_atual - amortizacao_parcela, 2)

                if saldo_atual < 0:
                    saldo_atual = 0

                cursor.execute("""
                    UPDATE item_financiamento
                    SET saldo_devedor_parcela = ?
                    WHERE id_item_financiamento = ?
                """, (
                    saldo_atual,
                    id_item_financiamento
                ))

            # Atualiza o valor restante do financiamento:
            # soma das parcelas ainda abertas.
            cursor.execute("""
                SELECT valor_parcela
                FROM item_financiamento
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
            """, (id_financiamento,))

            parcelas_soma = cursor.fetchall()

            soma_parcelas = 0

            for parcela_soma in parcelas_soma:
                soma_parcelas = round(soma_parcelas + float(parcela_soma[0] or 0), 2)

            cursor.execute("""
                UPDATE financiamento
                SET valor_restante_financiamento = ?
                WHERE id_financiamento = ?
            """, (
                soma_parcelas,
                id_financiamento
            ))

            # Gera novo PIX somente para a parcela parcial, se existir.
            if parcela_parcial:
                cursor.execute("""
                    SELECT valor_parcela
                    FROM item_financiamento
                    WHERE id_financiamento = ?
                      AND numero_parcela = ?
                """, (id_financiamento, parcela_parcial))

                parcela_pix = cursor.fetchone()

                if parcela_pix:
                    gerar_pix(
                        chave=chave_pix,
                        nome=nome_empresa,
                        cidade=cidade_empresa,
                        valor=float(parcela_pix[0] or 0),
                        pasta="financiamento",
                        txid=f"F{id_financiamento}P{parcela_parcial}"
                    )

            con.commit()

            return jsonify({
                'mensagem': 'Amortização concluída com sucesso',
                'tipo_amortizacao': tipo_amortizacao,
                'valor_amortizado': valor_amortizado,
                'saldo_anterior': saldo_devedor,
                'novo_saldo_devedor': novo_saldo_devedor,
                'parcelas_quitadas_por_amortizacao': parcelas_quitadas,
                'parcela_parcial': parcela_parcial,
                'valor_restante_financiamento': soma_parcelas
            }), 200

    except Exception as e:
        con.rollback()
        return jsonify({'mensagem': f'Erro ao concluir amortização: {str(e)}'}), 500

    finally:
        cursor.close()