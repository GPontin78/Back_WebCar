from flask import jsonify, request, make_response
from main import app, con
from funcao import validar_senha, gerar_token
from flask_bcrypt import generate_password_hash, check_password_hash
import os
import jwt
#

@app.route('/adicionar_usuario', methods=['POST'])
def adicionar_usuario():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')
    tipo = request.form.get('tipo')
    imagem = request.files.get('imagem')

    if not tipo:
        return jsonify({'mensagem': 'Tipo é obrigatório'}), 400

    try:
        tipo = int(tipo)
    except ValueError:
        return jsonify({'mensagem': 'Tipo inválido'}), 400

    if tipo not in [0, 1, 2]:
        return jsonify({'mensagem': 'Tipo deve ser 0, 1 ou 2'}), 400

    if not senha:
        return jsonify({'mensagem': 'Senha é obrigatória'}), 400

    validar = validar_senha(senha)
    if not validar:
        return jsonify({'mensagem': 'A senha nao esta nos nossos rigorossos padroes de segurança'}), 400

    token = request.cookies.get('access_token')
    tipo_usuario = None

    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            tipo_usuario = payload['tipo']
        except jwt.ExpiredSignatureError:
            if tipo != 2:
                return jsonify({'mensagem': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            if tipo != 2:
                return jsonify({'mensagem': 'Token invalido'}), 401

    # sem token válido, só pode cadastro público tipo 2
    if tipo_usuario is None:
        if tipo != 2:
            return jsonify({'mensagem': 'Token necessário para cadastrar este tipo de usuário'}), 401
    else:
        permitido = False

        if tipo_usuario == 0:
            permitido = tipo in [0, 1, 2]
        elif tipo_usuario == 1:
            permitido = tipo in [1, 2]
        elif tipo_usuario == 2:
            permitido = tipo == 2

        if not permitido:
            return jsonify({'mensagem': 'Acesso negado para cadastrar esse tipo de usuário'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("SELECT 1 FROM USUARIO WHERE EMAIL = ?", (email,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Email já cadastrado'}), 400

        senha_cripyto = generate_password_hash(senha).decode('utf-8')

        cursor.execute("""
            INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, CPF, SENHA, TIPO)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING ID_USUARIO
        """, (nome, email, telefone, cpf, senha_cripyto, tipo))

        id_usuario = cursor.fetchone()[0]
        con.commit()

        if imagem:
            pasta_usuario = os.path.join(app.config['UPLOAD_FOLDER'], "Usuarios")
            os.makedirs(pasta_usuario, exist_ok=True)

            caminho_imagem = os.path.join(pasta_usuario, f"{id_usuario}.jpg")
            imagem.save(caminho_imagem)

        return jsonify({
            'message': 'Usuário cadastrado com sucesso',
            'id_usuario': id_usuario
        }), 201

    except Exception as e:
        return jsonify({'mensagem': f'Erro no cadastro: {e}'}), 500

    finally:
        cursor.close()
@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha')
    try:
        cursor = con.cursor()

        cursor.execute("""SELECT ID_USUARIO, email, SENHA, TIPO FROM USUARIO WHERE email = ? """, (email,))
        verifica = cursor.fetchone()

        if not verifica:
            return jsonify({'mensagem': 'Email ou senha invalida'}), 401
        senha_escritanobanco = verifica[2]
        tipo = verifica[3]
        id_usuario = verifica[0]

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
        return jsonify({'mensagem': 'Deu ruim no login'}), 500
    finally:
        cursor.close()

