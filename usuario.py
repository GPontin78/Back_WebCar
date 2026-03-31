from flask import jsonify, request, make_response,  render_template
from main import app, con
from funcao import validar_senha, gerar_token,descobre_tipo_usuario, descobre_id_usuario, gerar_codigo,enviando_email,senha_repetida
from flask_bcrypt import generate_password_hash,check_password_hash
import os
import threading


@app.route('/adicionar_usuario', methods=['POST'])
def adicionar_usuario():
    nome = request.form.get('nome')
    email = request.form.get('email').lower()
    telefone = request.form.get('telefone')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')
    tipo = request.form.get('tipo')
    imagem = request.files.get('imagem')

    validado = validar_senha(senha)

    if not nome or not nome.strip():
        return jsonify({'mensagem': 'Nome é obrigatório'}), 400

    if not validado:
        return jsonify({'mensagem': 'Senha fora do padrão'}), 400

    tipo_usuario = descobre_tipo_usuario()

    if tipo == "0" or tipo == "1" :
        if tipo_usuario is None: # isso significa que a funcao returnou null entao, o usuario nao esta logado
            return jsonify({'mensagem': 'usuario nao logado'}), 403

        if tipo_usuario != 0:
            return jsonify({'mensagem': 'Apenas ADM pode cadastrar ADM ou VENDEDOR'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("SELECT 1 FROM USUARIO WHERE EMAIL = ?", (email,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Email já cadastrado'}), 400

        cursor.execute("SELECT 1 FROM USUARIO WHERE cpf = ?", (cpf,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'CPF já cadastrado'}), 400

        senha_hash = generate_password_hash(senha).decode('utf-8')

        cursor.execute("""
            INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, CPF, SENHA, TIPO,SITUACAO, TENTATIVA)
            VALUES (?, ?, ?, ?, ?, ?, 2, 1)
            RETURNING ID_USUARIO
        """, (nome, email, telefone, cpf, senha_hash, tipo))

        id_usuario = cursor.fetchone()[0]
        con.commit()
        cursor.execute("""
        INSERT INTO historico_senha(id_usuario, senha_anterior)
                       VALUES (?,?)""",(id_usuario, senha_hash))
        con.commit()

        codigo = gerar_codigo()

        cursor.execute("""
                       INSERT INTO recuperacao_senha (id_usuario, codigo)
                       VALUES (?, ?)
                       """, (id_usuario, codigo))

        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "Usuarios")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_usuario}.jpg")
            imagem.save(caminho)

        html = render_template('codigo_verificacao.html', codigo=codigo)

        try:
            thread = threading.Thread(
                target=enviando_email,
                args=(email, html)
            )
            thread.start()
        except Exception as e:
            return jsonify({"messagem": f"Erro ao enviar email: {e}"}), 500

        return jsonify({
            'mensagem': 'Usuário cadastrado com sucesso',
            'id_usuario': id_usuario
        }), 201

    except Exception as e:
        return jsonify({'mensagem': f'Erro: {e}'}), 500

    finally:
        cursor.close()



@app.route('/verificar_email', methods=['POST'])
def verificar_email():
    dados = request.get_json()
    email = dados.get('email')
    codigo = int(dados.get('codigo'))

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT u.id_usuario, r.codigo
            FROM usuario u
            INNER JOIN recuperacao_senha r ON u.id_usuario = r.id_usuario
            WHERE u.email = ?
        """, (email,))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'mensagem': 'Código inválido'}), 400

        id_usuario = resultado[0]
        codigo_banco = int(resultado[1])

        if codigo != codigo_banco:
            return jsonify({'mensagem': 'Código inválido'}), 400

        cursor.execute("""
            UPDATE usuario
            SET situacao = 0
            WHERE id_usuario = ?
        """, (id_usuario,))

        cursor.execute("""
            DELETE FROM recuperacao_senha
            WHERE id_usuario = ?
        """, (id_usuario,))

        con.commit()

        return jsonify({'mensagem': 'Email verificado com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao verificar email: {e}'}), 500

    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email').lower()
    senha = dados.get('senha')

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT ID_USUARIO, NOME, EMAIL, SENHA, TIPO, SITUACAO, TENTATIVA
            FROM USUARIO
            WHERE EMAIL = ?
        """, (email,))
        dados_do_banco = cursor.fetchone()

        if not dados_do_banco:
            return jsonify({'mensagem': 'Email ou senha invalida'}), 401

        id_usuario = dados_do_banco[0]
        nome = dados_do_banco[1]
        email_banco = dados_do_banco[2]
        senha_escritanobanco = dados_do_banco[3]
        tipo = dados_do_banco[4]
        situacao = dados_do_banco[5]
        tentativa = dados_do_banco[6]

        if situacao == 2:
            return jsonify({'mensagem': 'Verifique seu email antes de logar'}), 403

        if not check_password_hash(senha_escritanobanco, senha):
            cursor.execute(
                'UPDATE USUARIO SET TENTATIVA = TENTATIVA + 1 WHERE EMAIL = ?',
                (email,)
            )

            if tentativa == 3 and tipo != 0:
                cursor.execute(
                    'UPDATE USUARIO SET SITUACAO = 1 WHERE EMAIL = ?',
                    (email,)
                )
                con.commit()
                return jsonify({'mensagem': 'usuario bloqueado entre em contato com o adm'})

            con.commit()
            return jsonify({'mensagem': 'Email ou senha invalida'}), 401

        if situacao == 1:
            return jsonify({'mensagem': 'USUARIO BLOQUEADO'})

        token = gerar_token(id_usuario, tipo)

        cursor.execute('UPDATE USUARIO SET TENTATIVA = 1 WHERE EMAIL = ?', (email,))
        con.commit()

        resposta = make_response(jsonify({
            'mensagem': 'login com sucesso',
            'usuario': {
                'id': id_usuario,
                'nome': nome,
                'email': email_banco,
                'tipo': tipo
            }
        }), 200)

        resposta.set_cookie(
            'access_token',
            token,
            httponly=True,
            secure=False,
            samesite='Lax',
            path="/",
            max_age=3600
        )

        return resposta

    except Exception as e:
        return jsonify({'mensagem': f'Erro no login: {e}'}), 500

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
    if tipo_usuario != 0:
        if id_usuario_logado != id_usuario:
            return jsonify({'mensagem': 'usuario nao pertence a essa conta'}), 403

    cursor = con.cursor()
    cursor.execute(""" SELECT NOME, EMAIL, TELEFONE, CPF, SENHA, TIPO
                                            FROM USUARIO
                                    WHERE ID_USUARIO = ? """, (id_usuario,))
    existe_usuario = cursor.fetchone()

    if not existe_usuario:# ve se tem o usuario
        return jsonify({'mensage': 'Usuário não encontrado'})


    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cpf = request.form.get('cpf')
    imagem = request.files.get('imagem')

    try:
        cursor = con.cursor()
        cursor.execute("SELECT 1 FROM USUARIO WHERE EMAIL = ? AND ID_USUARIO != ?", (email, id_usuario))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Email já cadastrado'}), 400

        cursor.execute("SELECT 1 FROM USUARIO WHERE cpf = ? AND ID_USUARIO != ?", (cpf, id_usuario))
        if cursor.fetchone():
            return jsonify({'mensagem': 'cpf já cadastrado'}), 400


        cursor.execute('update usuario set nome=?, email=?, cpf=?, telefone=? where id_usuario = ?',
                   (nome, email, cpf, telefone, id_usuario))
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

    if tipo_usuario is None:  # isso significa que a funcao returnou null entao, o usuario nao esta logado
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario !=0:
        return jsonify({'mensagem': 'Apenas ADM Pode deletar'})
    try:
        cursor = con.cursor()
        cursor.execute('select 1 from usuario where id_usuario = ?', (id_usuario,))
        if not cursor.fetchone():
            return jsonify({'mensagem': 'Usuário nao encontrado'})

        cursor.execute('delete from usuario where id_usuario = ?', (id_usuario,))
        con.commit()
        return jsonify({'mensagem': 'Usuário deletado com sucesso'})

    except Exception as e:
        return jsonify({'mensagem': 'erro ao deletar usuario em mais de uma tabela'})
    finally:
        cursor.close()

@app.route('/esqueci_senha', methods=['POST'])
def esqueci_senha():
    dados = request.get_json()
    email = dados.get('email')

    try:
        cursor = con.cursor()

        cursor.execute("SELECT id_usuario FROM usuario WHERE email = ?", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({'mensagem': 'Email não encontrado'}), 404

        id_usuario = usuario[0]
        codigo = gerar_codigo()

        cursor.execute("DELETE FROM recuperacao_senha WHERE id_usuario = ?", (id_usuario,))

        cursor.execute("""
            INSERT INTO recuperacao_senha (id_usuario, codigo)
            VALUES (?, ?)
        """, (id_usuario, codigo))

        con.commit()
        html = render_template('codigo_verificacao.html', codigo=codigo)

        thread = threading.Thread(
            target=enviando_email,
            args=(email, html)
        )
        thread.start()

        return jsonify({'mensagem': 'Código enviado com sucesso'}), 200

    except:
        return jsonify({'mensagem': 'Erro ao enviar código'}), 500

    finally:
        cursor.close()

@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo():
    dados = request.get_json()
    email = dados.get('email')
    codigo = int(dados.get('codigo'))

    try:
        cursor = con.cursor()
        cursor.execute("""
            SELECT r.codigo
            FROM usuario u
            INNER JOIN recuperacao_senha r ON u.id_usuario = r.id_usuario
            WHERE u.email = ?
        """, (email,))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'mensagem': 'Código inválido'}), 400

        codigo_banco = int(resultado[0])

        if codigo != codigo_banco:
            return jsonify({'mensagem': 'Código inválido'}), 400

        return jsonify({'mensagem': 'Código válido'}), 200

    except:
        return jsonify({'mensagem': 'Erro ao verificar código'}), 500

    finally:
        cursor.close()
