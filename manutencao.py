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

@app.route('/adicionar_manutencao', methods=['POST'])
def adicionar_manutencao():
    dados = request.get_json()
    id_veiculo = dados.get('id_veiculo')
    data =  dados.get('data')
    valor_total = float(dados.get('valor_total'))

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute(""" select id_veiculo from veiculo where id_veiculo = ?
        """, (id_veiculo,))
        veiculo= cursor.fetchone()

        if not veiculo:
            return jsonify({'mensagem': 'Veiculo não encontrado',}), 400
        print(data)

        cursor.execute("""insert into manutencao ( id_veiculo, data, valor_total) 
                          values(?,?, ?)""", (veiculo[0], data, valor_total))
        con.commit()
        return jsonify({'mensagem': 'Manutenção cadastrado com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar Manutenção'}), 500
    finally:
        cursor.close()


@app.route('/edicao_manutencao/<int:id_manutencao>', methods=['PUT'])
def edicao_manutencao(id_manutencao):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()

    cursor.execute("""select id_manutencao, id_veiculo, data, valor_total       
                        from manutencao where id_manutencao=?""", (id_manutencao,))
    existe_manutencao = cursor.fetchone()
    if not existe_manutencao:
        return jsonify({'mensagem': 'Não existe manutencao'})
    print('sim')

    dados = request.get_json()
    id_veiculo = dados.get('id_veiculo')
    data = dados.get('data')
    valor_total = float(dados.get('valor_total'))
    try:
        cursor= con.cursor()
        cursor.execute("""update manutencao 
                        set id_veiculo = ? , data = ?, valor_total = ? 
                        where id_manutencao = ?""",
                       (id_veiculo, data, valor_total, id_manutencao))
        con.commit()
        return jsonify({
            'mensagem': 'Manutenção atualizado com sucesso',}), 201
    except Exception as e:
        return jsonify({'mensagem': 'erro ao editar'})
    finally:
        cursor.close()

@app.route('/deletar_manutencao/<int:id_manutencao>', methods=['DELETE'])
def deletar_manutencao(id_manutencao):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_manutencao, id_veiculo, valor_total, data       
                        from manutencao where id_manutencao=?""", (id_manutencao,))
    existe_manutencao = cursor.fetchone()
    if not existe_manutencao:
        return jsonify({'mensagem': 'Não existe manutenção'})
    try:
        cursor = con.cursor()
        cursor.execute("""delete from manutencao where id_manutencao=?""",
                       (id_manutencao,))
        con.commit()
        return jsonify({'mensagem': 'Manutenção deletado com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar manutenção em mais de uma tabela'})
    finally:
        cursor.close()

@app.route('/adicionar_item_manutencao', methods=['POST'])
def adicionar_item_manutencao():
    dados = request.get_json()
    id_servico = dados.get('id_servico')
    id_manutencao =  dados.get('id_manutencao')
    quantidade = int(dados.get('quantidade'))

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute(""" select id_servico, valor_unitario from servico where id_servico=? """,(id_servico, ))
        servico_banco = cursor.fetchone()
        valor_unitario = servico_banco[1]

        valor_multi = float(valor_unitario*quantidade)


        cursor.execute(""" select id_manutencao from manutencao where id_manutencao=?""",(id_manutencao,))
        manutencao_banco = cursor.fetchone()


        cursor.execute("""insert into item_manutencao ( id_manutencao, id_servico, quantidade, valor_total) 
                          values(?,?,?,?) returning id_item_manutencao""", (manutencao_banco[0],servico_banco[0],quantidade, valor_multi))

        con.commit()
        id_item_manutencao = cursor.fetchone()[0]


        cursor.execute("""UPDATE MANUTENCAO SET VALOR_TOTAL = COALESCE(MANUTENCAO.VALOR_TOTAL,0) + (SELECT ITEM_MANUTENCAO.VALOR_TOTAL  
                                                                FROM ITEM_MANUTENCAO
                                                               WHERE ITEM_MANUTENCAO.ID_MANUTENCAO = MANUTENCAO.ID_MANUTENCAO
                                                               AND ITEM_MANUTENCAO.ID_ITEM_MANUTENCAO = ?)
                           WHERE MANUTENCAO.ID_MANUTENCAO  = ? """,(id_item_manutencao,))
        con.commit()
        return jsonify({'mensagem': 'Item de manutencao cadastrado com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar Item Manutenção'}), 500
    finally:
        cursor.close()

