from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario, gerar_pix
from datetime import datetime, timedelta
import os


@app.route('/amortizar/<int:id_financiamento>', methods=['PUT'])
def amortizar(id_financiamento):
    # funcao da amortizacao do financiamento
    # funcao da mortizacao do financiamento
    dados = request.get_json()

    tipo_amortizacao = int(dados.get('tipo_amortizacao'))
    valor_amortizado = float(dados.get('valor_amortizado'))

    cursor = con.cursor()

    try:
        # busca os dados do financiamento para amortizar
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

        # conta parcelas abertas antes da amortizacao
        cursor.execute("""
            SELECT COUNT(*)
            FROM item_financiamento
            WHERE id_financiamento = ?
              AND status in(0,3)
        """, (id_financiamento,))

        parcela_restante = cursor.fetchone()[0]

        if parcela_restante == 0:
            return jsonify({'mensagem': 'Não existem parcelas em aberto'}), 400

        # calcula novo saldo devedor depois da amortizacao
        novo_saldo_devedor = saldo_devedor - valor_amortizado

        if novo_saldo_devedor <= 100:
            return jsonify({
                'mensagem': 'Não é possível realizar a amortização, pois o saldo devedor resultante seria inferior a R$ 100,00.'
            }), 400
        juro = porcentagem_juro_financiamento / 100

        # amortizacao tipo 1: mantem a quantidade de parcelas e diminui o valor mensal
        if tipo_amortizacao == 1:
            parcela_mensal_juro_novo = round(float(novo_saldo_devedor * juro / (1 - (1 + juro) ** -parcela_restante)),2)

            novo_valor_financiamento = round(float(parcela_mensal_juro_novo * parcela_restante),2)

            valor_parcela_original = round(float(novo_saldo_devedor/parcela_restante),2)

            # atualiza o valor restante do financiamento
            cursor.execute("""
                UPDATE financiamento
                SET valor_restante_financiamento = ?
                WHERE id_financiamento = ?
            """, ( novo_valor_financiamento, id_financiamento))

            # busca parcelas abertas que vao receber o novo valor
            cursor.execute("""
                SELECT id_item_financiamento, numero_parcela
                FROM item_financiamento
                WHERE id_financiamento = ? 
                AND status in(0,3) ORDER BY numero_parcela 
            """, (id_financiamento,))

            parcelas_abertas = cursor.fetchall()

            # recalcula cada parcela aberta e gera novo pix
            for parcela in parcelas_abertas:
                id_item_financiamento = parcela[0]
                numero_parcela = parcela[1]
                
                cursor.execute("""
                    UPDATE item_financiamento
                    SET valor_parcela = ?, SALDO_DEVEDOR_PARCELA = ?
                    WHERE id_item_financiamento = ?
                """, (parcela_mensal_juro_novo, valor_parcela_original, id_item_financiamento))
                gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa,
                    valor=parcela_mensal_juro_novo,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}"
                )
            
            # ajusta arredondamento das parcelas no banco


            con.commit()

            return jsonify({
                'mensagem': 'Amortização concluída com sucesso'}), 200
        
        # amortizacao tipo 2: diminui a quantidade de parcelas abertas
        if tipo_amortizacao ==2:
            while valor_amortizado > 0:
                if valor_amortizado == 0:
                    break
                # busca a ultima parcela aberta para amortizar de tras para frente
                cursor.execute(""" SELECT FIRST 1 id_item_financiamento, saldo_devedor_parcela, valor_parcela, valor_parcela_original, numero_parcela
                                FROM ITEM_FINANCIAMENTO
                                WHERE ID_FINANCIAMENTO = ? AND status in(0,3)
                                ORDER BY numero_parcela DESC  """, (id_financiamento,))
                item_financiamento = cursor.fetchone()
                id_item_financiamento = item_financiamento[0]
                saldo_parcela_devedor = float(item_financiamento[1])
                valor_parcela = float(item_financiamento[2])
                valor_parcela_original = float(item_financiamento[3])
                numero_parcela = item_financiamento[4]
                

                # se o valor cobre a parcela inteira, baixa essa parcela como amortizada
                if valor_amortizado >= saldo_parcela_devedor:
                    cursor.execute(""" update item_financiamento 
                                   set status = 2, saldo_devedor_parcela = 0 where id_item_financiamento = ? """, 
                                   (id_item_financiamento,))
                    valor_amortizado -= saldo_parcela_devedor
                    
                # se cobre apenas parte da parcela, atualiza o saldo restante dela
                else:
                    valor_restante = float(saldo_parcela_devedor - valor_amortizado)
                    cursor.execute(""" update item_financiamento set status = 3, saldo_devedor_parcela = ?  
                                   where id_item_financiamento = ? """, (valor_restante, id_item_financiamento))
                    
                    valor_amortizado -= saldo_parcela_devedor
                    valor_restante_parcela = round(float((valor_parcela - valor_parcela_original) + valor_restante),2)
                    cursor.execute(""" update item_financiamento set valor_parcela = ?
                                    where id_financiamento = ? and numero_parcela = ? """,
                                   (valor_restante_parcela, id_financiamento, numero_parcela))
                    gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa, 
                    valor=valor_restante_parcela,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}")

            # ajusta arredondamento das parcelas no banco


            con.commit()
                
            return jsonify({'mensagem': 'Amortização concluída com sucesso'}), 200

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