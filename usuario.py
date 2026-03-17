
from flask import jsonify, request,make_response
from main import app, con
from funcao import validar_senha, gerar_token,descobre_tipo_usuario, descobre_id_usuario
from flask_bcrypt import generate_password_hash,check_password_hash
import os
import jwt

@app.route('/adicionar_usuario', methods=['POST'])
def adicionar_usuario():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')
    tipo = int(request.form.get('tipo'))
    imagem = request.files.get('imagem')

    validado = validar_senha(senha)

    if not validado:
        return jsonify({'mensagem': 'Senha fora do padrão'}), 400

    tipo_usuario = descobre_tipo_usuario()

    if tipo == 0 or tipo == 1 :
        if tipo_usuario is None: # isso significa que a funcao returnou null entao, o usuario nao esta logado
            return jsonify({'mensagem': 'usuario nao logado'}), 403

        if tipo_usuario != 0:
            return jsonify({'mensagem': 'Apenas ADM pode cadastrar ADM ou VENDEDOR'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("SELECT 1 FROM USUARIO WHERE EMAIL = ?", (email,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Email já cadastrado'}), 400

        senha_hash = generate_password_hash(senha).decode('utf-8')

        cursor.execute("""
            INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, CPF, SENHA, TIPO,SITUACAO, TENTATIVA)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            RETURNING ID_USUARIO
        """, (nome, email, telefone, cpf, senha_hash, tipo))

        id_usuario = cursor.fetchone()[0]
        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "Usuarios")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_usuario}.jpg")
            imagem.save(caminho)

        return jsonify({
            'mensagem': 'Usuário cadastrado com sucesso',
            'id_usuario': id_usuario
        }), 201

    except Exception as e:
        return jsonify({'mensagem': f'Erro: {e}'}), 500

    finally:
        cursor.close()
@app.route('/login', methods=['POST'])
def login():   # verifica a situaçao e  tentativa de senha do animal
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha')
    try:
        cursor = con.cursor()

        cursor.execute("""SELECT ID_USUARIO, email, SENHA, TIPO FROM USUARIO WHERE email = ? """, (email,))
        dados_do_banco = cursor.fetchone()

        if not dados_do_banco:
            return jsonify({'mensagem': 'Email ou senha invalida'}), 401
        senha_escritanobanco = dados_do_banco[2]
        tipo = dados_do_banco[3]
        id_usuario = dados_do_banco[0]

        if not check_password_hash(senha_escritanobanco, senha):
            return jsonify({'mensagem': 'Email ou senha invalida'}), 401

        token = gerar_token(id_usuario, tipo)
        resposta = make_response(jsonify({'mensagem': 'login com sucesso'}), 200)
        resposta.set_cookie('access_token', token,
                            httponly=True,
                            secure=False,
                            samesite='Lax',
                            path="/",
                            max_age=3600)
        return resposta
    except Exception as e:
        return jsonify({'mensagem': 'Erro no login'}), 500
    finally:
        cursor.close()




@app.route('/logout', methods=['POST'])
def logout():
    resposta = make_response(jsonify({'mensagem': 'Logout realizado com sucesso'}), 200)
    resposta.set_cookie(
        'access_token',
        '',
        expires=0,
        path='/'
    )
    return resposta


@app.route('/edicao_usuario/<int:id_usuario>', methods=['PUT'])
def edicao_usuario(id_usuario):

    tipo_usuario = descobre_tipo_usuario()
    id_usuario_logado = descobre_id_usuario()
    if tipo_usuario is None: # isso significa que a funcao returnou null entao, o usuario nao esta logado
        return jsonify({'mensagem': 'usuario nao logado'}), 403
    if id_usuario_logado != id_usuario:
        return jsonify({'mensagem': 'usuario nao pertence a essa conta'}), 403

    cursor = con.cursor()
    cursor.execute(""" SELECT NOME, EMAIL, TELEFONE, CPF, SENHA TIPO
                                            FROM USUARIO
                                    WHERE ID_USUARIO = ? """, (id_usuario,))
    existe_usuario = cursor.fetchone()

    if not existe_usuario:# ve se tem o usuario
        return jsonify({'mensage': 'Usuário não encontrado'})


    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')

    imagem = request.files.get('imagem')

    validado = validar_senha(senha)

    try:
        cursor = con.cursor()
        if not validado:
            return jsonify({"error": "A senha nao esta nos nossos rigorossos padroes de segurança"}), 400
        senha_hash = generate_password_hash(senha).decode('utf-8')

        cursor.execute("SELECT 1 FROM USUARIO WHERE EMAIL = ?", (email,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Email já cadastrado'}), 400

        cursor.execute('update usuario set nome=?, email=?, cpf=?, telefone=?, senha=? where id_usuario = ?',
                   (nome, email, cpf, telefone, senha_hash, id_usuario))
        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "Usuarios")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_usuario}.jpg")
            imagem.save(caminho)

        return jsonify({
            'mensagem': 'Usuário atualizado com sucesso',
            'id_usuario': id_usuario
        }), 201

    except Exception as e:
        return jsonify({'mensagem': 'erro ao editar'})

@app.route('/deletar_usuario/<int:id_usuario>', methods=['DELETE'])
def deletar_usuario(id_usuario):

    tipo_usuario = descobre_tipo_usuario()
    id_usuario_logado = descobre_id_usuario()

    if tipo_usuario is None:  # isso significa que a funcao returnou null entao, o usuario nao esta logado
        return jsonify({'mensagem': 'usuario nao logado'}), 403
    if id_usuario_logado != id_usuario:
        return jsonify({'mensagem': 'usuario nao pertence a essa conta'}), 403

    try:
        cursor = con.cursor()
        cursor.execute('select 1 from usuario where id_usuario = ?', (id_usuario,))
        if not cursor.fetchone():
            return jsonify({'mensagem': 'usuario nao encontrado'})
        if cursor.fetchone():
            cursor.execute('delete from usuario where id_usuario = ?', (id_usuario,))
            con.commit()
            return jsonify({'mensagem': 'usuario deletado com sucesso'})

    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar'})
    finally:
        cursor.close()