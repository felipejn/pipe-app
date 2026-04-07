# PIPE — Sistema de Convites para Registo

## Visão Geral

**Problema:** O PIPE (Plataforma Inteligente Pessoal e Expansível) tem o registo aberto — qualquer pessoa pode criar conta em `/registo`. Queremos restringir o acesso à plataforma a **utilizadores convidados**, com registo exclusivamente via convite.

**Solução:** O administrador gera convites na área de administração. Cada convite é um link único que pode ser enviado por email (via SendGrid) ou copiado manualmente. O destinatário abre o link, cria a sua conta, e o convite é consumido e invalidado.

## Decisões de Design

| Critério | Decisão | Justificação |
|---|---|---|
| Validade do convite | 7 dias | Tempo suficiente para agir, mas curto para não acumular convites abertos |
| Uso do convite | Único (1 registo = 1 convite) | Evita partilha pública de links |
| Quem gera convites | Apenas utilizadores admin | Controlo centralizado por segurança |
| Registo directo | Bloqueado | `/registo` redirect para `/login` com flash informativa |
| Envio de convite | Email (SendGrid) ou link copiado | Flexibilidade para o admin |
| Registo por convite | Formulário pré-preenchido | Email do destinatário aparece read-only |

## Arquitectura do Projecto (Contexto)

O PIPE é uma aplicação Flask com a estrutura:

```
pipe-app/
├── app/
│   ├── __init__.py          # create_app, db, factory
│   ├── extensions.py        # Flask-Limiter
│   ├── auth/                # Blueprint de autenticação
│   │   ├── __init__.py
│   │   ├── models.py        # User (login, 2FA, TOTP, etc.)
│   │   ├── forms.py         # LoginForm, RegistoForm, etc.
│   │   └── routes.py        # /login, /registo, /2fa, /perfil, /logout
│   ├── admin/               # Blueprint de administração
│   │   ├── __init__.py
│   │   ├── decorators.py    # @admin_required
│   │   └── routes.py        # /admin/
│   ├── notifications/
│   │   └── channels/
│   │       └── email.py     # EmailChannel (SendGrid) — JÁ EXISTE
│   └── templates/
│       ├── auth/            # Templates de auth
│       └── admin/           # Templates de admin
├── scripts/
│   └── criar_admin.py       # Cria admin via CLI (sem registo web)
└── estado_atual.md          # Documentação de referência
```

## O que vai ser implementado

### 1. Novo modelo `Convite` (`app/auth/models.py`)

```python
class Convite(db.Model):
    __tablename__ = 'convites'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('utilizadores.id'))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    expira_em = db.Column(db.DateTime)  # criado_em + 7 dias
    usado = db.Column(db.Boolean, default=False)
    usado_em = db.Column(db.DateTime, nullable=True)
```

### 2. Rota de registo bloqueada (`app/auth/routes.py`)

- `GET /registo` → redirect `/login` com flash `"O registo requer um convite."`
- `GET /registo/<token>` → valida o token, mostra formulário `registo_token.html` com email pré-preenchido
- `POST /registo/<token>` → cria conta + marca convite como usado

### 3. Rotas de convites no admin (`app/admin/routes.py`)

- `GET /admin/convites` → lista todos os convites com estado (activo/usado/expirado)
- `POST /admin/convites/gerar` → gera convite com email; se checkbox `enviar_email`, envia por SendGrid; senão retorna link para copiar
- `POST /admin/convites/<id>/revogar` → invalida convite não usado

### 4. Templates novos

- `app/templates/admin/convites.html` — formulário de geração + tabela de convites
- `app/templates/auth/registo_token.html` — formulário de registo com token, email pré-preenchido (read-only)
- `app/templates/admin/dashboard.html` — adicionar link para "Gestão de Convites"

## Ferramentas/Canais Reutilizados

| Componente | Ficheiro | Uso no sistema de convites |
|---|---|---|
| EmailChannel | `app/notifications/channels/email.py` | Enviar convite por email via SendGrid |
| Config SendGrid | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` | Auth e remetente dos emails |
| `@admin_required` | `app/admin/decorators.py` | Protecção de rotas de convite |
| Padrão AJAX | `'X-CSRFToken': '{{ csrf_token() }}'` | Gerar/revogar convites sem reload |
| `secrets` module | (stdlib Python) | Gerar token URL-safe para convite |

## Fluxo de Uso

1. Admin faz login → acede ao dashboard admin → "Gestão de Convites"
2. Preenche email do destinatário + clica "Gerar convite"
3. **Opção A:** Marca "Enviar por email" → email é enviado com link directo
4. **Opção B:** Não marca → sistema mostra link para o admin copiar e partilhar manualmente
5. Destinatário abre o link → vê formulário de registo com email pré-preenchido
6. Preenche username + password → conta criada → convite marcado como usado
7. Se tentar reutilizar o link → "Convite já utilizado"
8. Se o convite expirou (7 dias) → "Convite expirado"

## Notas Técnicas

- O modelo `Convite` é criado automáticamente pelo `db.create_all()` na factory `create_app()`
- Token gerado com `secrets.token_urlsafe(32)` (mesmo padrão do reset de password existente)
- `scripts/criar_admin.py` continua a funcionar independentemente — cria admin directo na BD, sem convite
- Templates seguem padrão do PIPE: **vanilla JS inline**, sem ficheiros JS externos
- Todo o texto em **Português Europeu** (PT-PT)

## Segurança

- Convites são exclusivos de admin — rotas protegidas com `@login_required` + `@admin_required`
- Token de convite é criptograficamente seguro (256 bits de entropia via `secrets`)
- Convite usado não pode ser reutilizado
- Convite expirado é rejeitado
- Rota de registo directa é bloqueada — sem enumeração de utilizadores
