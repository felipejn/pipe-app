/* PIPE — JavaScript base */

// Fechar alertas ao clicar
document.querySelectorAll('.alerta').forEach(a => {
    a.style.cursor = 'pointer';
    a.addEventListener('click', () => a.remove());
});

// Auto-fechar alertas de sucesso após 4 segundos
document.querySelectorAll('.alerta-sucesso, .alerta-info').forEach(a => {
    setTimeout(() => a.remove(), 4000);
});
