# PIPE — Plataforma Inteligente Pessoal e Expansível

Aplicação web pessoal construída com Flask. O nome é simultaneamente um acrónimo e o meu apelido (Felipe = Pipe).

Este projecto serve três propósitos: ferramenta pessoal útil, base para aprendizagem prática de Python/Flask, e portfólio para transição para a área de software.

> A aplicação está deployed em [felipejn.pythonanywhere.com](https://felipejn.pythonanywhere.com) — plano free, custo zero.

---

## Módulos

### 🎯 Euromilhões
Registo e acompanhamento de jogos do Euromilhões.
- Regista jogos com selector de data (próximo sorteio ou data manual)
- Verifica resultados automaticamente após cada sorteio via [API pública](https://euromillions.api.pedromealha.dev)
- Análise de frequência histórica de números e estrelas
- Notificação de resultados por Telegram e/ou email

### ✅ Tarefas
Gestor de tarefas pessoal com suporte a múltiplas listas.
- Listas personalizáveis com ícone emoji
- Prioridade (alta / média / baixa), data limite e etiquetas
- Busca em tempo real por título e etiquetas
- Notificação diária de tarefas com prazo ultrapassado

### 📝 Notas
Bloco de notas com suporte a texto livre e checklists.
- Grelha de cartões com criação inline sem mudar de página
- Suporte a texto livre e checklist com toggle directo no cartão
- 8 cores de fundo dentro do tema escuro
- Fixar no topo, arquivar e etiquetas com sugestão automática
- Busca em tempo real por título, corpo e etiquetas

### 🔑 Passwords
Gerador de palavras-passe criptograficamente seguro. Sem base de dados — módulo completamente stateless.
- **Password** — comprimento 8–64, toggles: maiúsculas, minúsculas, números, símbolos, excluir ambíguos
- **Passphrase** — 3–10 palavras portuguesas separadas por hífen
- **PIN** — 4–12 dígitos numéricos
- Barra de força com 5 níveis calculados por entropia no backend

### 🔄 Conversões
Conversão de ficheiros e imagens. Zero disco — tudo processado em memória.
- **HEIC → JPG** — converter fotos do iPhone com drag & drop
- **PNG/JPG → ICO** — gerar ícones com tamanho selecionável (16–256px)
- Validações: extensão suportada, limite 10MB/ficheiro, máximo 20 ficheiros
- 1 ficheiro → download directo; 2+ ficheiros → download ZIP
- Histórico das últimas 10 conversões com metadados

### 💱 Câmbio
Conversão de moedas com cotações em tempo real. Sem base de dados — módulo stateless.
- Default EUR → BRL, com selects para qualquer par de moedas
- 8 moedas: EUR, BRL, USD, GBP, JPY, CHF, CAD, AUD
- Cotações via Wise API v3 (com fallback para ExchangeRate-API)
- Resultado com taxa de câmbio (inclui taxas reais quando disponível via Wise) e botão copiar
- Na whitelist do PythonAnywhere, compatível com plano free

### 🎨 Cores Flutter
Conversor de cores para código Flutter. Sem base de dados — módulo stateless.
- Color picker visual + input manual em HEX, RGB, HSL ou CMYK
- Gera todos os equivalentes Flutter: `Color(0x..)`, `fromRGB`, `fromARGB`, `HSLColor`, `HSVColor`, Material swatch mais próximo
- Modo bidirecional: cola código Flutter → vê a cor e o HEX
- Botão copiar em cada linha de código

---

## Stack técnica

| Área | Tecnologia |
|---|---|
| Framework | Flask 3.0 (Python) |
| Base de dados | SQLite + Flask-SQLAlchemy |
| Autenticação | Flask-Login + Werkzeug |
| Formulários | Flask-WTF + WTForms |
| Notificações | Telegram Bot API + SendGrid |
| 2FA | TOTP (pyotp) + Telegram + Email |
| Imagens | Pillow + pillow-heif |
| Hosting | PythonAnywhere (plano free) |
| Frontend | HTML/CSS/JS vanilla — sem frameworks |

---

## Funcionalidades transversais

- **Autenticação** — registo, login, recuperação de password por email
- **2FA opcional** — Telegram, Email ou TOTP (Google Authenticator / Authy) — múltiplos métodos em simultâneo
- **Notificações** — arquitectura modular com canais independentes (Telegram + SendGrid)
- **Área admin** — gestão de utilizadores, activar/desactivar contas
- **Scheduled task** — script unificado `pipe_tasks.py` a correr diariamente às 08:00

---

## Preview

<!-- Adicionar screenshot aqui -->
> *Screenshot em breve.*

---

## Instalação local

### Pré-requisitos
- Python 3.10+
- pip

### Passos

```bash
# Clonar o repositório
git clone https://github.com/felipejn/pipe-app.git
cd pipe-app

# Criar e activar ambiente virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env e preencher SECRET_KEY (obrigatório)
# As restantes variáveis são opcionais para uso local

# Criar a base de dados e o primeiro utilizador admin
python scripts/criar_admin.py

# Arrancar a aplicação
python run.py
```

A aplicação fica disponível em `http://127.0.0.1:5000`.

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SECRET_KEY` | ✅ | Chave secreta Flask — gerar com `secrets.token_hex(32)` |
| `TELEGRAM_BOT_TOKEN` | ❌ | Token do bot Telegram para notificações e 2FA |
| `SENDGRID_API_KEY` | ❌ | API key SendGrid para notificações por email |
| `SENDGRID_FROM_EMAIL` | ❌ | Endereço de remetente verificado no SendGrid |

---

## Estrutura do projecto

```
pipe-app/
├── app/
│   ├── auth/           # Autenticação, 2FA, recuperação de password
│   ├── euromilhoes/    # Módulo Euromilhões
│   ├── tarefas/        # Módulo Tarefas
│   ├── notas/          # Módulo Notas
│   ├── passwords/      # Módulo Passwords (stateless)
│   ├── conversoes/     # Módulo Conversões HEIC → JPG
│   ├── cambio/         # Módulo Câmbio (stateless)
│   ├── cores/          # Módulo Cores Flutter (stateless)
│   ├── notifications/  # Serviço central de notificações
│   ├── admin/          # Área de administração
│   ├── settings/       # Definições do utilizador
│   ├── static/         # CSS e JS
│   └── templates/      # Templates Jinja2
├── scripts/            # Scripts de manutenção e scheduled tasks
├── .env.example
├── requirements.txt
└── run.py
```

Cada módulo é um Flask Blueprint independente. Para adicionar um novo módulo basta criar a pasta, registar o blueprint e adicionar o card no dashboard.

---

## Contexto

Projecto iniciado como exercício prático de Flask/Python, com o objectivo de construir algo genuinamente útil enquanto aprendo. A arquitectura foi pensada para crescer — novos módulos podem ser adicionados sem alterar o que já existe.