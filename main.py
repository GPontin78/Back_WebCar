from flask import Flask
import fdb
import os
import sys
from flask_cors import CORS


app = Flask(__name__)
sys.modules.setdefault('main', sys.modules[__name__])
app.config.from_pyfile('config.py')

# Para funcionar com front publicado em HTTPS usando cookies/sessão
app.config['SESSION_COOKIE_SAMESITE'] = "None"
app.config['SESSION_COOKIE_SECURE'] = True

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "https://webcar-iota.vercel.app",
    "https://webcar-br.vercel.app"
])

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

host = app.config['DB_HOST']
database = app.config['DB_NAME']
user = app.config['DB_USER']
password = app.config['DB_PASSWORD']
con = None

try:
    # Se tiver host, conecta como servidor Firebird
    if host:
        con = fdb.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
    # Se não tiver host, tenta conectar direto no arquivo .FDB
    else:
        con = fdb.connect(
            database=database,
            user=user,
            password=password
        )

    print("DEU BOM")

except Exception as e:
    raise RuntimeError(f"Erro ao conectar no banco Firebird '{database}': {e}") from e


from usuario import *
from veiculo import *
from manutencao import *
from marca import *
from empresa import *
from pagamento import *
from graficos import *
from amortizar import *


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)