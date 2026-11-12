// Testa a função real de segmentação definida no template do Calendário.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const template = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'templates', 'calendario', 'index.html'),
  'utf8'
);
const regraPill = template.match(/\.cal-pilula\s*\{([^}]*)\}/);
if (!regraPill || !/min-height:\s*1\.2rem;/.test(regraPill[1])) {
  throw new Error('As pílulas do calendário precisam de altura mínima para segmentos vazios');
}
const inicio = template.indexOf('function segmentoEventoNoDia(');
if (inicio < 0) throw new Error('Função segmentoEventoNoDia não encontrada');

let profundidade = 0;
let fim = -1;
let abriu = false;
for (let i = template.indexOf('{', inicio); i < template.length; i++) {
  if (template[i] === '{') { profundidade++; abriu = true; }
  if (template[i] === '}') profundidade--;
  if (abriu && profundidade === 0) { fim = i + 1; break; }
}
if (fim < 0) throw new Error('Não foi possível extrair segmentoEventoNoDia');

const contexto = {};
vm.createContext(contexto);
vm.runInContext(template.slice(inicio, fim), contexto);

const evento = {
  data_inicio: '2026-12-25T09:00:00',
  data_fim: '2026-12-31T18:00:00',
  titulo: 'Férias',
};
const verificar = (data, esperado) => {
  const atual = contexto.segmentoEventoNoDia(evento, data);
  if (JSON.stringify(atual) !== JSON.stringify(esperado)) {
    throw new Error(`${data}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(atual)}`);
  }
};

verificar('2026-12-24', null);
verificar('2026-12-25', { tipo: 'inicio', titulo: 'Férias' });
verificar('2026-12-28', { tipo: 'continuacao', titulo: '' });
verificar('2026-12-31', { tipo: 'fim', titulo: '' });
verificar('2027-01-01', null);

console.log('Segmentação de evento multidiário verificada.');
