from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario, descobre_id_usuario
from datetime import datetime
import os

@app.route('/adicionar_venda', methods=['POST'])
def adicionar_venda():
    dados = request.get_json()
    id_veiculo = int(dados.get('id_veiculo'))
    forma_pagamento = dados.get('forma_pagamento')
    tipo_usuario = descobre_tipo_usuario()

    if not tipo_usuario:
        return jsonify({'mensagem': 'Usuário não logado, faça login'})


    try:
        cursor = con.cursor()
        cursor.execute(""" select preco_venda, id_empresa, preco_custo from veiculo where id_veiculo = ?""",(id_veiculo,))
        veiculo = cursor.fetchone()

        preco_venda = float(veiculo[0])

        id_empresa_veiculo = veiculo[1]
        preco_custo = float(veiculo[2])

        data_venda = datetime.now()

        id_usuario_cliente = descobre_id_usuario()

        cursor.execute(""" select desconto_a_vista from empresa where id_empresa = ?""",(id_empresa_veiculo,))
        empresa = cursor.fetchone()

        desconto_a_vista_banco = float(empresa[0])

        if forma_pagamento == 0 and tipo_usuario == 2 :
            valor_venda_desconto = float(preco_venda-(preco_venda * (desconto_a_vista_banco/100)))
            # if valor_venda_desconto < preco_custo:
            #     return jsonify({'mensagem': 'O valor da venda não pode ser menor que o preco de custo'})

            cursor.execute(""" insert into venda(id_usuario_cliente, id_veiculo, data_venda, valor_venda, forma_pagamento)
                            values(?,?,?,?,0)""", (id_usuario_cliente, id_veiculo, data_venda, valor_venda_desconto, forma_pagamento))
            cursor.execute(""" update veiculo set status = ? where id_veiculo = ?""",(2, id_veiculo))
            con.commit()
            return jsonify({'mensagem': 'Venda concluida com sucesso'})


    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar venda: {str(e)}'}), 500
