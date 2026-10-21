"""Composição dos emails do PIPE, separada das mensagens do Telegram."""

from flask import current_app, has_request_context, render_template, url_for


def _assunto(tipo, contexto):
    if tipo == 'codigo_2fa':
        return 'Código de acesso ao PIPE'
    if tipo == 'convite':
        return 'O teu convite para o PIPE'
    if tipo == 'recuperacao_password':
        return 'Pedido de recuperação da palavra-passe do PIPE'
    if tipo == 'teste':
        return 'Notificações do PIPE activadas'
    if tipo == 'resultados_euromilhoes':
        return f'Resultados do Euromilhões — {contexto.get("data", "hoje")}'
    if tipo == 'tarefas':
        hoje = contexto.get('total_hoje', 0)
        atraso = contexto.get('total_atraso', 0)
        if hoje and atraso:
            return f'{hoje} tarefa(s) para hoje e {atraso} em atraso — PIPE'
        if hoje:
            return f'{hoje} tarefa(s) com prazo hoje — PIPE'
        return f'{atraso} tarefa(s) em atraso — PIPE'
    if tipo == 'eventos':
        amanha = contexto.get('total_amanha', 0)
        hoje = contexto.get('total_hoje', 0)
        if amanha and hoje:
            return f'{amanha} evento(s) amanhã e {hoje} hoje — PIPE'
        return f'{amanha or hoje} evento(s) no Calendário — PIPE'
    if tipo == 'partilha_recurso':
        return 'Recebeste um recurso partilhado'
    raise ValueError(f'Template de email desconhecido: {tipo}')


def compor_email(tipo, contexto=None):
    """Devolve assunto, alternativa texto e HTML para um tipo conhecido."""
    contexto = dict(contexto or {})
    if has_request_context():
        url_app = url_for('dashboard', _external=True)
    else:
        url_base = current_app.config['PIPE_PUBLIC_URL']
        url_app = f'{url_base}/'
    contexto.setdefault('app_url', url_app)
    if has_request_context():
        contexto.setdefault('tarefas_url', url_for('tarefas.index', _external=True))
        contexto.setdefault('calendario_url', url_for('calendario.index', _external=True))
        contexto.setdefault('euromilhoes_url', url_for('euromilhoes.index', _external=True))
    else:
        contexto.setdefault('tarefas_url', f'{url_base}/tarefas/')
        contexto.setdefault('calendario_url', f'{url_base}/calendario/')
        contexto.setdefault('euromilhoes_url', f'{url_base}/euromilhoes/resultados')
    contexto['preheader'] = {
        'codigo_2fa': 'O teu código de verificação, válido durante 10 minutos.',
        'convite': 'Foste convidado a criar uma conta no PIPE.',
        'recuperacao_password': 'Segue o link para definires uma nova palavra-passe.',
        'teste': 'O endereço está pronto para receber notificações do PIPE.',
        'resultados_euromilhoes': 'Já podes consultar os resultados dos teus jogos.',
        'tarefas': 'Um resumo das tarefas com prazo hoje ou em atraso.',
        'eventos': 'Um resumo dos próximos eventos do Calendário.',
        'partilha_recurso': 'Um utilizador partilhou um recurso contigo no PIPE.',
    }[tipo]
    contexto['assunto'] = _assunto(tipo, contexto)
    return (
        contexto['assunto'],
        render_template('emails/email.txt', tipo=tipo, **contexto),
        render_template('emails/email.html', tipo=tipo, **contexto),
    )
