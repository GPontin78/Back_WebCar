from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
import os

@app.route('/adicionar_servico', methods=['POST'])
def adicionar_servico():
    dados = request.get_json()
    descricao = dados.get('descricao')
    valor_unitario = dados.get('valor_unitario')

    tipo_usuario = descobre_tipo_usuario()
    print(tipo_usuario)
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403


    try:
        cursor = con.cursor()
        cursor.execute("""insert into servico(descricao, valor_unitario) 
                          values(?,?)""", (descricao, valor_unitario))
        con.commit()
        return jsonify({'mensagem': 'Serviço cadastrado com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar serviço'}), 500
    finally:
        cursor.close()


