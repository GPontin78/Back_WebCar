#!/bin/sh

echo "Iniciando Firebird..."

service firebird3.0 start

echo "Aguardando Firebird subir..."
sleep 10

echo "Iniciando backend Flask..."

python server.py