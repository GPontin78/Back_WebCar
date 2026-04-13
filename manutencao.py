from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
from datetime import datetime
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
                          values(?,?)RETURNING ID_servico""", (descricao, valor_unitario))

        id_servico = cursor.fetchone()[0]

        con.commit()
        data_atual= datetime.now()

        cursor.execute("""insert into historico_servico(id_servico, valor_unitario, data_historico)
                        values(?,?)""", (id_servico, valor_unitario, data_atual))
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

    try:
        cursor.execute("""
            select id_servico, descricao, valor_unitario
            from servico
            where id_servico = ?
        """, (id_servico,))
        existe_servico = cursor.fetchone()

        if not existe_servico:
            return jsonify({'mensagem': 'Não existe serviço'}), 404

        valor_antigo = float(existe_servico[2])

        dados = request.get_json()
        descricao = dados.get('descricao')
        valor_unitario = float(dados.get('valor_unitario'))

        cursor.execute("""
            update servico
            set descricao = ?, valor_unitario = ?
            where id_servico = ?
        """, (descricao, valor_unitario, id_servico))

        if valor_antigo != valor_unitario:
            data_atual = datetime.now()

            cursor.execute("""
                insert into historico_servico(id_servico, valor_unitario, data_historico)
                values (?, ?, ?, ?)
            """, (id_servico, valor_unitario, data_atual))

        con.commit()

        return jsonify({'mensagem': 'Serviço atualizado com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao editar serviço: {str(e)}'}), 500

    finally:
        cursor.close()



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
    valor_unitario = dados.get('valor_unitario')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_servicos = []

        if descricao:
            descricao = descricao.upper()
            cursor.execute("""
                SELECT id_servico, descricao, valor_unitario
                FROM servico 
                WHERE upper(descricao) LIKE ?
            """, (f'%{descricao}%',))

        elif id_servico:
            cursor.execute("""
                SELECT id_servico, descricao, valor_unitario
                FROM servico 
                WHERE id_servico = ?
            """, (id_servico,))

        elif valor_unitario:
            valor_unitario = float(valor_unitario)
            cursor.execute("""
                SELECT id_servico, descricao, valor_unitario
                FROM servico 
                WHERE valor_unitario = ?
            """, (valor_unitario,))

        else:
            cursor.execute("""
                SELECT id_servico, descricao, valor_unitario
                FROM servico
            """)

        servicos = cursor.fetchall()

        for servico in servicos:
            id_servico_banco = servico[0]
            descricao_banco = servico[1]
            valor_atual = servico[2]

            cursor.execute("""
                SELECT valor_unitario
                FROM historico_servico
                WHERE id_servico = ?
                ORDER BY data_historico DESC
            """, (id_servico_banco,))

            historico = cursor.fetchone()

            valor_porcentagem = 0

            if historico:
                valor_historico = historico[0]

                if valor_historico != 0:
                    valor_porcentagem = (valor_atual - valor_historico) / valor_historico * 100
                    valor_porcentagem = round(valor_porcentagem, 2)

            lista_servicos.append({
                'descricao': descricao_banco,
                'valor_unitario': valor_atual,
                'valor_porcentagem': valor_porcentagem
            })

        if not lista_servicos:
            return jsonify({'mensagem': 'servico não encontrado'}), 404

        return jsonify({'servicos': lista_servicos}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao listar serviços: {str(e)}'}), 500

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
        data_atual = datetime.now()
        data = datetime.strptime(data, "%Y-%m-%d")
        if data < data_atual:
            return jsonify({'mensagem': 'Não é possível cadastrar manutencao com data retroativa'}), 403

        cursor.execute(""" select id_veiculo from veiculo where id_veiculo = ?
        """, (id_veiculo,))
        veiculo= cursor.fetchone()

        if not veiculo:
            return jsonify({'mensagem': 'Veiculo não encontrado',}), 400
        print(data)

        cursor.execute("""insert into manutencao ( id_veiculo, data, valor_total) 
                          values(?,?, 0)""", (veiculo[0], data, valor_total))
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
        data_atual = datetime.now()
        data = datetime.strptime(data, "%Y-%m-%d")
        if data < data_atual:
            return jsonify({'mensagem': 'Não é possível cadastrar manutencao com data retroativa'}), 403

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

        cursor.execute("""select data from manutencao where id_manutencao = ?""", (id_manutencao,))
        data = cursor.fetchone()
        data_atual = datetime.now()
        data = datetime.strptime(data, "%Y-%m-%d")

        if data < data_atual:
            return jsonify({'mensagem': 'Não é possível cadastrar manutencao com data retroativa'}), 403

        cursor.execute("""delete from manutencao where id_manutencao=?""",
                       (id_manutencao,))
        con.commit()
        return jsonify({'mensagem': 'Manutenção deletado com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar manutenção em mais de uma tabela'})
    finally:
        cursor.close()


@app.route('/buscar_manutencao', methods=['POST'])
def buscar_manutencao():
    dados = request.get_json()
    id_manutencao = dados.get('id_manutencao')
    valor_total = dados.get('valor_total')
    id_veiculo = dados.get('id_veiculo')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403
    try:
        cursor = con.cursor()
        lista_manutenções = []

        if id_veiculo:
            cursor.execute("""
                            SELECT v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME 
                            FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA 
                            WHERE M.ID_VEICULO = ?
            """, (id_veiculo,))

        elif id_manutencao:
            cursor.execute(""" 
                            SELECT v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME 
                            FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA 
                            WHERE M.id_manutencao = ?
            """, (id_manutencao,))

        elif valor_total:
            cursor.execute("""
                           SELECT v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME
                           FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA
                           WHERE M.valor_total = ?
            """, (valor_total,))

        else:
            cursor.execute("""
                            SELECT v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME
                           FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA
            """)

        manutenções = cursor.fetchall()

        for manutenção in manutenções:
            lista_manutenções.append({
                'modelo': manutenção[0],
                'data': manutenção[1],
                'nome': manutenção[3],
                'valor_total': manutenção[2]
            })

        if not lista_manutenções:
            return jsonify({'mensagem': 'manutanção não encontrado'}), 404

        return jsonify({'manutenções': lista_manutenções}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar manutenções'}), 500

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
        id_item_manutencao = cursor.fetchone()[0]

        con.commit()



        cursor.execute("""UPDATE MANUTENCAO SET VALOR_TOTAL = COALESCE(MANUTENCAO.VALOR_TOTAL,0) + (SELECT ITEM_MANUTENCAO.VALOR_TOTAL  
                                                                FROM ITEM_MANUTENCAO
                                                               WHERE ITEM_MANUTENCAO.ID_MANUTENCAO = MANUTENCAO.ID_MANUTENCAO
                                                               AND ITEM_MANUTENCAO.ID_ITEM_MANUTENCAO = ?)
                           WHERE MANUTENCAO.ID_MANUTENCAO  = ? """,(id_item_manutencao, id_manutencao))
        con.commit()
        return jsonify({'mensagem': 'Item de manutencao cadastrado com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar Item Manutenção'}), 500
    finally:
        cursor.close()

from datetime import datetime, timedelta

@app.route('/edicao_item_manutencao/<int:id_item_manutencao>', methods=['PUT'])
def edicao_item_manutencao(id_item_manutencao):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    dados = request.get_json()
    id_servico = dados.get('id_servico')
    quantidade = dados.get('quantidade')

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT im.id_manutencao, im.id_servico, im.quantidade, im.valor_total, m.data
            FROM item_manutencao im
            INNER JOIN manutencao m ON im.id_manutencao = m.id_manutencao
            WHERE im.id_item_manutencao = ?
        """, (id_item_manutencao,))
        item_banco = cursor.fetchone()

        if not item_banco:
            return jsonify({'mensagem': 'Não existe item de manutenção'}), 404

        id_manutencao = item_banco[0]
        id_servico_atual = item_banco[1]
        quantidade_atual = item_banco[2]
        valor_antigo = float(item_banco[3])
        data_manutencao = item_banco[4]

        data_atual = datetime.now().date()
        if data_manutencao < (data_atual - timedelta(days=0)):
            return jsonify({
                'mensagem': 'Não é possível editar item de manutenção, manutenção com data retroativa'
            }), 403

        if id_servico is None:
            id_servico = id_servico_atual

        if quantidade is None:
            quantidade = quantidade_atual

        cursor.execute("""
            SELECT valor_unitario
            FROM servico
            WHERE id_servico = ?
        """, (id_servico,))
        servico_banco = cursor.fetchone()

        if not servico_banco:
            return jsonify({'mensagem': 'Serviço não encontrado'}), 404

        valor_unitario = float(servico_banco[0])
        valor_novo = float(valor_unitario * int(quantidade))

        cursor.execute("""
            UPDATE item_manutencao
            SET id_servico = ?, quantidade = ?, valor_total = ?
            WHERE id_item_manutencao = ?
        """, (id_servico, quantidade, valor_novo, id_item_manutencao))

        cursor.execute("""
            UPDATE manutencao
            SET valor_total = COALESCE(valor_total, 0) - ? + ?
            WHERE id_manutencao = ?
        """, (valor_antigo, valor_novo, id_manutencao))

        con.commit()

        return jsonify({'mensagem': 'Item de manutenção atualizado com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao editar item de manutenção: {str(e)}'}), 500

    finally:
        cursor.close()