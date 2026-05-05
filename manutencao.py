from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
from datetime import datetime
import os

@app.route('/adicionar_servico', methods=['POST'])
def adicionar_servico():
    dados = request.get_json()
    descricao = dados.get('descricao').capitalize()
    valor_unitario =  float(dados.get('valor_unitario'))

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403


    try:
        cursor = con.cursor()

        cursor.execute("""select 1 from servico where descricao = ?""",(descricao,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Serviço já existe', }), 400

        if not descricao:
            return jsonify({'mensagem': 'Digite uma descrição', }), 400
        if not valor_unitario:
            return jsonify({'mensagem': 'Digite um valor', }), 400

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
    print(id_servico)
    print("1")

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403
    print("2")
    cursor = con.cursor()

    try:
        cursor.execute("""
            select id_servico, descricao, valor_unitario
            from servico
            where id_servico = ?
        """, (id_servico,))
        existe_servico = cursor.fetchone()

        print("3")

        print(existe_servico)
        if not existe_servico:
            return jsonify({'mensagem': 'Não existe serviço'}), 404

        print('3.3')

        valor_antigo = existe_servico[2]
        print('3.4')

        dados = request.get_json()
        descricao = dados.get('descricao', existe_servico[1]).title()
        valor_unitario = float(dados.get('valor_unitario', existe_servico[2]))
        print(descricao)
        print(valor_unitario)
        print("4")

        cursor.execute("""select descricao from servico where descricao = ?""", (descricao,))

        descricao_banco = cursor.fetchone()[0]

        print("5")

        if descricao_banco != descricao:
            cursor.execute("""select 1 from servico where descricao = ?""", (descricao,))
            if cursor.fetchone():
                return jsonify({'mensagem': 'Serviço já existe', }), 200

        print("6")

        cursor.execute("""
            update servico
            set descricao = ?, valor_unitario = ?
            where id_servico = ? 
        """, (descricao, valor_unitario, id_servico))

        print("7")

        if valor_antigo != valor_unitario:
            data_atual = datetime.now()
            print("8")
            cursor.execute("""
                insert into historico_servico(id_servico, valor_unitario, data_historico)
                values (?, ?, ?)
            """, (id_servico, valor_antigo, data_atual))
            print("9")
            con.commit()
            print("10")
        con.commit()
        print("11")

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
                'id_servico': id_servico_banco,
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

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        data_atual = datetime.now().date()
        data = datetime.strptime(data, "%d/%m/%Y").date()

        if data < data_atual:
            return jsonify({
                'mensagem': 'Não é possível cadastrar manutencao com data retroativa'
            }), 403

        cursor.execute(""" select id_veiculo from veiculo where id_veiculo = ?
        """, (id_veiculo,))
        veiculo= cursor.fetchone()

        if not veiculo:
            return jsonify({'mensagem': 'Veiculo não encontrado',}), 400
        print(data)
        valor_total=0
        cursor.execute("""
            insert into manutencao (id_veiculo, data, valor_total) 
            values (?, ?, ?)
            returning id_manutencao
        """, (veiculo[0], data, valor_total))

        id_manutencao = cursor.fetchone()[0]
        con.commit()

        return jsonify({
            'mensagem': 'Manutenção cadastrada com sucesso',
            'id_manutencao': id_manutencao
        }), 200
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
    try:
        cursor= con.cursor()
        data_atual = datetime.now().date()
        data = datetime.strptime(data, "%d/%m/%Y").date()

        if data < data_atual:
            return jsonify({
                'mensagem': 'Não é possível deletar manutencao com data retroativa'
            }), 403
        cursor.execute("""update manutencao 
                        set id_veiculo = ? , data = ? 
                        where id_manutencao = ?""",
                       (id_veiculo, data, id_manutencao))
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
    print("1")
    cursor.execute("""select id_manutencao, id_veiculo, valor_total, data       
                        from manutencao where id_manutencao=?""", (id_manutencao,))
    existe_manutencao = cursor.fetchone()
    print("2")
    print(existe_manutencao)
    if not existe_manutencao:
        return jsonify({'mensagem': 'Não existe manutenção'})

    try:
        cursor = con.cursor()

        cursor.execute("""select data from manutencao where id_manutencao = ?""", (id_manutencao,))
        data = cursor.fetchone()[0]
        print(data)
        data_atual = datetime.now().date()

        if data < data_atual:
            return jsonify({
                'mensagem': 'Não é possível deletar manutencao com data retroativa'
            }), 403
        cursor.execute("""delete from manutencao where id_manutencao=?""",
                       (id_manutencao,))
        con.commit()
        return jsonify({'mensagem': 'Manutenção deletado com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar manutenção'}), 500
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
                            SELECT m.ID_MANUTENCAO, v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME 
                            FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA 
                            WHERE M.ID_VEICULO = ?
            """, (id_veiculo,))

        elif id_manutencao:
            cursor.execute(""" 
                            SELECT m.ID_MANUTENCAO, v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME 
                            FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA 
                            WHERE M.id_manutencao = ?
            """, (id_manutencao,))

        elif valor_total:
            cursor.execute("""
                           SELECT m.ID_MANUTENCAO, v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME
                           FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA
                           WHERE M.valor_total = ?
            """, (valor_total,))

        else:
            cursor.execute("""
                            SELECT m.ID_MANUTENCAO, v.modelo, m."DATA", m.VALOR_TOTAL, M2.NOME
                           FROM MANUTENCAO m
                            INNER JOIN VEICULO v ON M.ID_VEICULO = V.ID_VEICULO
                            INNER JOIN MARCA m2 ON V.ID_MARCA = M2.ID_MARCA
            """)

        manutenções = cursor.fetchall()

        for manutenção in manutenções:
            lista_manutenções.append({
                'id_manutencao': manutenção[0],
                'modelo': manutenção[1],
                'data': manutenção[2],
                'valor_total': manutenção[3],
                'nome': manutenção[4]
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



        cursor.execute("""UPDATE MANUTENCAO SET VALOR_TOTAL =  (SELECT sum(coalesce(ITEM_MANUTENCAO.VALOR_TOTAL,0))  
                                                                FROM ITEM_MANUTENCAO
                                                               WHERE ITEM_MANUTENCAO.ID_MANUTENCAO = MANUTENCAO.ID_MANUTENCAO
                                                               )
                           WHERE MANUTENCAO.ID_MANUTENCAO  = ? """,(id_manutencao,))
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

        cursor.execute("""UPDATE MANUTENCAO
                          SET VALOR_TOTAL = (SELECT sum(coalesce(ITEM_MANUTENCAO.VALOR_TOTAL, 0))
                                             FROM ITEM_MANUTENCAO
                                             WHERE ITEM_MANUTENCAO.ID_MANUTENCAO = MANUTENCAO.ID_MANUTENCAO)
                          WHERE MANUTENCAO.ID_MANUTENCAO = ? """, (id_manutencao,))
        con.commit()

        return jsonify({'mensagem': 'Item de manutencao atualizado com sucesso', }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao editar item de manutenção: {str(e)}'}), 500

    finally:
        cursor.close()

@app.route('/deletar_item_manutencao/<int:id_item_manutencao>', methods=['DELETE'])
def deletar_item_manutencao(id_item_manutencao):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode deletar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT im.id_manutencao, im.valor_total, m.data
            FROM item_manutencao im
            INNER JOIN manutencao m ON im.id_manutencao = m.id_manutencao
            WHERE im.id_item_manutencao = ?
        """, (id_item_manutencao,))
        item_banco = cursor.fetchone()

        if not item_banco:
            return jsonify({'mensagem': 'Item de manutenção não encontrado'}), 404

        id_manutencao = item_banco[0]
        valor_item = float(item_banco[1])
        data_manutencao = item_banco[2]

        data_atual = datetime.now().date()

        if data_manutencao < data_atual:
            return jsonify({
                'mensagem': 'Não é possível deletar manutencao com data retroativa'
            }), 403

        cursor.execute("""
            DELETE FROM item_manutencao
            WHERE id_item_manutencao = ?
        """, (id_item_manutencao,))

        cursor.execute("""UPDATE MANUTENCAO
                          SET VALOR_TOTAL = (SELECT sum(coalesce(ITEM_MANUTENCAO.VALOR_TOTAL, 0))
                                             FROM ITEM_MANUTENCAO
                                             WHERE ITEM_MANUTENCAO.ID_MANUTENCAO = MANUTENCAO.ID_MANUTENCAO)
                          WHERE MANUTENCAO.ID_MANUTENCAO = ? """, (id_manutencao,))
        con.commit()

        return jsonify({'mensagem': 'Item de manutenção deletado com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao deletar item: {str(e)}'}), 500

    finally:
        cursor.close()

@app.route('/buscar_itens_manutencao_veiculo', methods=['POST'])
def buscar_itens_manutencao_veiculo():
    dados = request.get_json()
    id_veiculo = dados.get('id_veiculo')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT 
                im.id_item_manutencao,
                im.id_manutencao,
                s.descricao,
                im.quantidade,
                im.valor_total,
                m.data
            FROM item_manutencao im
            INNER JOIN manutencao m ON im.id_manutencao = m.id_manutencao
            INNER JOIN servico s ON im.id_servico = s.id_servico
            WHERE m.id_veiculo = ?
            ORDER BY m.data DESC
        """, (id_veiculo,))

        itens = cursor.fetchall()

        lista_itens = []

        for item in itens:
            lista_itens.append({
                'id_item_manutencao': item[0],
                'id_manutencao': item[1],
                'descricao': item[2],
                'quantidade': item[3],
                'valor_total': item[4],
                'data': item[5]
            })

        return jsonify({'itens': lista_itens}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar itens: {str(e)}'}), 500

    finally:
        cursor.close()






@app.route('/buscar_historico_servico', methods=['POST'])
def buscar_historico_servico():
    dados = request.get_json()
    id_servico = dados.get('id_servico')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403
    try:
        cursor = con.cursor()
        lista_historico_servico = []

        if id_servico:
            cursor.execute("""
                            SELECT S.DESCRICAO, HS.VALOR_UNITARIO, HS.DATA_HISTORICO
                            FROM HISTORICO_SERVICO hs 
                            INNER JOIN SERVICO s ON HS.ID_SERVICO = S.ID_SERVICO 
                            WHERE S.ID_SERVICO = ?
            """, (id_servico,))

        else:
            cursor.execute("""
                            SELECT S.DESCRICAO, HS.VALOR_UNITARIO, HS.DATA_HISTORICO
                            FROM HISTORICO_SERVICO hs 
                            INNER JOIN SERVICO s ON HS.ID_SERVICO = S.ID_SERVICO 
            """)

        historico_servicos = cursor.fetchall()

        for historico_servico in historico_servicos:
            lista_historico_servico.append({
                'descrição': historico_servico[0],
                'valor_unitário': historico_servico[1],
                'data_histórico': historico_servico[2],
            })

        if not lista_historico_servico:
            return jsonify({'mensagem': 'historico não encontrado'}), 404

        return jsonify({'manutenções': lista_historico_servico}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar histórico'}), 500

    finally:
        cursor.close()

@app.route('/atualizacao_preco', methods=['POST'])
def atualizacao_preco():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode atualizar'}), 403

    try:
        cursor = con.cursor()
        print("aquii")
        dados = request.get_json()
        print("DADOS RECEBIDOS:", dados)
        id_servico = int(dados.get('id_servico'))
        tipo = int(dados.get('tipo'))
        porcentagem = float(dados.get('porcentagem'))
        print(porcentagem)
        print(tipo)
        print(id_servico)
        if not dados:
            return jsonify({'mensagem': 'JSON inválido'}), 400
        print(porcentagem)
        print(tipo)
        print(id_servico)
        cursor.execute(
            """EXECUTE PROCEDURE pr_atualiza_valor (?,?,?)""",
            (int(tipo), int(id_servico), float(porcentagem))
        )

        con.commit()

        return jsonify({'mensagem': 'Serviço atualizado com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao atualizar Serviço: {str(e)}'}), 500

    finally:
            cursor.close()