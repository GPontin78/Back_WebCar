from flask import Flask
import fdb
import os
from flask_cors import CORS


app = Flask(__name__)
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

try:
    con = fdb.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    print("DEU BOM")

except Exception as e:
    print(f"DEU RUIM : {e}")


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