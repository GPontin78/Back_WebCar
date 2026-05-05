from flask import jsonify, request, send_from_directory
from main import app, con
from funcao import descobre_tipo_usuario
import os



@app.route('/adicionar_empresa', methods=['POST'])
def adicionar_empresa():
    cnpj = request.form.get('cnpj')
    nome_fantasia = request.form.get('nome_fantasia').title()
    razao_social = request.form.get('razao_social').title()
    cidade = request.form.get('cidade').title()
    porcentagem_juro = float(request.form.get('porcentagem_juro'))
    inscricao_estadual = request.form.get('inscricao_estadual')
    cep = int(request.form.get('cep'))
    rua = request.form.get('rua').title()
    uf = int(request.form.get('uf'))
    numero_endereco = int(request.form.get('numero_endereco'))
    agencia = int(request.form.get('agencia'))
    conta = int(request.form.get('conta'))
    chave_pix = int(request.form.get('chave_pix'))
    banco = int(request.form.get('banco'))
    porcentagem_lucro = float(request.form.get('porcentagem_lucro'))
    imagem = request.files.get('imagem')

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""select 1 from empresa where cnpj = ?""",(cnpj,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Esta empresa já existe'}), 400

        cursor.execute("""select 1 from empresa where inscricao_estadual = ?""",(inscricao_estadual,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Esta empresa já existe'}), 400

        if not cnpj:
            return jsonify({'mensagem': 'Digite um cnpj'}), 400

        if not inscricao_estadual:
            return jsonify({'mensagem': 'Digite um inscricao_estadual'}), 400

        cursor.execute("""
            insert into empresa
            (cnpj, nome_fantasia, razao_social, cidade, porcentagem_juro, inscricao_estadual,
             cep, rua, uf, numero_endereco, agencia, conta, chave_pix, banco, porcentagem_lucro)
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            RETURNING id_empresa
        """,
        (cnpj, nome_fantasia, razao_social, cidade, porcentagem_juro, inscricao_estadual,
         cep, rua, uf, numero_endereco, agencia, conta, chave_pix, banco, porcentagem_lucro))

        id_empresa = cursor.fetchone()[0]
        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "empresa")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_empresa}.jpg")
            imagem.save(caminho)

        return jsonify({
            'mensagem': 'Empresa cadastrada com sucesso',
            'id_empresa': id_empresa
        }), 201

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao cadastrar empresa: {e}'}), 500

    finally:
        cursor.close()



@app.route('/edicao_empresa/<int:id_empresa>', methods=['PUT'])
def edicao_empresa(id_empresa):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT id_empresa, cnpj FROM empresa WHERE id_empresa = ?
        """, (id_empresa,))
        existe_empresa = cursor.fetchone()

        if not existe_empresa:
            return jsonify({'mensagem': 'Não existe empresa'}), 404

        cnpj = request.form.get('cnpj')
        nome_fantasia = request.form.get('nome_fantasia').title()
        razao_social = request.form.get('razao_social').title()
        cidade = request.form.get('cidade').title()
        porcentagem_juro = float(request.form.get('porcentagem_juro'))
        inscricao_estadual = request.form.get('inscricao_estadual')
        cep = int(request.form.get('cep'))
        rua = request.form.get('rua').title()
        uf = int(request.form.get('uf'))
        numero_endereco = int(request.form.get('numero_endereco'))
        agencia = int(request.form.get('agencia'))
        conta = int(request.form.get('conta'))
        chave_pix = int(request.form.get('chave_pix'))
        banco = int(request.form.get('banco'))
        porcentagem_lucro = float(request.form.get('porcentagem_lucro'))
        imagem = request.files.get('imagem')

        cursor.execute("""
            UPDATE empresa SET
                cnpj = ?,
                nome_fantasia = ?,
                razao_social = ?,
                cidade = ?,
                porcentagem_juro = ?,
                inscricao_estadual = ?,
                cep = ?,
                rua = ?,
                uf = ?,
                numero_endereco = ?,
                agencia = ?,
                conta = ?,
                chave_pix = ?,
                banco = ?,
                porcentagem_lucro = ?
            WHERE id_empresa = ?
        """, (
            cnpj, nome_fantasia, razao_social, cidade, porcentagem_juro,
            inscricao_estadual, cep, rua, uf, numero_endereco,
            agencia, conta, chave_pix, banco, porcentagem_lucro,
            id_empresa
        ))

        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "empresa")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, f"{id_empresa}.jpg")
            imagem.save(caminho)

        return jsonify({'mensagem': 'Empresa atualizada com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao editar empresa: {e}'}), 500

    finally:
        cursor.close()

@app.route('/deletar_empresa/<int:id_empresa>', methods=['DELETE'])
def deletar_empresa(id_empresa):
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode editar'}), 403

    cursor = con.cursor()
    cursor.execute("""
        select id_empresa, cnpj
        from empresa where id_empresa=?
    """, (id_empresa,))
    existe_empresa = cursor.fetchone()

    if not existe_empresa:
        return jsonify({'mensagem': 'Não existe empresa'})

    try:
        cursor = con.cursor()
        cursor.execute("""
            delete from empresa where id_empresa=?
        """, (id_empresa,))
        con.commit()

        return jsonify({'mensagem': 'Empresa deletada com sucesso'}), 300

    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar empresa'}), 404

    finally:
        cursor.close()
