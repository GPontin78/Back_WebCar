from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario, gerar_pix
from datetime import datetime


from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario, gerar_pix
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
        # Se o valor amortizado for igual ao saldo devedor,
        # todas as parcelas abertas viram status 2.
        # 2 = pago por amortização
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
        # TIPO 1: REDUZIR VALOR DAS PARCELAS
        # Mantém a quantidade de parcelas abertas.
        # Recalcula a Price com o novo saldo devedor.
        # =====================================================
        if tipo_amortizacao == 1:
            if juro == 0:
                parcela_mensal_juro_novo = round(
                    novo_saldo_devedor / quantidade_parcelas_abertas,
                    2
                )
            else:
                parcela_mensal_juro_novo = round(
                    novo_saldo_devedor * juro / (1 - (1 + juro) ** -quantidade_parcelas_abertas),
                    2
                )

            saldo_recalculo = novo_saldo_devedor
            contador = 1

            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]

                valor_parcela_atual = parcela_mensal_juro_novo

                juros_parcela = round(saldo_recalculo * juro, 2)
                amortizacao_parcela = round(valor_parcela_atual - juros_parcela, 2)

                if contador == quantidade_parcelas_abertas:
                    amortizacao_parcela = round(saldo_recalculo, 2)
                    juros_parcela = round(valor_parcela_atual - amortizacao_parcela, 2)

                    juros_centavos = int(round(juros_parcela * 100))
                    amortizacao_centavos = int(round(amortizacao_parcela * 100))
                    valor_parcela_atual = (juros_centavos + amortizacao_centavos) / 100

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

            # Garante que valor_parcela = juros_parcela + amortizacao_parcela
            cursor.execute("""
                UPDATE item_financiamento
                SET valor_parcela = juros_parcela + amortizacao_parcela
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
            """, (id_financiamento,))

            # Soma no Python para evitar erro do Firebird com SUM/COALESCE
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
                'nova_parcela': parcela_mensal_juro_novo,
                'quantidade_parcelas_abertas': quantidade_parcelas_abertas,
                'valor_restante_financiamento': soma_parcelas
            }), 200

        # =====================================================
        # TIPO 2: REDUZIR QUANTIDADE DE PARCELAS
        # Mantém o valor da parcela atual.
        # Recalcula até quitar o novo saldo.
        # Parcelas que sobrarem viram status 2.
        # =====================================================
        if tipo_amortizacao == 2:
            cursor.execute("""
                SELECT FIRST 1 valor_parcela
                FROM item_financiamento
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
                ORDER BY numero_parcela
            """, (id_financiamento,))

            parcela_base_banco = cursor.fetchone()

            if not parcela_base_banco:
                return jsonify({'mensagem': 'Não foi possível encontrar parcela base'}), 400

            parcela_base = round(float(parcela_base_banco[0] or 0), 2)

            if parcela_base <= 0:
                return jsonify({'mensagem': 'Valor da parcela base inválido'}), 400

            saldo_recalculo = novo_saldo_devedor
            parcelas_ativas = 0
            data_pagamento = datetime.now().date()

            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]

                if saldo_recalculo > 0:
                    juros_parcela = round(saldo_recalculo * juro, 2)
                    amortizacao_para_quitar = round(saldo_recalculo, 2)

                    juros_centavos = int(round(juros_parcela * 100))
                    amortizacao_centavos = int(round(amortizacao_para_quitar * 100))
                    valor_para_quitar = (juros_centavos + amortizacao_centavos) / 100

                    if valor_para_quitar <= parcela_base:
                        amortizacao_parcela = amortizacao_para_quitar

                        juros_centavos = int(round(juros_parcela * 100))
                        amortizacao_centavos = int(round(amortizacao_parcela * 100))
                        valor_parcela_atual = (juros_centavos + amortizacao_centavos) / 100

                        saldo_devedor_parcela = 0.00

                        if valor_parcela_atual < parcela_base:
                            status_parcela = 3
                        else:
                            status_parcela = 0
                    else:
                        valor_parcela_atual = parcela_base
                        amortizacao_parcela = round(valor_parcela_atual - juros_parcela, 2)
                        saldo_devedor_parcela = round(saldo_recalculo - amortizacao_parcela, 2)
                        status_parcela = 0

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
                        status_parcela,
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

                    parcelas_ativas = parcelas_ativas + 1
                    saldo_recalculo = saldo_devedor_parcela

                else:
                    cursor.execute("""
                        UPDATE item_financiamento
                        SET
                            valor_parcela = 0,
                            juros_parcela = 0,
                            amortizacao_parcela = 0,
                            porcentagem_juro_parcela = ?,
                            saldo_devedor_parcela = 0,
                            status = ?,
                            data_pagamento = ?
                        WHERE id_item_financiamento = ?
                    """, (
                        porcentagem_juro_financiamento,
                        2,
                        data_pagamento,
                        id_item_financiamento
                    ))

            # Garante que valor_parcela = juros_parcela + amortizacao_parcela
            cursor.execute("""
                UPDATE item_financiamento
                SET valor_parcela = juros_parcela + amortizacao_parcela
                WHERE id_financiamento = ?
                  AND status IN (0, 3)
            """, (id_financiamento,))

            # Soma no Python para evitar erro do Firebird com SUM/COALESCE
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
                'parcela_base': parcela_base,
                'parcelas_ativas': parcelas_ativas,
                'parcelas_quitadas_por_amortizacao': quantidade_parcelas_abertas - parcelas_ativas,
                'valor_restante_financiamento': soma_parcelas
            }), 200

    except Exception as e:
        con.rollback()
        return jsonify({'mensagem': f'Erro ao concluir amortização: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route('/saldo_devedor/<int:id_financiamento>', methods=['GET'])
def saldo_devedor(id_financiamento):
    cursor = con.cursor()

    try:
        cursor.execute("""
            SELECT saldo_devedor
            FROM financiamento
            WHERE id_financiamento = ?
        """, (id_financiamento,))

        financiamento = cursor.fetchone()

        if not financiamento:
            return jsonify({'mensagem': 'Financiamento não encontrado'}), 404

        return jsonify({
            'id_financiamento': id_financiamento,
            'saldo_devedor': float(financiamento[0] or 0)
        }), 200

    except Exception as e:
        return jsonify({
            'mensagem': f'Erro ao buscar saldo devedor: {str(e)}'
        }), 500

    finally:
        cursor.close()
