#!/bin/sh

echo "Iniciando Firebird 4..."

service firebird4.0 start || true

echo "Aguardando Firebird escutar em ${DB_HOST}:${DB_PORT}..."

for i in $(seq 1 30); do
  nc -z "$DB_HOST" "$DB_PORT" && break
  sleep 1
done

if ! nc -z "$DB_HOST" "$DB_PORT"; then
  echo "ERRO: Firebird nao abriu a porta ${DB_PORT}"
  exit 1
fi

echo "Firebird abriu a porta ${DB_PORT}"

echo "Ajustando senha do SYSDBA para a senha definida em DB_PASSWORD..."
gsec -user sysdba -password masterkey -modify sysdba -pw "$DB_PASSWORD" || true

echo "Testando conexao com ${DB_NAME}..."
isql-fb -user "$DB_USER" -password "$DB_PASSWORD" "$DB_HOST/$DB_PORT:$DB_NAME" -q <<EOF || true
SELECT 1 FROM RDB\$DATABASE;
EOF

echo "Iniciando backend Flask..."

python server.py