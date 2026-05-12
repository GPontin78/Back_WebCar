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
    uf = request.form.get('uf').upper()
    numero_endereco = int(request.form.get('numero_endereco'))
    agencia = int(request.form.get('agencia'))
    conta = request.form.get('conta')
    chave_pix = request.form.get('chave_pix')
    banco = int(request.form.get('banco'))
    porcentagem_lucro = float(request.form.get('porcentagem_lucro'))
    desconto_a_vista = float(request.form.get('desconto_a_vista'))
    cor_primaria = request.form.get('cor_primaria')
    cor_secundaria = request.form.get('cor_secundaria')
    cor_terciaria = request.form.get('cor_terciaria')
    cor_fonte = request.form.get('cor_fonte')
    descricao = request.form.get('descricao')
    fonte = request.form.get('fonte')
    logo = request.files.get('logo')
    banner = request.files.get('banner')

    tipo_usuario = descobre_tipo_usuario()
    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode cadastrar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""select 1 from empresa where cnpj = ?""", (cnpj,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Esta empresa já existe'}), 400

        cursor.execute("""select 1 from empresa where inscricao_estadual = ?""", (inscricao_estadual,))
        if cursor.fetchone():
            return jsonify({'mensagem': 'Esta empresa já existe'}), 400

        if not cnpj:
            return jsonify({'mensagem': 'Digite um cnpj'}), 400

        if not inscricao_estadual:
            return jsonify({'mensagem': 'Digite um inscricao_estadual'}), 400

        cursor.execute("""
            insert into empresa
            (
                cnpj,
                nome_fantasia,
                razao_social,
                cidade,
                porcentagem_juro,
                inscricao_estadual,
                cep,
                rua,
                uf,
                numero_endereco,
                agencia,
                conta,
                chave_pix,
                banco,
                porcentagem_lucro,
                desconto_a_vista,
                cor_primaria,
                cor_secundaria,
                cor_terciaria,
                cor_fonte,
                descricao,
                fonte
            )
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            RETURNING id_empresa
        """, (
            cnpj,
            nome_fantasia,
            razao_social,
            cidade,
            porcentagem_juro,
            inscricao_estadual,
            cep,
            rua,
            uf,
            numero_endereco,
            agencia,
            conta,
            chave_pix,
            banco,
            porcentagem_lucro,
            desconto_a_vista,
            cor_primaria,
            cor_secundaria,
            cor_terciaria,
            cor_fonte,
            descricao,
            fonte
        ))

        id_empresa = cursor.fetchone()[0]
        con.commit()

        pasta = os.path.join(app.config['UPLOAD_FOLDER'], "empresa")
        os.makedirs(pasta, exist_ok=True)

        if logo:
            caminho_logo = os.path.join(pasta, f"logo_{id_empresa}.jpg")
            logo.save(caminho_logo)

        if banner:
            caminho_banner = os.path.join(pasta, f"banner_{id_empresa}.jpg")
            banner.save(caminho_banner)

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
            SELECT id_empresa, cnpj
            FROM empresa 
            WHERE id_empresa = ?
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
        uf = request.form.get('uf').upper()
        numero_endereco = int(request.form.get('numero_endereco'))
        agencia = int(request.form.get('agencia'))
        conta = request.form.get('conta')
        chave_pix = request.form.get('chave_pix')
        banco = int(request.form.get('banco'))
        porcentagem_lucro = float(request.form.get('porcentagem_lucro'))
        desconto_a_vista = float(request.form.get('desconto_a_vista'))
        cor_primaria = request.form.get('cor_primaria')
        cor_secundaria = request.form.get('cor_secundaria')
        cor_terciaria = request.form.get('cor_terciaria')
        cor_fonte = request.form.get('cor_fonte')
        descricao = request.form.get('descricao')
        fonte = request.form.get('fonte')
        logo = request.files.get('logo')
        banner = request.files.get('banner')

        if not cnpj:
            return jsonify({'mensagem': 'Digite um CNPJ'}), 400

        if not inscricao_estadual:
            return jsonify({'mensagem': 'Digite uma inscrição estadual'}), 400

        cursor.execute("""
            SELECT id_empresa 
            FROM empresa 
            WHERE cnpj = ? 
            AND id_empresa <> ?
        """, (cnpj, id_empresa))

        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe uma empresa com este CNPJ'}), 400

        cursor.execute("""
            SELECT id_empresa 
            FROM empresa 
            WHERE inscricao_estadual = ? 
            AND id_empresa <> ?
        """, (inscricao_estadual, id_empresa))

        if cursor.fetchone():
            return jsonify({'mensagem': 'Já existe uma empresa com esta inscrição estadual'}), 400

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
                porcentagem_lucro = ?,
                desconto_a_vista = ?,
                cor_primaria = ?,
                cor_secundaria = ?,
                cor_terciaria = ?,
                cor_fonte = ?,
                descricao = ?,
                fonte = ?
            WHERE id_empresa = ?
        """, (
            cnpj,
            nome_fantasia,
            razao_social,
            cidade,
            porcentagem_juro,
            inscricao_estadual,
            cep,
            rua,
            uf,
            numero_endereco,
            agencia,
            conta,
            chave_pix,
            banco,
            porcentagem_lucro,
            desconto_a_vista,
            cor_primaria,
            cor_secundaria,
            cor_terciaria,
            cor_fonte,
            descricao,
            fonte,
            id_empresa
        ))

        con.commit()

        pasta = os.path.join(app.config['UPLOAD_FOLDER'], "empresa")
        os.makedirs(pasta, exist_ok=True)

        if logo:
            caminho_logo = os.path.join(pasta, f"logo_{id_empresa}.jpg")
            logo.save(caminho_logo)

        if banner:
            caminho_banner = os.path.join(pasta, f"banner_{id_empresa}.jpg")
            banner.save(caminho_banner)

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
        return jsonify({'mensagem': 'Não existe empresa'}), 404

    try:
        cursor.execute("""
            delete from empresa where id_empresa=?
        """, (id_empresa,))
        con.commit()

        return jsonify({'mensagem': 'Empresa deletada com sucesso'}), 200

    except Exception as e:
        return jsonify({'mensagem': 'Erro ao deletar empresa'}), 404

    finally:
        cursor.close()


