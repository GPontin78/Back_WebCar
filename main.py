from flask import Flask
import fdb
import os


app = Flask(__name__)
app.config.from_pyfile('config.py')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

host = app.config['DB_HOST']
database = app.config['DB_NAME']
user = app.config['DB_USER']
password = app.config['DB_PASSWORD']



try:
    con = fdb.connect(host=host, database=database, user=user, password=password)
    print("DEU BOM")

except Exception as e:
        print(f"DEU RUIM : {e}")



from usuario import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)