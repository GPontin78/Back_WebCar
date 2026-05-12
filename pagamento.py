from flask import jsonify, request, send_from_directory, send_file
from main import app, con
from funcao import descobre_tipo_usuario, descobre_id_usuario, gerar_pix
from datetime import datetime, timedelta

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

        if forma_pagamento != 0 and forma_pagamento != 1:
           return jsonify({'mensagem': 'Selecione uma forma de pagamento válida'}), 400


        if forma_pagamento == 0 or tipo_usuario == 2:

            valor_venda_desconto = float(preco_venda - (preco_venda * (desconto_a_vista_banco / 100)))

            cursor.execute("""INSERT INTO venda(id_usuario_cliente, id_veiculo, data_venda, 
                            valor_venda, forma_pagamento, id_usuario_vendedor) 
                            VALUES(?,?,?,?,?,?) RETURNING ID_VENDA""",
                           (id_usuario_cliente, id_veiculo, data_venda, valor_venda_desconto, forma_pagamento, id_usuario_cliente_avista))

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
            tabela = 'VENDA'.upper()
            cursor.execute("""INSERT INTO receita(id_tabela, descricao, valor, data_receita, tabela, status) 
                            VALUES(?,?,?,?,?,?)""",
                           (id_venda, descricao, valor_venda_desconto, data_venda, tabela, status ))

            con.commit()

            return send_file(
                pix['imagem'],
                mimetype='image/png')

        if forma_pagamento == 1 and tipo_usuario == 1:
            valor = preco_venda
            juro = porcentagem_juro_banco / 100
            parcela_mensal_juro = float(valor * juro / (1 - (1 + juro) ** -parcela))
            valor_venda_financiamento = float(parcela_mensal_juro * parcela)
            print("aquiii")

            cursor.execute("""INSERT INTO venda(id_usuario_cliente, id_usuario_vendedor, id_veiculo, data_venda, valor_venda, forma_pagamento)
                              VALUES(?,?,?,?,?,1) RETURNING ID_VENDA""",
                (id_usuario_cliente, descobre_id_usuario(), id_veiculo, data_venda, valor_venda_financiamento,forma_pagamento))
            id_venda = cursor.fetchone()[0]
            print("aquiii2222")

            cursor.execute(""" INSERT INTO FINANCIAMENTO(ID_VENDA, DATA_FINANCIAMENTO, VALOR_VENDA,
                                VALOR_VENDA_FINANCIAMENTO)
                                VALUES(?,?,?,?) RETURNING ID_FINANCIAMENTO""",
                                    (id_venda, data_venda, valor, valor_venda_financiamento))
            id_financiamento = cursor.fetchone()[0]
            print("aquiii333333333")


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

                cursor.execute("""INSERT INTO item_financiamento(id_financiamento, numero_parcela, 
                                valor_parcela, data_vencimento) VALUES(?,?,?,?)""",
                    (id_financiamento, numero_parcela, parcela_mensal_juro, data_vencimento))

            cursor.execute("""UPDATE veiculo SET status = ? WHERE id_veiculo = ?""", (2, id_veiculo))
            con.commit()
            return jsonify({'mensagem': 'Venda concluída com sucesso'}), 200

    except Exception as e:

        return jsonify({'mensagem': f'Erro ao concluir venda: {str(e)}'}), 500


@app.route('/adicionar_receita', methods=['POST'])
def adicionar_receita():
    dados = request.get_json()
    descricao = dados.get('descricao').capitalize()
    valor =  float(dados.get('valor'))
    data_receita = dados.get('data_receita')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        if not descricao:
            return jsonify({'mensagem': 'Digite uma descrição', }), 400
        if not valor:
            return jsonify({'mensagem': 'Digite um valor', }), 400
        if not data_receita:
            return jsonify({'mensagem': 'Digite uma data', }), 400

        print("1")
        print(descricao)
        print(valor)
        print(data_receita)
        data_receita = datetime.strptime(data_receita, "%d/%m/%Y").date()
        print(data_receita)

        cursor.execute("""insert into receita (descricao, valor, data_receita) 
                          values(?,?,?)""", (descricao, valor , data_receita))
        con.commit()

        return jsonify({'mensagem': 'Receita cadastrada com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar Receita'}), 500
    finally:
        cursor.close()

@app.route('/edicao_receita/<int:id_receita>', methods=['PUT'])
def edicao_receita(id_receita):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()

    try:
        cursor.execute("""
            select id_receita, descricao, valor, data_receita
            from receita
            where id_receita = ?
        """, (id_receita,))

        existe_receita = cursor.fetchone()

        if not existe_receita:
            return jsonify({'mensagem': 'Receita não encontrada'}), 404

        dados = request.get_json()

        descricao = dados.get('descricao', existe_receita[1]).capitalize()
        valor = float(dados.get('valor', existe_receita[2]))
        data_receita = dados.get('data_receita')

        if data_receita:
            data_receita = datetime.strptime(data_receita, "%d/%m/%Y").date()
        else:
            data_receita = existe_receita[3]


        cursor.execute("""
            update receita
            set descricao = ?, valor = ?, data_receita = ?
            where id_receita = ?
        """, (descricao, valor, data_receita, id_receita))

        con.commit()

        return jsonify({'mensagem': 'Receita atualizada com sucesso'}), 200

    except Exception as e:
        return jsonify({
            'mensagem': f'Erro ao editar receita: {str(e)}'
        }), 500

    finally:
        cursor.close()