@app.route('/trocar_senha', methods=['POST'])
def trocar_senha():
    dados = request.get_json()
    email = dados.get('email')
    codigo = dados.get('codigo')
    nova_senha = dados.get('nova_senha')
    confirmar_senha = dados.get('confirmar_senha')
    valida = validar_senha(nova_senha)

    if nova_senha != confirmar_senha:
        return jsonify({'mensagem': 'Senhas não coincidem'}), 400
    if not valida:
        return jsonify({'mensagem': 'Senhas fraca'}), 400

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT u.id_usuario, u.senha
            FROM usuario u
            INNER JOIN recuperacao_senha r ON u.id_usuario = r.id_usuario
            WHERE u.email = ? AND r.codigo = ?
        """, (email, codigo))

        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({'mensagem': 'Código inválido'}), 400

        id_usuario = usuario[0]
        senha_atual = usuario[1]

        if senha_repetida(id_usuario, nova_senha):
            return jsonify({'mensagem': 'Não pode repetir as últimas 3 senhas'}), 400

        nova_senha_hash = generate_password_hash(nova_senha).decode('utf-8')

        cursor.execute("""
            INSERT INTO historico_senha (id_usuario, senha_anterior)
            VALUES (?, ?)
        """, (id_usuario, senha_atual))

        cursor.execute("""
            UPDATE usuario
            SET senha = ?
            WHERE id_usuario = ?
        """, (nova_senha_hash, id_usuario))

        cursor.execute("""
            DELETE FROM recuperacao_senha
            WHERE id_usuario = ?
        """, (id_usuario,))

        con.commit()
        cursor.execute("""
            DELETE FROM historico_senha
            WHERE id_usuario = ?
            AND id_historico_senha NOT IN (
                SELECT FIRST 3 id_historico_senha
                FROM historico_senha
                WHERE id_usuario = ?
                ORDER BY id_historico_senha DESC
            )
        """, (id_usuario, id_usuario))

        con.commit()

        return jsonify({'mensagem': 'Senha alterada com sucesso'}), 200

    except:
        return jsonify({'mensagem': 'Erro ao trocar senha'}), 500

    finally:
        cursor.close()

@app.route('/buscar_usuario', methods=['POST'])
def buscar_usuario():
    dados = request.get_json()
    nome = dados.get('nome')
    id_usuario = dados.get('id_usuario')

    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario is None:
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas ADM pode acessar'}), 403

    try:
        cursor = con.cursor()
        lista_usuarios = []

        if nome:
            cursor.execute("""
                SELECT id_usuario, nome, email, cpf, telefone 
                FROM usuario 
                WHERE nome LIKE ?
            """, (f'%{nome}%',))

        elif id_usuario:
            cursor.execute("""
                SELECT id_usuario, nome, email, cpf, telefone 
                FROM usuario 
                WHERE id_usuario = ?
            """, (id_usuario,))

        else:
            cursor.execute("""
                SELECT id_usuario, nome, email, cpf, telefone 
                FROM usuario
            """)

        usuarios = cursor.fetchall()

        for usuario in usuarios:
            lista_usuarios.append({
                'id_usuario': usuario[0],
                'nome': usuario[1],
                'email': usuario[2],
                'cpf': usuario[3],
                'telefone': usuario[4]
            })

        if not lista_usuarios:
            return jsonify({'mensagem': 'Usuário não encontrado'}), 404

        return jsonify({'usuarios': lista_usuarios}), 200

    except:
        return jsonify({'mensagem': 'Erro ao listar usuários'}), 500

    finally:
        cursor.close()


@app.route('/alterar_situacao/<int:id_usuario>', methods=['PUT'])
def alterar_situacao(id_usuario):
    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario is None:
        return jsonify({'mensagem': 'usuario nao logado'}), 403

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'sem permissao, apenas adm pode mudar a situação'}), 403

    try:
        situacao = request.form.get('situacao')

        if situacao is None:
            return jsonify({'mensagem': 'situacao obrigatoria'}), 400

        try:
            situacao = int(situacao)
        except:
            return jsonify({'mensagem': 'situacao deve ser 0 ou 1'}), 400

        # Validação: só 0 ou 1
        if situacao != 1 and situacao != 0:
            return jsonify({'mensagem': 'situacao invalida (use 0 ou 1)'}), 400

        cursor = con.cursor()

        cursor.execute(
            'UPDATE usuario SET situacao = ? WHERE id_usuario = ?',
            (situacao, id_usuario)
        )

        con.commit()
        return jsonify({'mensagem': 'situacao atualizada com sucesso'}), 200

    except Exception as e:
        return jsonify({'erro no mudar situação'}), 500