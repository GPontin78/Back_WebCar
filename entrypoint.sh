#!/bin/sh
set -eu

echo "Iniciando Firebird..."

: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=3050}"
: "${DB_NAME:=/app/WEBCAR.FDB}"
: "${DB_USER:=sysdba}"
: "${DB_PASSWORD:=masterkey}"

export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD

if [ ! -f "$DB_NAME" ]; then
    echo "ERRO: banco Firebird nao encontrado em $DB_NAME"
    exit 1
fi

chown firebird:firebird "$DB_NAME" 2>/dev/null || true
chmod 664 "$DB_NAME" 2>/dev/null || true

service firebird3.0 start

CURRENT_SYSDBA_PASSWORD="$DB_PASSWORD"
if [ -f /etc/firebird/3.0/SYSDBA.password ]; then
    . /etc/firebird/3.0/SYSDBA.password
    CURRENT_SYSDBA_PASSWORD="${ISC_PASSWORD:-$DB_PASSWORD}"
fi

echo "Aguardando Firebird escutar em 127.0.0.1:${DB_PORT}..."
i=0
until python -c "import socket; s=socket.create_connection(('127.0.0.1', int('${DB_PORT}')), 2); s.close()" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "ERRO: Firebird nao abriu a porta ${DB_PORT}"
        exit 1
    fi
    sleep 1
done

if [ "$DB_USER" = "sysdba" ] && [ "$CURRENT_SYSDBA_PASSWORD" != "$DB_PASSWORD" ]; then
    echo "Ajustando senha do SYSDBA para a senha definida em DB_PASSWORD..."
    gsec -user sysdba -password "$CURRENT_SYSDBA_PASSWORD" -mo sysdba -pw "$DB_PASSWORD" \
        || echo "Aviso: nao foi possivel alterar a senha do SYSDBA; tentando conectar mesmo assim."
fi

echo "Testando conexao com $DB_NAME..."
printf 'select 1 from rdb$database;\n' | isql-fb -user "$DB_USER" -password "$DB_PASSWORD" "127.0.0.1/${DB_PORT}:$DB_NAME"

echo "Iniciando backend Flask..."

exec python server.py
