# 🚗 WebCar — Scripts de População do Banco

## O que estes scripts fazem

| Script | Modo | Quando usar |
|---|---|---|
| `popular_webcar.py` | Via API HTTP | Quando a API Flask estiver rodando |
| `popular_webcar_fdb.py` | Direto no banco FDB | Quando quiser acessar o banco sem a API |

---

## O que é criado

### 👥 6 Usuários
| Nome | Email | Senha | Tipo |
|---|---|---|---|
| Carlos Eduardo Silva | carlos.silva@email.com | @Carlos123 | Vendedor |
| Ana Paula Ferreira | ana.ferreira@email.com | @AnaFer456 | Vendedor |
| Fernanda Lima | fernanda.lima@email.com | @Ferna987! | Vendedor |
| Roberto Mendes | roberto.mendes@email.com | @Rober789! | Cliente |
| Juliana Costa | juliana.costa@email.com | @Julia321! | Cliente |
| Marcos Oliveira | marcos.oliveira@email.com | @Marc654! | Cliente |

### 🚗 18 Veículos com fotos (das marcas já cadastradas)
Toyota, Honda, Volkswagen, Hyundai, Chevrolet, Fiat, Ford, Renault, Nissan, Jeep

### 🔧 55+ Serviços organizados por categoria
- Troca de óleo (mineral, semissintético, sintético, diesel)
- Pneus (aro 14 a 18, balanceamento, alinhamento, rodízio)
- Freios (pastilhas, discos, fluido, revisão)
- Suspensão (amortecedores, molas, buchas)
- Motor e transmissão (filtros, correia, velas, câmbio)
- Elétrica (bateria, alternador, scanner OBD)
- Arrefecimento (fluido, radiador, bomba d'água)
- Ar-condicionado (recarga, higienização, filtro)
- Revisão geral (10k, 20k, 30k, 60k km)
- Estética (polimento, higienização, película)

---

## Como usar

### Opção 1 — Via API (recomendado)

```bash
# 1. Com a API Flask rodando em localhost:5000
python popular_webcar.py
```

### Opção 2 — Direto no banco Firebird

```bash
# 1. Instale as dependências
pip install fdb flask-bcrypt requests

# 2. Ajuste o caminho do banco no início do arquivo se necessário
# DB_NAME = r"C:\Users\Aluno\Desktop\Back_WebCar-main\WEBCAR.FDB"

# 3. Execute
python popular_webcar_fdb.py
```

---

## Observações
- Os scripts são idempotentes: se rodar duas vezes, pula o que já existe
- Fotos são baixadas do Wikimedia Commons (licença livre) e randomuser.me
- Se a internet estiver indisponível, o script de API gera fotos coloridas como placeholder
- Para adicionar mais veículos, basta adicionar entradas nos dicionários `VEICULOS_POR_MARCA` / `VEICULOS`
