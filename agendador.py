import os
from flask import render_template
from apscheduler.schedulers.background import BackgroundScheduler
from funcao import enviando_email
from main import app, con

# =========================================================
# FUNÇÃO PARA RODAR COM CONTEXTO DO FLASK
# =========================================================
def executar_com_contexto(funcao):

    with app.app_context():

        funcao()

def enviar_email_antes_vencimento():

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT T.DATA_VENCIMENTO,T.NUMERO_PARCELA,T.VALOR_PARCELA,F.ID_VENDA,V.ID_VENDA,U.ID_USUARIO, U.EMAIL
            FROM ITEM_FINANCIAMENTO T
            INNER JOIN FINANCIAMENTO F ON T.ID_FINANCIAMENTO = F.ID_FINANCIAMENTO
            INNER JOIN VENDA V ON F.ID_VENDA = V.ID_VENDA 
            INNER JOIN USUARIO U ON V.ID_USUARIO_CLIENTE = U.ID_USUARIO
            WHERE T.DATA_VENCIMENTO = CURRENT_DATE + 2
        """)

        parcelas = cursor.fetchall()

        for parcela in parcelas:

            data_vencimento = parcela[0]
            numero_parcela = parcela[1]
            valor_parcela = parcela[2]
            email = parcela[6]

            html = render_template(
                'email_antes_vencimento.html',
                numero_parcela=numero_parcela,
                valor_parcela=valor_parcela,
                data_vencimento=data_vencimento
            )

            enviando_email(email, html)

        print('email enviado')

    except Exception as e:
        print( 'erro ao enviar email')


def enviar_email_atrasado():

    try:

        cursor = con.cursor()

        cursor.execute("""
            SELECT T.DATA_VENCIMENTO,]T.NUMERO_PARCELA,]T.VALOR_PARCELA,]F.ID_VENDA,V.ID_VENDA, U.ID_USUARIO, U.EMAIL
            FROM ITEM_FINANCIAMENTO T
            INNER JOIN FINANCIAMENTO F ON T.ID_FINANCIAMENTO = F.ID_FINANCIAMENTO
            INNER JOIN VENDA V ON F.ID_VENDA = V.ID_VENDA
            INNER JOIN USUARIO U ON V.ID_USUARIO_CLIENTE = U.ID_USUARIO
            WHERE T.DATA_VENCIMENTO = CURRENT_DATE - 2
        """)

        parcelas = cursor.fetchall()

        for parcela in parcelas:

            data_vencimento = parcela[0]
            numero_parcela = parcela[1]
            valor_parcela = parcela[2]
            email = parcela[6]

            html = render_template(
                'email_atrasado.html',
                numero_parcela=numero_parcela,
                valor_parcela=valor_parcela,
                data_vencimento=data_vencimento
            )

            enviando_email(email, html)

        print('email enviado')

    except Exception as e:
        print('erro ao enviar email')


# =========================================================
# AGENDADOR AUTOMÁTICO
# =========================================================
scheduler = BackgroundScheduler()

scheduler.add_job(
    lambda: executar_com_contexto(enviar_email_antes_vencimento),# serve para chamar outra função apenas quando o scheduler executar.
    'cron', #cron' é o tipo de agendamento.
    hour=12,
    minute=20,
    id='email_antes_vencimento',
    replace_existing=True
    # se já existir um job com esse mesmo id,
    # substitui o antigo pelo novo.
)

scheduler.add_job(
    lambda: executar_com_contexto(enviar_email_atrasado),
    'cron',
    hour=12,
    minute=25,
    id='email_atrasado',
    replace_existing=True
)

if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()