from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
import os

@app.route("/adicionar_veiculo", methods=['POST'])
def adicionar_veiculo():
    marca = request.form.get('marca')
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

        cursor.execute("""INSERT INTO veiculo(marca,modelo,ano_fabricacao,ano_modelo,placa,km,cor,cambio,combustivel,renavam,preco_custo,preco_venda,status,documentacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            RETURNING id_veiculo
        """, (marca,modelo,ano_fabricacao,ano_modelo,placa,km,cor,cambio,combustivel,renavam,preco_custo,preco_venda,documentacao))

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

    cursor = con.cursor()
    cursor.execute("""
        SELECT MARCA, MODELO, ANO_FABRICACAO, ANO_MODELO, PLACA, KM, COR, CAMBIO,
               COMBUSTIVEL, RENAVAM, PRECO_CUSTO, PRECO_VENDA, STATUS, DOCUMENTACAO
        FROM VEICULO
        WHERE ID_VEICULO = ?
    """, (id_veiculo,))
    existe_veiculo = cursor.fetchone()

    if not existe_veiculo:
        return jsonify({'mensagem': 'Veiculo nao encontrado'}), 404

    marca = request.form.get('marca')
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
    status = request.form.get('status')

    imagens = request.files.getlist('imagem')

    try:
        cursor = con.cursor()


        cursor.execute("SELECT 1 FROM VEICULO WHERE RENAVAM = ? AND ID_VEICULO != ?", (renavam, id_veiculo))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Renavam já cadastrado'}), 400

        cursor.execute("SELECT 1 FROM VEICULO WHERE PLACA = ? AND ID_VEICULO != ?", (placa, id_veiculo))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Placa já cadastrada'}), 400

        cursor.execute("""
            UPDATE VEICULO
            SET MARCA = ?, MODELO = ?, ANO_FABRICACAO = ?, ANO_MODELO = ?, PLACA = ?,
                KM = ?, COR = ?, CAMBIO = ?, COMBUSTIVEL = ?, RENAVAM = ?,
                PRECO_CUSTO = ?, PRECO_VENDA = ?, DOCUMENTACAO = ?, STATUS = ?
                WHERE ID_VEICULO = ?
        """, (
            marca, modelo, ano_fabricacao, ano_modelo, placa, km, cor, cambio,
            combustivel, renavam, preco_custo, preco_venda, documentacao, status, id_veiculo
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
        return jsonify({'mensagem': 'erro ao editar veiculo'}), 500

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
        return jsonify({'mensagem': 'Veículo deletado com sucesso'})

    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar veiculo, em mais de uma tabela'})
    finally:
        cursor.close()


@app.route('/buscar_veiculo', methods=['POST'])
def buscar_veiculo():
    dados = request.get_json()
    modelo = dados.get('modelo').upper()
    id_veiculo = dados.get('id_veiculo')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_veiculos = []

        if modelo:
            cursor.execute("""
                SELECT MARCA, MODELO, ANO_FABRICACAO, ANO_MODELO, PLACA, KM, COR, CAMBIO,
               COMBUSTIVEL, RENAVAM, PRECO_CUSTO, PRECO_VENDA, STATUS, DOCUMENTACAO
                FROM veiculo 
                WHERE upper(modelo) LIKE ?
            """, (f'%{modelo}%',))


        elif id_veiculo:
            cursor.execute("""
                SELECT MARCA, MODELO, ANO_FABRICACAO, ANO_MODELO, PLACA, KM, COR, CAMBIO,
               COMBUSTIVEL, RENAVAM, PRECO_CUSTO, PRECO_VENDA, STATUS, DOCUMENTACAO
                FROM veiculo 
                WHERE id_veiculo = ?
            """, (id_veiculo,))

        else:
            cursor.execute("""
                SELECT MARCA, MODELO, ANO_FABRICACAO, ANO_MODELO, PLACA, KM, COR, CAMBIO,
               COMBUSTIVEL, RENAVAM, PRECO_CUSTO, PRECO_VENDA, STATUS, DOCUMENTACAO
                FROM veiculo
            """)

        veiculos = cursor.fetchall()

        for veiculo in veiculos:
            lista_veiculos.append({
                'MARCA': veiculo[0],
                'MODELO': veiculo[1],
                'ANO_FABRICACAO': veiculo[2],
                'ANO_MODELO': veiculo[3],
                'PLACA': veiculo[4],
                'KM': veiculo[5],
                'COR': veiculo[6],
                'CAMBIO': veiculo[7],
                'COMBUSTIVEL': veiculo[8],
                'RENAVAM': veiculo[9],
                'PRECO_CUSTO': veiculo[10],
                'PRECO_VENDA': veiculo[11],
                'STATUS': veiculo[12],
                'DOCUMENTACAO': veiculo[13]
            })

        if not lista_veiculos:
            return jsonify({'mensagem': 'Veículo não encontrado'}), 404

        return jsonify({'veiculos': lista_veiculos}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar veículos'}), 500

    finally:
        cursor.close()





