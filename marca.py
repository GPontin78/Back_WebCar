from flask import jsonify, request,send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario
import os

@app.route("/adicionar_marca", methods=['POST'])
def adicionar_marca():
    nome = request.form.get('nome').title()
    imagem = request.files.get('imagem')

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""SELECT 1 FROM marca WHERE nome = ?""", (nome,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe esta marca'}), 400
        if not nome:
            return jsonify({'mensagem': 'Digite uma Marca'}), 400

        cursor.execute("""
            INSERT INTO marca(nome)
            VALUES (?)
            RETURNING id_marca
        """, (nome,))

        id_marca = cursor.fetchone()[0]
        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "marca")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_marca}.jpg")
            imagem.save(caminho)

        return jsonify({
            'mensagem': 'Marca cadastrada com sucesso',
            'id_marca': id_marca
        }), 201

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar marca: {e}'}), 500

    finally:
        cursor.close()

@app.route('/edicao_marca/<int:id_marca>', methods=['PUT'])
def edicao_marca(id_marca):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT id_marca, nome       
            FROM marca 
            WHERE id_marca = ?
        """, (id_marca,))
        existe_marca = cursor.fetchone()

        if not existe_marca:
            return jsonify({'mensagem': 'Não existe marca'}), 404

        nome = request.form.get('nome').title()

        if not nome:
            return jsonify({'mensagem': 'Digite um nome'}), 400

        nome = nome.capitalize().title()
        imagem = request.files.get('imagem')

        cursor.execute("""
            SELECT nome 
            FROM marca 
            WHERE nome = ?
        """, (nome,))
        marca_existente = cursor.fetchone()

        if marca_existente and marca_existente[0] != existe_marca[1]:
            return jsonify({'mensagem': 'Já existe esta marca'}), 404

        cursor.execute("""
            UPDATE marca 
            SET nome = ?  
            WHERE id_marca = ?
        """, (nome, id_marca))

        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "marca")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_marca}.jpg")
            imagem.save(caminho)

        return jsonify({
            'mensagem': 'Marca atualizada com sucesso'
        }), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao editar: {e}'}), 500

    finally:
        cursor.close()


@app.route('/deletar_marca/<int:id_marca>', methods=['DELETE'])
def deletar_marca(id_marca):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_marca, nome      
                        from marca where id_marca=?""", (id_marca,))
    existe_marca = cursor.fetchone()
    if not existe_marca:
        return jsonify({'mensagem': 'Não existe marca'})
    try:
        cursor = con.cursor()
        cursor.execute("""delete from marca where id_marca=?""",
                       (id_marca,))
        con.commit()
        return jsonify({'mensagem': 'Marca deletado com sucesso'})
    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar, marca em mais de uma tabela'}), 400
    finally:
        cursor.close()

@app.route('/buscar_marca', methods=['POST'])
def buscar_marca():
    dados = request.get_json() or {}

    nome = dados.get('nome')
    id_marca = dados.get('id_marca')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    try:
        cursor = con.cursor()
        lista_marcas = []

        if nome:
            nome = nome.upper()

            cursor.execute("""
                SELECT id_marca, nome
                FROM marca 
                WHERE upper(nome) LIKE ?
                ORDER BY nome
            """, (f'%{nome}%',))

        elif id_marca:
            cursor.execute("""
                SELECT id_marca, nome
                FROM marca 
                WHERE id_marca = ?
            """, (id_marca,))

        else:
            cursor.execute("""
                SELECT id_marca, nome
                FROM marca
                ORDER BY nome
            """)

        marcas = cursor.fetchall()

        for marca in marcas:
            id_marca = marca[0]

            lista_marcas.append({
                'id_marca': id_marca,
                'nome': marca[1],
                'imagem': f'{request.host_url}uploads/marca/{id_marca}.jpg'
            })

        return jsonify({'marcas': lista_marcas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao listar marcas: {e}'}), 500

    finally:
        cursor.close()


@app.route('/uploads/marca/<arquivo>', methods=['GET'])
def imagem_marca(arquivo):
    pasta = os.path.join(app.config['UPLOAD_FOLDER'], "marca")
    return send_from_directory(pasta, arquivo)