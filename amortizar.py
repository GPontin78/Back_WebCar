from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario, gerar_pix
from datetime import datetime, timedelta
import os


@app.route('/amortizar/<int:id_financiamento>', methods=['PUT'])
def amortizar(id_financiamento):
    dados = request.get_json()

    tipo_amortizacao = int(dados.get('tipo_amortizacao'))
    valor_amortizado = float(dados.get('valor_amortizado'))

    cursor = con.cursor()

    try:
        cursor.execute("""
            SELECT f.saldo_devedor,f.porcentagem_juro_financiamento,e.chave_pix,e.nome_fantasia, e.cidade
            FROM financiamento f
            INNER JOIN venda v ON f.id_venda = v.id_venda
            INNER JOIN veiculo ve ON v.id_veiculo = ve.id_veiculo
            INNER JOIN empresa e ON ve.id_empresa = e.id_empresa
            WHERE f.id_financiamento = ?
        """, (id_financiamento,))

        financiamento = cursor.fetchone()

        if not financiamento:
            return jsonify({'mensagem': 'Financiamento não encontrado'}), 404

        saldo_devedor = float(financiamento[0])
        porcentagem_juro_financiamento = float(financiamento[1])
        chave_pix = financiamento[2]
        nome_empresa = financiamento[3]
        cidade_empresa = financiamento[4]

        cursor.execute("""
            SELECT COUNT(*)
            FROM item_financiamento
            WHERE id_financiamento = ?
              AND status = 0
        """, (id_financiamento,))

        parcela_restante = cursor.fetchone()[0]

        if parcela_restante == 0:
            return jsonify({'mensagem': 'Não existem parcelas em aberto'}), 400

        novo_saldo_devedor = saldo_devedor - valor_amortizado

        if novo_saldo_devedor <= 0:
            return jsonify({'mensagem': 'Valor amortizado não pode ser maior ou igual ao saldo devedor'}), 400

        juro = porcentagem_juro_financiamento / 100

        if tipo_amortizacao == 1:
            parcela_mensal_juro_novo = round(float(novo_saldo_devedor * juro / (1 - (1 + juro) ** -parcela_restante)),2)

            novo_valor_financiamento = round(float(parcela_mensal_juro_novo * parcela_restante),2)

            cursor.execute("""
                UPDATE financiamento
                SET saldo_devedor = ?,
                    valor_venda_financiamento = ?
                WHERE id_financiamento = ?
            """, (novo_saldo_devedor, novo_valor_financiamento, id_financiamento))

            cursor.execute("""
                SELECT id_item_financiamento, numero_parcela
                FROM item_financiamento
                WHERE id_financiamento = ? AND status = 0 ORDER BY numero_parcela
            """, (id_financiamento,))

            parcelas_abertas = cursor.fetchall()

            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]

                gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa,
                    valor=parcela_mensal_juro_novo,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}"
                )

                cursor.execute("""
                    UPDATE item_financiamento
                    SET valor_parcela = ?
                    WHERE id_item_financiamento = ?
                """, (parcela_mensal_juro_novo,id_item_financiamento))

            con.commit()

            return jsonify({
                'mensagem': 'Amortização concluída com sucesso'}), 200


    except Exception as e:
        con.rollback()
        return jsonify({'mensagem': f'Erro ao concluir amortização: {str(e)}'}), 500

    finally:
        cursor.close()