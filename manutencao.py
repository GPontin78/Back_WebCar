from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
import os

@app.route('/adicionar_servico', methods=['POST'])
def adicionar_servico():
    dados = request.get_json()
    descricao = dados.get('descricao')
    valor_unitario =  float(dados.get('valor_unitario'))

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403


    try:
        cursor = con.cursor()
        cursor.execute("""insert into servico (descricao, valor_unitario) 
                          values(?,?)""", (descricao, valor_unitario))
        con.commit()
        return jsonify({'mensagem': 'Serviço cadastrado com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar serviço'}), 500
    finally:
        cursor.close()

@app.route('/edicao_servico/<int:id_servico>', methods=['PUT'])
def edicao_servico(id_servico):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_servico, descricao, valor_unitario       
                        from servico where id_servico=?""", (id_servico,))
    existe_servico = cursor.fetchone()
    if not existe_servico:
        return jsonify({'mensagem': 'Não existe serviço'})

    dados = request.get_json()
    descricao = dados.get('descricao')
    valor_unitario = float(dados.get('valor_unitario'))
    try:
        cursor= con.cursor()
        cursor.execute("""update servico 
                        set descricao = ? , valor_unitario = ? 
                        where id_servico = ?""",
                       (descricao, valor_unitario, id_servico))
        con.commit()
        return jsonify({
            'mensagem': 'Serviço atualizado com sucesso',}), 201
    except Exception as e:
        return jsonify({'mensagem': 'erro ao editar'})



@app.route('/deletar_servico/<int:id_servico>', methods=['DELETE'])
def deletar_servico(id_servico):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_servico, descricao, valor_unitario       
                        from servico where id_servico=?""", (id_servico,))
    existe_servico = cursor.fetchone()
    if not existe_servico:
        return jsonify({'mensagem': 'Não existe serviço'})
    try:
        cursor = con.cursor()
        cursor.execute("""delete from servico where id_servico=?""",
                       (id_servico,))
        con.commit()
        return jsonify({'mensagem': 'Servico deletado com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar servico em mais de uma tabela'})
    finally:
        cursor.close()

@app.route('/buscar_servico', methods=['POST'])
def buscar_servico():
    dados = request.get_json()
    descricao = dados.get('descricao')
    id_servico = dados.get('id_servico')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403
    try:
        cursor = con.cursor()
        lista_servicos = []

        if descricao :
            descricao = descricao.upper()
            cursor.execute("""
                SELECT descricao, valor_unitario
                FROM servico 
                WHERE upper(descricao) LIKE ?
            """, (f'%{descricao}%',))


        elif id_servico:
            cursor.execute("""
                SELECT descricao, valor_unitario
                FROM servico 
                WHERE id_servico = ?
            """, (id_servico,))

        else:
            cursor.execute("""
                SELECT descricao, valor_unitario
                FROM servico
            """)

        servicos = cursor.fetchall()

        for servico in servicos:
            lista_servicos.append({
                'descricao': servico[0],
                'valor_unitario': servico[1]
            })

        if not lista_servicos:
            return jsonify({'mensagem': 'servico não encontrado'}), 404

        return jsonify({'servicos': lista_servicos}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar serviços'}), 500

    finally:
        cursor.close()