@app.route('/verdadosempresa', methods=['GET'])
def verdadosempresa():
    tipo_usuario = descobre_tipo_usuario()

    if tipo_usuario != 0:
        return jsonify({'mensagem': 'Apenas Adm pode visualizar'}), 403

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT 
                id_empresa,
                cnpj,
                nome_fantasia,
                razao_social,
                cidade,
                porcentagem_juro,
                inscricao_estadual,
                cep,
                rua,
                uf,
                numero_endereco,
                agencia,
                conta,
                chave_pix,
                banco,
                porcentagem_lucro,
                desconto_a_vista,
                cor_primaria,
                cor_secundaria,
                cor_terciaria,
                cor_fonte,
                descricao,
                fonte
            FROM empresa
            ORDER BY id_empresa
        """)

        empresas = cursor.fetchall()
        lista_empresas = []

        for empresa in empresas:
            id_empresa = empresa[0]

            lista_empresas.append({
                'id_empresa': id_empresa,
                'cnpj': empresa[1],
                'nome_fantasia': empresa[2],
                'razao_social': empresa[3],
                'cidade': empresa[4],
                'porcentagem_juro': empresa[5],
                'inscricao_estadual': empresa[6],
                'cep': empresa[7],
                'rua': empresa[8],
                'uf': empresa[9],
                'numero_endereco': empresa[10],
                'agencia': empresa[11],
                'conta': empresa[12],
                'chave_pix': empresa[13],
                'banco': empresa[14],
                'porcentagem_lucro': empresa[15],
                'desconto_a_vista': empresa[16],
                'cor_primaria': empresa[17],
                'cor_secundaria': empresa[18],
                'cor_terciaria': empresa[19],
                'cor_fonte': empresa[20],
                'descricao': empresa[21],
                'texto_banner': empresa[21],
                'fonte': empresa[22],
                'logo_url': f'{request.host_url}uploads/empresa/logo_{id_empresa}.jpg',
                'banner_url': f'{request.host_url}uploads/empresa/banner_{id_empresa}.jpg'
            })

        if not lista_empresas:
            return jsonify({'mensagem': 'Nenhuma empresa encontrada'}), 404

        return jsonify({'empresas': lista_empresas}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar empresa: {e}'}), 500

    finally:
        cursor.close()


@app.route('/uploads/empresa/<arquivo>', methods=['GET'])
def imagem_empresa(arquivo):
    pasta = os.path.join(app.config['UPLOAD_FOLDER'], "empresa")
    return send_from_directory(pasta, arquivo)