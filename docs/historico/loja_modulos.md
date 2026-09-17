Implementa seleção de módulos por utilizador no projecto Flask PIPE (pipe-app).

## Regras gerais
- Português Europeu em todos os comentários, mensagens e templates
- Padrão AJAX do PIPE: header X-CSRFToken, backend usa request.get_json()
- Sem quebrar nenhum blueprint existente

## 1. Criar app/modulos/config.py
Dicionário MODULOS_DISPONIVEIS com os seguintes módulos (slug → dict):
  euromilhoes  → nome='Euromilhões',  icone='🎱', url_endpoint='euromilhoes.index',  descricao='Regista combinações e acompanha resultados do Euromilhões.'
  tarefas      → nome='Tarefas',      icone='✅', url_endpoint='tarefas.index',       descricao='Listas de tarefas com prazos, prioridades e notificações.'
  notas        → nome='Notas',        icone='📝', url_endpoint='notas.index',         descricao='Notas rápidas, checklists e etiquetas.'
  passwords    → nome='Passwords',    icone='🔑', url_endpoint='passwords.index',     descricao='Gerador de passwords, passphrases e PINs seguros.'
  cambio       → nome='Câmbio',       icone='💱', url_endpoint='cambio.index',        descricao='Conversão de moedas com taxas em tempo real (Wise + fallback).'
  cores        → nome='Cores Flutter',icone='🎨', url_endpoint='cores.index',        descricao='Converte cores HEX/RGB/HSL para código Flutter.'
  conversoes   → nome='Conversões',   icone='🔄', url_endpoint='conversoes.index',   descricao='Converte ficheiros HEIC→JPG e PNG/JPG→ICO.'
  assistente   → nome='Assistente IA',icone='🤖', url_endpoint='assistente.index',   descricao='Assistente inteligente com acesso às tuas tarefas e notas.'

## 2. Criar app/modulos/models.py
Modelo UserModulo:
  - user_id: Integer, ForeignKey('user.id'), primary_key=True
  - modulo_slug: String(32), primary_key=True
  - ativo: Boolean, default=True
  
Função helper get_modulos_ativos(user_id) → lista de slugs activos para o user

## 3. Criar app/modulos/routes.py + app/modulos/__init__.py
Blueprint 'modulos', url_prefix='/modulos'

Rotas:
  GET  /modulos/loja          → render modulos/loja.html com MODULOS_DISPONIVEIS e slugs activos do user
  POST /modulos/api/toggle    → AJAX, recebe {slug, ativo}, cria ou actualiza UserModulo, devolve {ok, slug, ativo}

## 4. Registar blueprint em app/__init__.py
Adicionar após os outros blueprints:
  from app.modulos import modulos_bp
  app.register_blueprint(modulos_bp)

## 5. Criar app/templates/modulos/loja.html
Segue o design system do PIPE (tema escuro, âmbar/dourado, pipe.css).
Layout: página com título 'Loja de Módulos', subtítulo 'Activa os módulos que queres usar'.
Cards em grelha (estilo dashboard existente), cada card tem:
  - ícone grande
  - nome
  - descrição
  - toggle switch (checked se activo) — chama /modulos/api/toggle via fetch com X-CSRFToken
  - feedback visual imediato no toggle (sem reload)
JS inline no template (padrão do PIPE).

## 6. Modificar app/templates/dashboard.html
Substituir os cards estáticos actuais por cards dinâmicos gerados a partir dos módulos activos do user.

A view do dashboard (em app/core/routes.py ou onde estiver definida) deve ser modificada para injectar a lista de módulos activos com os seus metadados (nome, icone, url_endpoint) vindos de get_modulos_ativos() + MODULOS_DISPONIVEIS.

Estado vazio (zero módulos activos):
  - Ícone grande (ex: 🧩)
  - Mensagem: 'Ainda não tens módulos activos.'
  - Botão/link destacado: 'Ir para a Loja de Módulos' → /modulos/loja

## 7. Adicionar link 'Loja de Módulos' na navbar ou área de definições
Adicionar entrada acessível a todos os utilizadores autenticados (não só admins).
Sugestão: ícone 🧩 na navbar junto às definições, ou link em /definicoes.