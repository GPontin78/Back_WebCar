#!/bin/sh

echo "Iniciando Firebird..."

service firebird3.0 start || true

sleep 3

echo "Iniciando backend Flask..."

python server.py