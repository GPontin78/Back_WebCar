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
              AND status in(0,3)
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

            valor_parcela_original = round(float(novo_saldo_devedor/parcela_restante),2)

            cursor.execute("""
                UPDATE financiamento
                SET valor_restante_financiamento = ?
                WHERE id_financiamento = ?
            """, ( novo_valor_financiamento, id_financiamento))

            cursor.execute("""
                SELECT id_item_financiamento, numero_parcela
                FROM item_financiamento
                WHERE id_financiamento = ? 
                AND status in(0,3) ORDER BY numero_parcela 
            """, (id_financiamento,))

            parcelas_abertas = cursor.fetchall()

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
            
            cursor.execute("""
                EXECUTE PROCEDURE SP_AJUSTA_ARREDONDAMENTO(?)
            """, (id_financiamento,))


            con.commit()

            return jsonify({
                'mensagem': 'Amortização concluída com sucesso'}), 200
        
        if tipo_amortizacao ==2:
            while valor_amortizado > 0:
                if valor_amortizado == 0:
                    break
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
                

                if valor_amortizado >= saldo_parcela_devedor:
                    cursor.execute(""" update item_financiamento 
                                   set status = 2, saldo_devedor_parcela = 0 where id_item_financiamento = ? """, 
                                   (id_item_financiamento,))
                    valor_amortizado -= saldo_parcela_devedor
                    
                else:
                    valor_restante = float(saldo_parcela_devedor - valor_amortizado)
                    cursor.execute(""" update item_financiamento set status = 3, saldo_devedor_parcela = ?  
                                   where id_item_financiamento = ? """, (valor_restante, id_item_financiamento))
                    
                    valor_amortizado -= saldo_parcela_devedor
                    valor_restante_parcela = round(float((valor_parcela - valor_parcela_original) + valor_restante),2)
                    gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa, 
                    valor=valor_restante_parcela,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}")

            cursor.execute("""
                EXECUTE PROCEDURE SP_AJUSTA_ARREDONDAMENTO(?)
            """, (id_financiamento,))

            con.commit()
                
            return jsonify({'mensagem': 'Amortização concluída com sucesso'}), 200

    except Exception as e:
        con.rollback()
        return jsonify({'mensagem': f'Erro ao concluir amortização: {str(e)}'}), 500

    finally:
        cursor.close()