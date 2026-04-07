from flask import jsonify, request
from main import app, con
from funcao import descobre_tipo_usuario
import os

@app.route("/adicionar_marca", methods=['POST'])
def adicionar_marca():
    dados = request.get_json()
    nome = dados.get('nome')

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()
        cursor.execute("""select 1 from marca where nome = ?""", (nome,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe está marca'}), 400

        cursor.execute("""insert into marca(nome) 
                       values (?)""", (nome,))
        con.commit()

        return jsonify({'mensagem': 'Marca cadastrada com sucesso'}), 403
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar marca'}), 500
    finally:
        cursor.close()

@app.route('/edicao_marca/<int:id_marca>', methods=['PUT'])
def edicao_marca(id_marca):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""select id_marca, nome       
                        from marca where id_marca=?""", (id_marca,))
    existe_marca = cursor.fetchone()
    if not existe_marca:
        return jsonify({'mensagem': 'Não existe marca'})

    dados = request.get_json()
    nome = dados.get('nome')

    try:
        cursor= con.cursor()
        cursor.execute("""update marca 
                        set nome = ?  
                        where id_marca = ?""",
                       (nome, id_marca))
        con.commit()
        return jsonify({
            'mensagem': 'Marca atualizado com sucesso',}), 201
    except Exception as e:
        return jsonify({'mensagem': 'erro ao editar'})

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
        return jsonify({'mensagem': 'erro ao deletar servico em mais de uma tabela'})
    finally:
        cursor.close()

@app.route('/buscar_marca', methods=['POST'])
def buscar_marca():
    dados = request.get_json()
    nome = dados.get('nome')
    id_marca = dados.get('id_marca')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'Usuário não logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_marcas = []

        if nome :
            nome = nome.upper()
            cursor.execute("""
                SELECT nome
                FROM marca 
                WHERE upper(nome) LIKE ?
            """, (f'%{nome}%',))


        elif id_marca:
            cursor.execute("""
                SELECT nome
                FROM marca 
                WHERE id_marca = ?
            """, (id_marca,))

        else:
            cursor.execute("""
                SELECT nome
                FROM marca
            """)

        marcas = cursor.fetchall()

        for marca in marcas:
            lista_marcas.append({
                'nome': marca[0],
            })

        if not lista_marcas:
            return jsonify({'mensagem': 'Marca não encontrado'}), 404

        return jsonify({'marcas': lista_marcas}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar marcas'}), 500

    finally:
        cursor.close()