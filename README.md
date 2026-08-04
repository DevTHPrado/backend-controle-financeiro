# Backend - Controle Financeiro

API RESTful assíncrona desenvolvida com **FastAPI**, **SQLAlchemy (Async)** e **PostgreSQL** para a plataforma de controle financeiro pessoal.

## 🚀 Tecnologias Utilizadas

- **Linguagem:** Python 3.11+
- **Framework Web:** FastAPI
- **ORM & Banco de Dados:** SQLAlchemy 2.0 (Async) + PostgreSQL (`asyncpg`)
- **Validação de Dados:** Pydantic v2
- **Autenticação e Segurança:** JWT (PyJWT) + Passlib (Argon2)
- **Processamento de Planilhas:** Pandas (leitura/análise) + OpenPyXL (escrita/formatação)
- **Testes:** Pytest + Asyncio

---

## 🏗️ Estrutura do Projeto

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Injeção de dependências (auth, DB session)
│   │   └── v1/                  # Rotas da API v1
│   │       ├── auth.py          # Registro e Login
│   │       ├── users.py         # Dados do usuário
│   │       ├── categories.py    # CRUD de Categorias
│   │       ├── transactions.py  # CRUD de Lançamentos
│   │       ├── excel.py         # Importação e Exportação Excel
│   │       ├── dashboard.py     # Métricas e Gráficos
│   │       └── recommendations.py # Motor de Recomendações
│   ├── core/                    # Configurações, Segurança e DB connection
│   ├── models/                  # Entidades SQLAlchemy (User, Category, Transaction, etc.)
│   ├── schemas/                 # Schemas Pydantic para requisições e respostas
│   ├── services/                # Regras de negócio e lógica da aplicação
│   └── tests/                   # Suíte de testes unitários e de integração
├── .env.example                 # Exemplo de variáveis de ambiente
├── requirements.txt             # Dependências do Python
└── README.md
```

---

## ⚙️ Configuração e Execução

### 1. Pré-requisitos
- Python 3.11 ou superior
- Banco de dados PostgreSQL rodando

### 2. Instalação

Crie e ative um ambiente virtual:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:
```bash
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e ajuste as credenciais do seu banco PostgreSQL:

```bash
cp .env.example .env
```

Exemplo de `.env`:
```env
APP_NAME="Controle Financeiro API"
DEBUG=true
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/controle_financeiro"
SECRET_KEY="sua_chave_secreta_jwt_gerada"
CORS_ORIGINS=["http://localhost:5173"]
```

### 4. Rodando o Servidor

Inicie o servidor de desenvolvimento via Uvicorn:

```bash
uvicorn app.main:app --reload --port 8001
```
ou
```bash
python -m uvicorn app.main:app --reload --port 8001
```

---

## 📖 Documentação da API (Swagger / ReDoc)

Com o servidor rodando, acesse:

- **Swagger UI:** [http://localhost:8001/docs](http://localhost:8001/docs)
- **ReDoc:** [http://localhost:8001/redoc](http://localhost:8001/redoc)
- **Health Check:** [http://localhost:8001/health](http://localhost:8001/health)

---

## 🧪 Rodando os Testes

Para rodar a suíte de testes com `pytest`:

```bash
pytest
```
