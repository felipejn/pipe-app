// content.js — Content Script do PIPE Cofre
// Injectado em todas as páginas via manifest V3 content_scripts
// Responsável pela captura activa de forms de login

(function () {
  'use strict';

  // ─── Ignorar se PAGE é PIPE (evitar loop) ───
  if (window.location.hostname.includes('pythonanywhere.com') &&
      window.location.pathname.includes('/passwords/')) {
    return;
  }

  // ─── Verificar se o form é de registo ───
  function isRegistrationForm(form) {
    const buttons = form.querySelectorAll('button, input[type="submit"]');
    for (const btn of buttons) {
      const text = (btn.value || btn.textContent || '').toLowerCase();
      if (text.includes('registar') || text.includes('criar conta') ||
          text.includes('sign up') || text.includes('inscrever') ||
          text.includes('registar-me') || text.includes('cadastrar')) {
        return true;
      }
    }
    // Verificar se há campos de registo (nome, email, etc.)
    const hasName = form.querySelector('input[name="nome"], input[name="name"], input[name="first_name"]');
    const hasEmail = form.querySelector('input[type="email"], input[name="email"]');
    if (hasName && hasEmail) return true;
    return false;
  }

  // ─── Verificar se o form parece de login ───
  function isLoginForm(form) {
    const hasPassword = form.querySelector('input[type="password"]');
    if (!hasPassword) return false;

    const textInputs = form.querySelectorAll('input[type="text"], input[type="email"]');
    for (const input of textInputs) {
      const name = (input.name || '').toLowerCase();
      const placeholder = (input.placeholder || '').toLowerCase();
      if (name.includes('user') || name.includes('login') || name.includes('email') ||
          name.includes('mail') || placeholder.includes('user') ||
          placeholder.includes('login') || placeholder.includes('email')) {
        return true;
      }
    }
    // Qualquer form com password + texto é provavelmente login
    return textInputs.length >= 1;
  }

  // ─── Listener de submit (delegation) ───
  document.addEventListener('submit', (e) => {
    const form = e.target.closest('form');
    if (!form) return;

    // Ignorar forms de registo
    if (isRegistrationForm(form)) return;

    // Só capturar em forms de login
    if (!isLoginForm(form)) return;

    // Perguntar ao utilizador
    const passwordInput = form.querySelector('input[type="password"]');
    const usernameInput = form.querySelector('input[type="text"], input[type="email"]');

    const username = usernameInput?.value || '';

    // Enviar ao background com a URL completa
    chrome.runtime.sendMessage({
      type: 'FORM_CAPTURE',
      data: {
        url: window.location.href,
        username: username,
        password: passwordInput?.value || '',
        domain: '', // O backend chama extrair_dominio() — não calcular aqui
      }
    });
  }, true); // capture phase
})();
