from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario
import os


@app.route("/adicionar_veiculo", methods=['POST'])
def adicionar_veiculo():
    id_marca = request.form.get('id_marca')
    modelo = request.form.get('modelo')
    ano_fabricacao = request.form.get('ano_fabricacao')
    ano_modelo = request.form.get('ano_modelo')
    placa = request.form.get('placa')
    km = request.form.get('km')
    cor = request.form.get('cor')
    cambio = request.form.get('cambio')
    combustivel = request.form.get('combustivel')
    renavam = request.form.get('renavam')
    preco_custo = request.form.get('preco_custo')
    preco_venda = request.form.get('preco_venda')
    documentacao = request.form.get('documentacao')

    imagens = request.files.getlist('imagem')

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("SELECT 1 FROM veiculo WHERE renavam = ?", (renavam,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe um veículo com esse renavam'}), 400

        cursor.execute("SELECT 1 FROM veiculo WHERE placa = ?", (placa,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe um veículo com essa placa'}), 400

        print('aqqqq')

        cursor.execute(""" select id_marca from marca where id_marca=? """, (id_marca,))
        marca_banco = cursor.fetchone()

        print('aq de novo')

        cursor.execute("select id_empresa from empresa")
        empresa_banco = cursor.fetchone()

        print('aq de novoooo')

        cursor.execute("""INSERT INTO veiculo(id_marca,modelo,ano_fabricacao,ano_modelo,placa,km,cor,cambio,combustivel,renavam,preco_custo,preco_venda,status,documentacao, id_empresa
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            RETURNING id_veiculo
        """, (marca_banco[0],modelo,ano_fabricacao,ano_modelo,placa,km,cor,cambio,combustivel,renavam,preco_custo,preco_venda,documentacao, empresa_banco[0]))
        print("a2")

        id_veiculo = cursor.fetchone()[0]
        con.commit()

        pasta_veiculo = os.path.join(app.config['UPLOAD_FOLDER'], 'veiculo', str(id_veiculo))
        os.makedirs(pasta_veiculo, exist_ok=True)

        contador = 1
        for imagem in imagens:
            if imagem.filename != "":
                caminho = os.path.join(pasta_veiculo, f"foto_{contador}.jpg")
                imagem.save(caminho)
                contador += 1

        return jsonify({
            'mensagem': 'Veículo cadastrado com sucesso',
            'id_veiculo': id_veiculo
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar veículo'}), 500
    finally:
        cursor.close()

@app.route('/edicao_veiculo/<int:id_veiculo>', methods=['PUT'])
def edicao_veiculo(id_veiculo):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar veiculo'}), 403

    id_marca = request.form.get('id_marca')
    modelo = request.form.get('modelo')
    ano_fabricacao = request.form.get('ano_fabricacao')
    ano_modelo = request.form.get('ano_modelo')
    placa = request.form.get('placa')
    km = request.form.get('km')
    cor = request.form.get('cor')
    cambio = request.form.get('cambio')
    combustivel = request.form.get('combustivel')
    renavam = request.form.get('renavam')
    preco_custo = request.form.get('preco_custo')
    preco_venda = request.form.get('preco_venda')
    documentacao = request.form.get('documentacao')
    status = request.form.get('status') or 0

    imagens = request.files.getlist('imagem')

    try:
        cursor = con.cursor()

        cursor.execute("SELECT 1 FROM VEICULO WHERE ID_VEICULO = ?", (id_veiculo,))
        if not cursor.fetchone():
            return jsonify({'mensagem': 'Veiculo nao encontrado'}), 404

        cursor.execute(
            "SELECT 1 FROM VEICULO WHERE RENAVAM = ? AND ID_VEICULO != ?",
            (renavam, id_veiculo)
        )
        if cursor.fetchone():
            return jsonify({'mensagem': 'Renavam já cadastrado'}), 400

        cursor.execute(
            "SELECT 1 FROM VEICULO WHERE PLACA = ? AND ID_VEICULO != ?",
            (placa, id_veiculo)
        )
        if cursor.fetchone():
            return jsonify({'mensagem': 'Placa já cadastrada'}), 400

        cursor.execute(""" SELECT STATUS FROM VEICULO WHERE ID_VEICULO = ?""",(id_veiculo,))
        veiculo = cursor.fetchone()
        status = veiculo[0]
        if status == 2:
            return jsonify({'mensagem': 'Veículo vendido não pode ser editado.'}), 404

        cursor.execute("""
            UPDATE VEICULO
            SET 
                ID_MARCA = ?,
                MODELO = ?,
                ANO_FABRICACAO = ?,
                ANO_MODELO = ?,
                PLACA = ?,
                KM = ?,
                COR = ?,
                CAMBIO = ?,
                COMBUSTIVEL = ?,
                RENAVAM = ?,
                PRECO_CUSTO = ?,
                PRECO_VENDA = ?,
                DOCUMENTACAO = ?,
                STATUS = ?
            WHERE ID_VEICULO = ?
        """, (
            id_marca,
            modelo,
            ano_fabricacao,
            ano_modelo,
            placa,
            km,
            cor,
            cambio,
            combustivel,
            renavam,
            preco_custo,
            preco_venda,
            documentacao,
            status,
            id_veiculo
        ))

        con.commit()

        if imagens:
            pasta_veiculo = os.path.join(app.config['UPLOAD_FOLDER'], 'veiculo', str(id_veiculo))
            os.makedirs(pasta_veiculo, exist_ok=True)

            contador = 1
            for imagem in imagens:
                if imagem.filename != "":
                    caminho = os.path.join(pasta_veiculo, f"foto_{contador}.jpg")
                    imagem.save(caminho)
                    contador += 1

        return jsonify({
            'mensagem': 'Veículo atualizado com sucesso',
            'id_veiculo': id_veiculo
        }), 200

    except Exception as e:
        print("ERRO AO EDITAR VEICULO:", e)
        return jsonify({'mensagem': f'Erro ao editar veiculo: {e}'}), 500

    finally:
        cursor.close()


@app.route('/deletar_veiculo/<id_veiculo>', methods=['DELETE'])
def deletar_veiculo(id_veiculo):

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:  # isso significa que a funcao returnou null entao, o usuario nao esta logado
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM Pode deletar'})


    try:

        cursor = con.cursor()
        cursor.execute('select 1 from veiculo where id_veiculo = ?', (id_veiculo,))

        if not cursor.fetchone():
            return jsonify({'mensagem': 'veiculo nao encontrado'})

        print('aq')
        cursor.execute('delete from veiculo where id_veiculo = ?', (id_veiculo,))
        con.commit()
        return jsonify({'mensagem': 'Veículo deletado com sucesso'}), 300

    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar veiculo'}), 500
    finally:
        cursor.close()


@app.route('/buscar_veiculo', methods=['POST'])
def buscar_veiculo():
    dados = request.get_json()
    modelo = dados.get('modelo')
    nome = dados.get('nome')
    id_veiculo = dados.get('id_veiculo')

    tipo_usuario = descobre_tipo_usuario()

    try:
        cursor = con.cursor()
        lista_veiculos = []

        if modelo:
            modelo = modelo.upper()
            cursor.execute("""
                SELECT v.ID_VEICULO, m.nome, v.MODELO, v.ANO_FABRICACAO, v.ANO_MODELO, v.PLACA, v.KM, v.COR, v.CAMBIO,
                       v.COMBUSTIVEL, v.RENAVAM, v.PRECO_CUSTO, v.PRECO_VENDA, v.STATUS, v.DOCUMENTACAO
                FROM veiculo v 
                INNER JOIN MARCA m ON V.ID_MARCA = M.ID_MARCA 
                WHERE upper(modelo) LIKE ?
            """, (f'%{modelo}%',))

        elif nome:
            nome = nome.upper()
            cursor.execute("""
                SELECT v.ID_VEICULO, m.nome, v.MODELO, v.ANO_FABRICACAO, v.ANO_MODELO, v.PLACA, v.KM, v.COR, v.CAMBIO,
                       v.COMBUSTIVEL, v.RENAVAM, v.PRECO_CUSTO, v.PRECO_VENDA, v.STATUS, v.DOCUMENTACAO
                FROM veiculo v 
                INNER JOIN MARCA m ON V.ID_MARCA = M.ID_MARCA 
                WHERE upper(m.NOME) LIKE ?
            """, (f'%{nome}%',))

        elif id_veiculo:
            cursor.execute("""
                SELECT v.ID_VEICULO, m.nome, v.MODELO, v.ANO_FABRICACAO, v.ANO_MODELO, v.PLACA, v.KM, v.COR, v.CAMBIO,
                       v.COMBUSTIVEL, v.RENAVAM, v.PRECO_CUSTO, v.PRECO_VENDA, v.STATUS, v.DOCUMENTACAO
                FROM veiculo v 
                INNER JOIN MARCA m ON V.ID_MARCA = M.ID_MARCA 
                WHERE v.ID_VEICULO = ?
            """, (id_veiculo,))

        else:
            cursor.execute("""
                SELECT v.ID_VEICULO, m.nome, v.MODELO, v.ANO_FABRICACAO, v.ANO_MODELO, v.PLACA, v.KM, v.COR, v.CAMBIO,
                       v.COMBUSTIVEL, v.RENAVAM, v.PRECO_CUSTO, v.PRECO_VENDA, v.STATUS, v.DOCUMENTACAO
                FROM veiculo v 
                INNER JOIN MARCA m ON V.ID_MARCA = M.ID_MARCA
            """)

        veiculos = cursor.fetchall()

        for veiculo in veiculos:
            lista_veiculos.append({
                'ID_VEICULO': veiculo[0],
                'MARCA': veiculo[1],
                'MODELO': veiculo[2],
                'ANO_FABRICACAO': veiculo[3],
                'ANO_MODELO': veiculo[4],
                'PLACA': veiculo[5],
                'KM': veiculo[6],
                'COR': veiculo[7],
                'CAMBIO': veiculo[8],
                'COMBUSTIVEL': veiculo[9],
                'RENAVAM': veiculo[10],
                'PRECO_CUSTO': veiculo[11],
                'PRECO_VENDA': veiculo[12],
                'STATUS': veiculo[13],
                'DOCUMENTACAO': veiculo[14]
            })

        if not lista_veiculos:
            return jsonify({'mensagem': 'Veículo não encontrado'}), 404

        return jsonify({'veiculos': lista_veiculos}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao listar veículos: {str(e)}'}), 500

    finally:
        cursor.close()


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
