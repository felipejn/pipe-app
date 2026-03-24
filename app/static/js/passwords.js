(function () {
  'use strict';

  const elValor     = document.getElementById('pw-valor');
  const elCopiar    = document.getElementById('pw-copiar');
  const elGerar     = document.getElementById('pw-gerar');
  const elForcaFill = document.getElementById('pw-forca-fill');
  const elForcaLbl  = document.getElementById('pw-forca-label');

  let modoActual = 'password';

  document.querySelectorAll('.pw-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.pw-tab').forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      modoActual = tab.dataset.modo;
      document.querySelectorAll('.pw-painel').forEach(p => p.classList.add('hidden'));
      document.getElementById('painel-' + modoActual).classList.remove('hidden');
      gerar();
    });
  });

  function bindSlider(sliderId, labelId) {
    const sl = document.getElementById(sliderId);
    const lb = document.getElementById(labelId);
    sl.addEventListener('input', () => { lb.textContent = sl.value; gerar(); });
  }
  bindSlider('sl-comprimento', 'val-comprimento');
  bindSlider('sl-palavras',    'val-palavras');
  bindSlider('sl-pin',         'val-pin');

  ['tog-maiusculas','tog-minusculas','tog-numeros','tog-simbolos','tog-ambiguos']
    .forEach(id => document.getElementById(id).addEventListener('change', gerar));

  elCopiar.addEventListener('click', () => {
    const txt = elValor.textContent.trim();
    if (!txt || txt === '—') return;
    navigator.clipboard.writeText(txt).then(() => {
      elCopiar.classList.add('copiado');
      setTimeout(() => elCopiar.classList.remove('copiado'), 1500);
    });
  });

  elGerar.addEventListener('click', gerar);

  function gerar() {
    elGerar.disabled = true;
    elValor.textContent = '…';

    let payload = { modo: modoActual };

    if (modoActual === 'password') {
      payload.comprimento      = parseInt(document.getElementById('sl-comprimento').value);
      payload.maiusculas       = document.getElementById('tog-maiusculas').checked;
      payload.minusculas       = document.getElementById('tog-minusculas').checked;
      payload.numeros          = document.getElementById('tog-numeros').checked;
      payload.simbolos         = document.getElementById('tog-simbolos').checked;
      payload.excluir_ambiguos = document.getElementById('tog-ambiguos').checked;
    } else if (modoActual === 'passphrase') {
      payload.num_palavras = parseInt(document.getElementById('sl-palavras').value);
    } else {
      payload.comprimento = parseInt(document.getElementById('sl-pin').value);
    }

    fetch('/passwords/api/gerar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    .then(r => r.json())
    .then(data => {
      elValor.textContent = data.valor;
      actualizarForca(data.forca_score, data.forca_label);
    })
    .catch(() => { elValor.textContent = 'Erro'; })
    .finally(() => { elGerar.disabled = false; });
  }

  function actualizarForca(score, label) {
    const niveis = ['','forca-1','forca-2','forca-3','forca-4','forca-5'];
    elForcaFill.className = 'pw-forca-fill ' + (niveis[score] || '');
    elForcaFill.style.width = (score * 20) + '%';
    elForcaLbl.textContent = label;
  }

  gerar();
})();
