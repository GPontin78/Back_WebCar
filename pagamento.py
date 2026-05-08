from flask import jsonify, request, send_from_directory, send_file
from main import app, con
from funcao import descobre_tipo_usuario, descobre_id_usuario, gerar_pix
from datetime import datetime, timedelta

import os

@app.route('/adicionar_venda', methods=['POST'])
def adicionar_venda():

    dados = request.get_json()

    id_veiculo = int(dados.get('id_veiculo'))
    forma_pagamento = dados.get('forma_pagamento')
    parcela = dados.get('parcela')

    id_usuario_cliente_avista = descobre_id_usuario()

    id_usuario_cliente = int(dados.get('id_usuario_cliente', id_usuario_cliente_avista))

    tipo_usuario = descobre_tipo_usuario()

    if not tipo_usuario:
        return jsonify({'mensagem': 'Usuário não logado'})

    try:

        cursor = con.cursor()

        cursor.execute("""SELECT preco_venda, id_empresa, preco_custo, status, id_marca, modelo FROM veiculo WHERE id_veiculo = ?""", (id_veiculo,))
        veiculo = cursor.fetchone()

        if veiculo is None:
            return jsonify({'mensagem': 'Selecione um veiculo'}), 400
        if not veiculo :
            return jsonify({'mensagem': 'Selecione um veiculo'}), 400

        preco_venda = float(veiculo[0])
        id_empresa_veiculo = veiculo[1]
        status = veiculo[3]
        id_marca = veiculo[4]
        modelo = veiculo[5]

        cursor.execute(""" select nome from marca where id_marca = ?""",(id_marca,))
        marca = cursor.fetchone()
        nome_marca = marca[0]
        print(marca)


        if status == 2:
            return jsonify({'mensagem': 'Este veículo já foi vendido'})

        data_venda = datetime.now()

        cursor.execute("""SELECT desconto_a_vista, porcentagem_juro, chave_pix, nome_fantasia, cidade 
                            FROM empresa 
                            WHERE id_empresa = ?""", (id_empresa_veiculo,))
        empresa = cursor.fetchone()

        desconto_a_vista_banco = float(empresa[0])
        porcentagem_juro_banco = float(empresa[1])

        chave_pix = empresa[2]
        nome_empresa = empresa[3]
        cidade_empresa = empresa[4]

        if forma_pagamento != 0 or 1:
           return jsonify({'mensagem': 'Selecione uma forma de pagamento válida'}), 400


        if forma_pagamento == 0 or tipo_usuario == 2:

            valor_venda_desconto = float(preco_venda - (preco_venda * (desconto_a_vista_banco / 100)))

            cursor.execute("""INSERT INTO venda(id_usuario_cliente, id_veiculo, data_venda, valor_venda, forma_pagamento) VALUES(?,?,?,?,0) RETURNING ID_VENDA""",
                           (id_usuario_cliente_avista, id_veiculo, data_venda, valor_venda_desconto, forma_pagamento))

            id_venda = cursor.fetchone()[0]

            pix = gerar_pix(
                chave=chave_pix,
                nome=nome_empresa,
                cidade=cidade_empresa,
                valor=valor_venda_desconto,
                pasta="avista",
                txid=str(id_venda)
            )

            cursor.execute("""UPDATE veiculo SET status = ? WHERE id_veiculo = ?""", (2, id_veiculo))

            descricao = f'Veículo vendido: {nome_marca} {modelo}'

            cursor.execute("""INSERT INTO receita(id_venda, descricao, valor, data_receita) VALUES(?,?,?,?)""",
                           (id_venda, descricao, valor_venda_desconto, data_venda))

            con.commit()

            return send_file(
                pix['imagem'],
                mimetype='image/png')

        if forma_pagamento == 1 and tipo_usuario == 1:
            valor = preco_venda
            juro = porcentagem_juro_banco / 100
            parcela_mensal_juro = float(valor * juro / (1 - (1 + juro) ** -parcela))
            valor_venda_financiamento = float(parcela_mensal_juro * parcela)

            cursor.execute("""INSERT INTO venda(id_usuario_cliente, id_usuario_vendedor, id_veiculo, data_venda, valor_venda, forma_pagamento)
                              VALUES(?,?,?,?,?,1) RETURNING ID_VENDA""",
                (id_usuario_cliente, descobre_id_usuario(), id_veiculo, data_venda, valor_venda_financiamento,forma_pagamento))

            id_venda = cursor.fetchone()[0]

            for numero_parcela in range(1, parcela + 1):
                data_vencimento = data_venda + timedelta(days=30 * numero_parcela)

                pix = gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa,
                    valor=parcela_mensal_juro,
                    pasta="financiamento",
                    txid=f"V{id_venda}P{numero_parcela}"
                )

                cursor.execute("""INSERT INTO financiamento(id_venda, numero_parcela, valor_parcela, data_vencimento) VALUES(?,?,?,?)""",
                    (id_venda, numero_parcela, parcela_mensal_juro, data_vencimento))

            cursor.execute("""UPDATE veiculo SET status = ? WHERE id_veiculo = ?""", (2, id_veiculo))
            con.commit()
            return jsonify({'mensagem': 'Venda concluída com sucesso'}), 200

    except Exception as e:

        return jsonify({'mensagem': f'Erro ao concluir venda: {str(e)}'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)