import jwt
import datetime
from main import app
from flask import request

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