/* PIPE — JavaScript base */

/* Alternância de tema claro/escuro — persistido em localStorage */
(function() {
    var btn = document.getElementById('btn-alternar-tema');
    if (!btn) return;

    var icone = document.getElementById('icone-tema');

    function atualizarIcone() {
        var temaAtual = document.documentElement.getAttribute('data-theme');
        icone.textContent = temaAtual === 'light' ? '☀️' : '🌙';
    }

    atualizarIcone();

    btn.addEventListener('click', function() {
        var temaAtual = document.documentElement.getAttribute('data-theme');
        var novoTema = temaAtual === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', novoTema);
        localStorage.setItem('pipe-tema', novoTema);
        atualizarIcone();
    });
})();

// Fechar alertas ao clicar
document.querySelectorAll('.alerta').forEach(a => {
    a.style.cursor = 'pointer';
    a.addEventListener('click', () => a.remove());
});

// Auto-fechar alertas de sucesso após 4 segundos
document.querySelectorAll('.alerta-sucesso, .alerta-info').forEach(a => {
    setTimeout(() => a.remove(), 4000);
});
