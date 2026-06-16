# Back WebCar

Backend Flask do projeto WebCar usando banco Firebird local (`WEBCAR.FDB`).

## Rodar no VS Code

1. Abra esta pasta no VS Code.
2. Selecione o interpretador Python em `.venv/Scripts/python.exe`.
3. Aperte `F5` e escolha a configuracao `WebCar Backend`.

## Rodar pelo terminal

```powershell
.\.venv\Scripts\python.exe server.py
```

A API sobe em:

```text
http://localhost:5000
```

## Reinstalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configuracao do banco

Por padrao, o backend usa o arquivo `WEBCAR.FDB` que fica na raiz do projeto.
Se precisar usar outro banco, defina a variavel de ambiente `DB_NAME`.