@app.route('/deletar_receita/<int:id_receita>', methods=['DELETE'])
def deletar_receita(id_receita):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode deletar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_receita, descricao, valor, data_receita       
                        from receita where id_receita=?""", (id_receita,))
    existe_receita = cursor.fetchone()
    if not existe_receita:
        return jsonify({'mensagem': 'Não existe despesa'})
    try:
        cursor = con.cursor()
        cursor.execute("""delete from receita where id_receita=?""",
                       (id_receita,))
        con.commit()
        return jsonify({'mensagem': 'Receita deletada com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar Receita'})
    finally:
        cursor.close()



@app.route('/adicionar_despesa', methods=['POST'])
def adicionar_despesa():
    dados = request.get_json()
    descricao = dados.get('descricao').capitalize()
    valor =  float(dados.get('valor'))
    data_despesa = dados.get('data_despesa')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        if not descricao:
            return jsonify({'mensagem': 'Digite uma descrição', }), 400
        if not valor:
            return jsonify({'mensagem': 'Digite um valor', }), 400
        if not data_despesa:
            return jsonify({'mensagem': 'Digite uma data', }), 400

        print("1")
        print(descricao)
        print(valor)
        print(data_despesa)
        data_despesa = datetime.strptime(data_despesa, "%d/%m/%Y").date()
        print(data_despesa)

        cursor.execute("""insert into despesa (descricao, valor, data_despesa) 
                          values(?,?,?)""", (descricao, valor , data_despesa))
        con.commit()

        return jsonify({'mensagem': 'Despesa cadastrada com sucesso',}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar Despesa'}), 500
    finally:
        cursor.close()


@app.route('/edicao_despesa/<int:id_despesa>', methods=['PUT'])
def edicao_despesa(id_despesa):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()

    try:
        cursor.execute("""
            select id_despesa, descricao, valor, data_despesa
            from despesa
            where id_despesa = ?
        """, (id_despesa,))

        existe_despesa = cursor.fetchone()

        if not existe_despesa:
            return jsonify({'mensagem': 'Despesa não encontrada'}), 404

        dados = request.get_json()

        descricao = dados.get('descricao', existe_despesa[1]).capitalize()
        valor = float(dados.get('valor', existe_despesa[2]))
        data_despesa = dados.get('data_despesa')

        if data_despesa:
            data_despesa = datetime.strptime(data_despesa, "%d/%m/%Y").date()
        else:
            data_despesa = existe_despesa[3]


        cursor.execute("""
            update despesa
            set descricao = ?, valor = ?, data_despesa = ?
            where id_despesa = ?
        """, (descricao, valor, data_despesa, id_despesa))

        con.commit()

        return jsonify({'mensagem': 'Despesa atualizada com sucesso'}), 200

    except Exception as e:
        return jsonify({
            'mensagem': f'Erro ao editar despesa: {str(e)}'
        }), 500

    finally:
        cursor.close()

@app.route('/deletar_depesa/<int:id_despesa>', methods=['DELETE'])
def deletar_depesa(id_despesa):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode deletar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_despesa, descricao, valor, data_despesa       
                        from despesa where id_despesa=?""", (id_despesa,))
    existe_despesa = cursor.fetchone()
    if not existe_despesa:
        return jsonify({'mensagem': 'Não existe despesa'})
    try:
        cursor = con.cursor()
        cursor.execute("""delete from despesa where id_despesa=?""",
                       (id_despesa,))
        con.commit()
        return jsonify({'mensagem': 'Despesa deletada com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar Despesa'})
    finally:
        cursor.close()


@app.route('/adicionar_baixa/<int:id_financiamento>', methods=['PUT'])
def adicionar_baixa(id_financiamento):
    dados = request.get_json()
    parcela = int(dados.get('parcela'))

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        if not parcela:
            return jsonify({'mensagem': 'Digite uma parcela '})

        data_pagamento = datetime.now().date()

        cursor.execute(""" select numero_parcela from item_financiamento 
                            where numero_parcela = ? and id_financiamento = ? """,(parcela, id_financiamento))
        if not cursor.fetchone():
            return jsonify({'mensagem': 'Selecione uma parcela válida'})

        cursor.execute("""update item_financiamento set data_pagamento = ?, status = ?
                            where numero_parcela = ? and id_financiamento = ?
        """, (data_pagamento, 1, parcela, id_financiamento))

        con.commit()

        return jsonify({'mensagem': 'Baixa realizada com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao adicionar baixa: {str(e)}'})


@app.route('/retirar_baixa/<int:id_financiamento>', methods=['PUT'])
def retirar_baixa(id_financiamento):
    dados = request.get_json()
    parcela = int(dados.get('parcela'))

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        if not parcela:
            return jsonify({'mensagem': 'Digite uma parcela '})

        data_pagamento = datetime.now().date()

        cursor.execute(""" select numero_parcela from item_financiamento 
                            where numero_parcela = ? and id_financiamento = ? """, (parcela, id_financiamento))
        if not cursor.fetchone():
            return jsonify({'mensagem': 'Selecione uma parcela válida'})

        cursor.execute("""update item_financiamento set data_pagamento = ?, status = ?
                            where numero_parcela = ? and id_financiamento = ?
        """, (data_pagamento, 0 , parcela, id_financiamento))

        con.commit()

        return jsonify({'mensagem': 'Baixa retirarada com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao retirar baixa: {str(e)}'})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)