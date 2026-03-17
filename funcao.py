import jwt
import datetime
from main import app, con
from flask import request
import random
import smtplib
from email.mime.text import MIMEText
from flask_bcrypt import check_password_hash


senha_secreta = app.config['SECRET_KEY']

def validar_senha(senha):
    if not senha:
        return False

    maiuscula = minuscula = numero = especial = False

    for s in senha:
        if s.isupper():
            maiuscula = True
        elif s.islower():
            minuscula = True
        elif s.isdigit():
            numero = True
        elif not s.isalnum():
            especial = True

    if len(senha) < 8 or len(senha) > 12:
        return False

    if not (maiuscula and minuscula and numero and especial):
        return False
    return True

def gerar_token(id_usuario, tipo):
    payload = {
        'id_usuario': int(id_usuario),
        'tipo': int(tipo),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

def descobre_tipo_usuario():
    token = request.cookies.get('access_token')
    if not token:
        return None # manda o arrumbado logar
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['tipo']
    except:
        return None # se der erro volta nada

def descobre_id_usuario():
    token = request.cookies.get('access_token')
    if not token:
        return None
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return int(payload['id_usuario'])
    except:
        return None

def gerar_codigo():
    return str(random.randint(100000, 999999))

def enviando_email(destinatario, codigo):
    user = 'gustavopontin02@gmail.com'
    senha = 'oqwm swse unid odxl'

    assunto = 'Código de recuperação de senha'
    mensagem = f'Seu código de verificação é: {codigo}'

    msg = MIMEText(mensagem)
    msg['From'] = user
    msg['To'] = destinatario
    msg['Subject'] = assunto

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user, senha)
    server.send_message(msg)
    server.quit()

def senha_repetida(id_usuario, nova_senha):
    cursor = con.cursor()

    cursor.execute("""
        SELECT FIRST 3 senha_anterior
        FROM historico_senha
        WHERE id_usuario = ?
        ORDER BY id_historico_senha DESC
    """, (id_usuario,))

    ultimas = cursor.fetchall()

    cursor.close()

    for senha in ultimas:
        if check_password_hash(senha[0], nova_senha):
            return True
    return False