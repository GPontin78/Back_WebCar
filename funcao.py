import jwt
import datetime
from main import app, con
from flask import request
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_bcrypt import check_password_hash
import qrcode
import os

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
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=120)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# def descobre_tipo_usuario():
#     token = request.cookies.get('access_token')
#     if not token:
#         return None # manda o arrumbado logar
#     try:
#         payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
#         return payload['tipo']
#     except:
#         return None # se der erro volta nada



def pegar_token_requisicao():
    token = request.cookies.get('access_token')

    if token:
        return token

    authorization = request.headers.get('Authorization')

    if authorization:
        partes = authorization.split()

        if len(partes) == 2 and partes[0].lower() == 'bearer':
            return partes[1]

    return None


def decodificar_token_requisicao():
    token = pegar_token_requisicao()

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )

        return payload

    except Exception as e:
        print("ERRO TOKEN:", e)
        return None


def descobre_tipo_usuario():
    payload = decodificar_token_requisicao()

    if not payload:
        return None

    try:
        return int(payload['tipo'])
    except:
        return None


def descobre_id_usuario():
    payload = decodificar_token_requisicao()

    if not payload:
        return None

    try:
        return int(payload['id_usuario'])
    except:
        return None

def gerar_codigo():
    return str(random.randint(100000, 999999))


def enviando_email(destinatario, assunto, html):
    user_email = 'webcar89@gmail.com'
    senha = 'dbgu pqdq htkb bcds'

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = assunto
        msg['From'] = user_email
        msg['To'] = destinatario

        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(user_email, senha)
        server.send_message(msg)
        server.quit()

        print("EMAIL ENVIADO")

    except Exception as e:
        print("ERRO:", e)

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









# =========================================================
# FORMATA OS CAMPOS NO PADRÃO PIX
# =========================================================
def format_field(id, value):

    # pega tamanho do valor
    size = f"{len(value):02d}"

    # retorna:
    # ID + TAMANHO + VALOR
    return f"{id}{size}{value}"


# =========================================================
# GERA ASSINATURA CRC16
# =========================================================
def crc16(payload):

    # polinômio padrão
    polinomio = 0x1021

    # valor inicial
    resultado = 0xFFFF

    # percorre payload
    for c in payload:

        resultado ^= (ord(c) << 8)

        # percorre bits
        for _ in range(8):

            # verifica bit mais significativo
            if resultado & 0x8000:

                resultado = (resultado << 1) ^ polinomio

            else:

                resultado <<= 1

            # limita em 16 bits
            resultado &= 0xFFFF

    # retorna hexadecimal
    return f"{resultado:04X}"


# =========================================================
# GERA PAYLOAD PIX
# =========================================================
def gerar_payload_pix(
    chave,
    nome,
    cidade,
    valor,
    txid="***"
):

    # inicia payload
    payload = ""

    # versão do PIX
    payload += format_field("00", "01")

    # =====================================================
    # DADOS DA CONTA PIX
    # =====================================================
    merchant_account = ""

    # identificador PIX BACEN
    merchant_account += format_field(
        "00",
        "br.gov.bcb.pix"
    )

    # chave PIX
    merchant_account += format_field(
        "01",
        chave
    )

    # adiciona conta no payload
    payload += format_field(
        "26",
        merchant_account
    )

    # categoria da conta
    payload += format_field("52", "0000")

    # moeda BRL
    payload += format_field("53", "986")

    # valor do PIX
    payload += format_field(
        "54",
        f"{valor:.2f}"
    )

    # país
    payload += format_field("58", "BR")

    # nome da empresa
    payload += format_field(
        "59",
        nome[:25]
    )

    # cidade
    payload += format_field(
        "60",
        cidade[:15]
    )

    # =====================================================
    # TXID
    # =====================================================
    additional = format_field(
        "05",
        txid
    )

    payload += format_field(
        "62",
        additional
    )

    # prepara CRC16
    payload += "6304"

    # gera CRC16
    crc = crc16(payload)

    # adiciona CRC16
    payload += crc

    # retorna payload
    return payload


# =========================================================
# GERA IMAGEM QR CODE
# =========================================================
def gerar_qrcode(payload, nome_arquivo, pasta):

    # cria pasta automaticamente
    os.makedirs(
        f"uploads/pagamento/{pasta}",
        exist_ok=True
    )

    # gera QR Code
    qr = qrcode.make(payload)

    # caminho da imagem
    caminho = os.path.join(
        "uploads",
        "pagamento",
        pasta,
        f"{nome_arquivo}.png"
    )

    # salva imagem
    qr.save(caminho)

    # retorna caminho
    return caminho


# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================
def gerar_pix(
    chave,
    nome,
    cidade,
    valor,
    pasta,
    txid="***"
):

    # gera payload PIX
    payload = gerar_payload_pix(
        chave=chave,
        nome=nome,
        cidade=cidade,
        valor=valor,
        txid=txid
    )

    # gera imagem QR Code
    caminho_imagem = gerar_qrcode(
        payload,
        f"{txid}",
        pasta
    )

    # retorna caminho da imagem
    return {
        "imagem": caminho_imagem
    }