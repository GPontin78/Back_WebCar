from flask import jsonify, request, send_from_directory, send_file
from main import app, con
from funcao import descobre_tipo_usuario, descobre_id_usuario, gerar_pix
from datetime import datetime, timedelta
import os


@app.route('/adicionar_venda', methods=['POST'])
def adicionar_venda():
    dados = request.get_json()

    id_veiculo = int(dados.get('id_veiculo'))
    forma_pagamento = int(dados.get('forma_pagamento'))
    parcela = dados.get('parcela')
    cpf_cliente = dados.get('cpf_cliente')

    id_usuario_logado = descobre_id_usuario()
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if forma_pagamento != 0 and forma_pagamento != 1:
        return jsonify({'mensagem': 'Selecione uma forma de pagamento válida'}), 400

    if tipo_usuario == 1:
        if not cpf_cliente:
            return jsonify({'mensagem': 'Informe o CPF do cliente'}), 400

        if len(cpf_cliente) != 11:
            return jsonify({'mensagem': 'CPF inválido'}), 400

    if forma_pagamento == 1:
        if tipo_usuario != 1:
            return jsonify({'mensagem': 'Apenas vendedor pode registrar financiamento'}), 403

        if not parcela:
            return jsonify({'mensagem': 'Selecione a quantidade de parcelas'}), 400

        parcela = int(parcela)

        if parcela <= 0:
            return jsonify({'mensagem': 'Quantidade de parcelas inválida'}), 400

    cursor = con.cursor()

    try:
        if tipo_usuario == 1:
            cursor.execute("""
                SELECT id_usuario
                FROM usuario
                WHERE cpf = ?
                AND tipo = ?
            """, (cpf_cliente, 2))

            cliente = cursor.fetchone()

            if not cliente:
                return jsonify({'mensagem': 'Cliente não encontrado com esse CPF'}), 404

            id_usuario_cliente = cliente[0]
        else:
            id_usuario_cliente = id_usuario_logado

        cursor.execute("""
            SELECT preco_venda, id_empresa, preco_custo, status, id_marca, modelo
            FROM veiculo
            WHERE id_veiculo = ?
        """, (id_veiculo,))

        veiculo = cursor.fetchone()

        if not veiculo:
            return jsonify({'mensagem': 'Selecione um veiculo'}), 400

        preco_venda = float(veiculo[0])
        id_empresa_veiculo = veiculo[1]
        status = veiculo[3]
        id_marca = veiculo[4]
        modelo = veiculo[5]

        if status == 2:
            return jsonify({'mensagem': 'Este veículo já foi vendido'}), 400

        cursor.execute("""
            SELECT nome
            FROM marca
            WHERE id_marca = ?
        """, (id_marca,))

        marca = cursor.fetchone()
        nome_marca = marca[0] if marca else ''

        cursor.execute("""
            SELECT desconto_a_vista, porcentagem_juro, chave_pix, nome_fantasia, cidade
            FROM empresa
            WHERE id_empresa = ?
        """, (id_empresa_veiculo,))

        empresa = cursor.fetchone()

        if not empresa:
            return jsonify({'mensagem': 'Empresa do veículo não encontrada'}), 404

        desconto_a_vista_banco = float(empresa[0] or 0)
        porcentagem_juro_banco = float(empresa[1] or 0)
        chave_pix = empresa[2]
        nome_empresa = empresa[3]
        cidade_empresa = empresa[4]

        data_venda = datetime.now()

        if forma_pagamento == 0 or tipo_usuario == 2:
            valor_venda_desconto = float(
                preco_venda - (preco_venda * (desconto_a_vista_banco / 100))
            )

            cursor.execute("""
                INSERT INTO venda (
                    id_usuario_cliente,
                    id_veiculo,
                    data_venda,
                    valor_venda,
                    forma_pagamento,
                    id_usuario_vendedor
                )
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id_venda
            """, (
                id_usuario_cliente,
                id_veiculo,
                data_venda,
                valor_venda_desconto,
                forma_pagamento,
                id_usuario_logado
            ))

            id_venda = cursor.fetchone()[0]

            pix = gerar_pix(
                chave=chave_pix,
                nome=nome_empresa,
                cidade=cidade_empresa,
                valor=valor_venda_desconto,
                pasta="avista",
                txid=str(id_venda)
            )

            cursor.execute("""
                UPDATE veiculo
                SET status = ?
                WHERE id_veiculo = ?
            """, (2, id_veiculo))

            descricao = f'Veículo vendido: {nome_marca} {modelo}'
            tabela = 'VENDA'.upper()

            cursor.execute("""
                INSERT INTO receita (
                    id_tabela,
                    descricao,
                    valor,
                    data_receita,
                    tabela,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                id_venda,
                descricao,
                valor_venda_desconto,
                data_venda,
                tabela,
                0
            ))

            con.commit()

            return send_file(pix['imagem'], mimetype='image/png')

        if forma_pagamento == 1 and tipo_usuario == 1:
            valor = preco_venda
            valor_parcela_orginal = round(float(valor/parcela), 2)
            valor_certo = round(float(valor_parcela_orginal * parcela), 2)
            juro = porcentagem_juro_banco / 100

            parcela_mensal_juro = round(float(valor_certo * juro / (1 - (1 + juro) ** -parcela)), 2)

            valor_venda_financiamento = round(float(parcela_mensal_juro * parcela),2)

            cursor.execute("""
                INSERT INTO venda (
                    id_usuario_cliente,
                    id_usuario_vendedor,
                    id_veiculo,
                    data_venda,
                    valor_venda,
                    forma_pagamento
                )
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id_venda
            """, (
                id_usuario_cliente,
                id_usuario_logado,
                id_veiculo,
                data_venda,
                valor_venda_financiamento,
                forma_pagamento
            ))

            id_venda = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO financiamento (
                    id_venda,
                    data_financiamento,
                    valor_venda,
                    valor_venda_financiamento,
                    PORCENTAGEM_JURO_FINANCIAMENTO
                )
                VALUES (?, ?, ?, ?, ?)
                RETURNING id_financiamento
            """, (
                id_venda,
                data_venda,
                valor,
                valor_venda_financiamento,
                porcentagem_juro_banco
            ))

            id_financiamento = cursor.fetchone()[0]

            for numero_parcela in range(1, parcela + 1):
                data_vencimento = data_venda + timedelta(days=30 * numero_parcela)

                gerar_pix(
                    chave=chave_pix,
                    nome=nome_empresa,
                    cidade=cidade_empresa,
                    valor=parcela_mensal_juro,
                    pasta="financiamento",
                    txid=f"F{id_financiamento}P{numero_parcela}"
                )

                cursor.execute("""
                    INSERT INTO item_financiamento (
                        id_financiamento,
                        numero_parcela,
                        valor_parcela,
                        data_vencimento,
                        valor_parcela_original,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    id_financiamento,
                    numero_parcela,
                    parcela_mensal_juro,
                    data_vencimento,
                    valor_parcela_orginal,
                    0
                ))

            cursor.execute("""
                UPDATE veiculo
                SET status = ?
                WHERE id_veiculo = ?
            """, (2, id_veiculo))

            con.commit()

            return jsonify({
                'mensagem': 'Venda concluída com sucesso',
                'id_venda': id_venda,
                'id_financiamento': id_financiamento,
                'porcentagem_juro': porcentagem_juro_banco,
                'valor_parcela': round(parcela_mensal_juro, 2),
                'valor_total': valor_venda_financiamento
            }), 200

    except Exception as e:
        con.rollback()
        return jsonify({'mensagem': f'Erro ao concluir venda: {str(e)}'}), 500

    finally:
        cursor.close()


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

@app.route('/verporcentagem_juro', methods=['GET'])
def verporcentagem_juro():
    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT FIRST 1 porcentagem_juro
            FROM empresa
        """)

        empresa = cursor.fetchone()

        if not empresa:
            return jsonify({'mensagem': 'Empresa não encontrada'}), 404

        return jsonify({
            'porcentagem_juro': float(empresa[0] or 0)
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar juros: {e}'}), 500

    finally:
        cursor.close()


@app.route('/verporcentagem_desconto', methods=['GET'])
def verporcentagem_desconto():
    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT FIRST 1 desconto_a_vista
            FROM empresa
        """)

        empresa = cursor.fetchone()

        if not empresa:
            return jsonify({'mensagem': 'Empresa não encontrada'}), 404

        return jsonify({
            'desconto_a_vista': float(empresa[0] or 0)
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar desconto: {e}'}), 500

    finally:
        cursor.close()

@app.route('/qrcode_financiamento/<int:id_financiamento>/<int:numero_parcela>', methods=['GET'])
def qrcode_financiamento(id_financiamento, numero_parcela):
    tipo_usuario = descobre_tipo_usuario()
    id_usuario_logado = descobre_id_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT v.id_usuario_cliente
            FROM financiamento f
            INNER JOIN venda v ON v.id_venda = f.id_venda
            WHERE f.id_financiamento = ?
        """, (id_financiamento,))

        financiamento = cursor.fetchone()

        if not financiamento:
            return jsonify({'mensagem': 'Financiamento não encontrado'}), 404

        id_cliente = financiamento[0]

        if tipo_usuario != 0:
            if id_usuario_logado != id_cliente:
                return jsonify({'mensagem': 'usuario nao pertence a essa conta'}), 403

        caminho = os.path.join(
            "uploads",
            "pagamento",
            "financiamento",
            f"F{id_financiamento}P{numero_parcela}.png"
        )

        if not os.path.exists(caminho):
            return jsonify({'mensagem': 'QR Code não encontrado'}), 404

        return send_file(caminho, mimetype='image/png')

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar QR Code: {e}'}), 500

    finally:
        cursor.close()

@app.route('/minhas_compras', methods=['GET'])
def minhas_compras():
    tipo_usuario = descobre_tipo_usuario()
    id_usuario_logado = descobre_id_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    id_usuario = request.args.get('id_usuario', id_usuario_logado)
    id_usuario = int(id_usuario)

    if tipo_usuario != 0:
        if id_usuario_logado != id_usuario:
            return jsonify({'mensagem': 'usuario nao pertence a essa conta'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT
                v.id_venda,
                v.id_veiculo,
                v.data_venda,
                v.valor_venda,
                v.forma_pagamento,
                vei.modelo,
                vei.ano_modelo,
                vei.placa,
                m.nome,
                vendedor.nome,
                f.id_financiamento,
                f.valor_venda,
                f.valor_venda_financiamento
            FROM venda v
            INNER JOIN veiculo vei ON vei.id_veiculo = v.id_veiculo
            INNER JOIN marca m ON m.id_marca = vei.id_marca
            LEFT JOIN usuario vendedor ON vendedor.id_usuario = v.id_usuario_vendedor
            LEFT JOIN financiamento f ON f.id_venda = v.id_venda
            WHERE v.id_usuario_cliente = ?
            ORDER BY v.data_venda DESC
        """, (id_usuario,))

        vendas = cursor.fetchall()
        compras = []

        for venda in vendas:
            id_financiamento = venda[10]
            parcelas = []

            if id_financiamento:
                cursor.execute("""
                    SELECT
                        numero_parcela,
                        valor_parcela,
                        data_vencimento,
                        data_pagamento,
                        COALESCE(status, 0)
                    FROM item_financiamento
                    WHERE id_financiamento = ?
                    ORDER BY numero_parcela
                """, (id_financiamento,))

                itens = cursor.fetchall()

                for item in itens:
                    parcelas.append({
                        'numero_parcela': item[0],
                        'valor_parcela': float(item[1] or 0),
                        'data_vencimento': item[2],
                        'data_pagamento': item[3],
                        'status': int(item[4] or 0),
                        'qrcode_url': f'{request.host_url}qrcode_financiamento/{id_financiamento}/{item[0]}'
                    })

            compras.append({
                'id_venda': venda[0],
                'id_veiculo': venda[1],
                'data_venda': venda[2],
                'valor_venda': float(venda[3] or 0),
                'forma_pagamento': int(venda[4] or 0),
                'modelo': venda[5],
                'ano_modelo': venda[6],
                'placa': venda[7],
                'marca': venda[8],
                'vendedor': venda[9] or 'Nao informado',
                'id_financiamento': id_financiamento,
                'valor_original': float(venda[11] or 0),
                'valor_financiado': float(venda[12] or 0),
                'parcelas': parcelas
            })

        return jsonify({'compras': compras}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar compras: {e}'}), 500

    finally:
        cursor.close()