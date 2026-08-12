const state = { layers: [{ neurons: 1, activation: 'sigmoid' }], selectedModel: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const orDataset = [{input:[0,0],target:0},{input:[0,1],target:1},{input:[1,0],target:1},{input:[1,1],target:1}];

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json().catch(() => ({ error: 'Nieprawidłowa odpowiedź serwera' }));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}


function calculateParameters() {
  let inputs = Number($('#input-size').value) || 0;
  let count = 0;
  state.layers.forEach(layer => { count += layer.neurons * inputs + layer.neurons; inputs = layer.neurons; });
  return count;
}

function renderLayers() {
  const root = $('#layers'); root.innerHTML = '';
  state.layers.forEach((layer, index) => {
    const connector = document.createElement('div'); connector.className = 'connector'; root.append(connector);
    const node = document.createElement('div'); node.className = `flow-node ${index === state.layers.length - 1 ? 'output' : ''}`;
    node.innerHTML = `<i></i><div><span>${index === state.layers.length - 1 ? 'OUTPUT' : `LAYER ${index + 1}`}</span><b>${layer.neurons} neuron${layer.neurons === 1 ? '' : 's'}</b></div><div class="layer-controls"><input type="number" min="1" max="512" value="${layer.neurons}" aria-label="Neurony warstwy ${index + 1}"><select aria-label="Aktywacja warstwy ${index + 1}">${['sigmoid','relu','tanh','linear','leaky_relu','step'].map(a => `<option ${a === layer.activation ? 'selected' : ''}>${a}</option>`).join('')}</select>${state.layers.length > 1 ? '<button class="remove-layer" title="Usuń warstwę">×</button>' : ''}</div>`;
    node.querySelector('input').addEventListener('input', e => { layer.neurons = Math.max(1, Math.min(512, Number(e.target.value) || 1)); updateSummary(); });
    node.querySelector('select').addEventListener('change', e => { layer.activation = e.target.value; });
    node.querySelector('.remove-layer')?.addEventListener('click', () => { state.layers.splice(index, 1); renderLayers(); });
    root.append(node);
  }); updateSummary();
}

function updateSummary() { $('#input-count').textContent = $('#input-size').value; $('#layer-count').textContent = state.layers.length; $('#parameter-count').textContent = calculateParameters(); }
function addLayer() { if (state.layers.length >= 10) return; state.layers.splice(Math.max(0, state.layers.length - 1), 0, { neurons: 4, activation: 'relu' }); renderLayers(); }
$('#add-layer').addEventListener('click', addLayer); $('#flow-add').addEventListener('click', addLayer); $('#input-size').addEventListener('input', updateSummary);

$('#dataset-select').addEventListener('change', event => { const custom = event.target.value === 'custom'; $('#custom-dataset-wrap').hidden = !custom; $('#dataset-preview').hidden = custom; });

$('#train-button').addEventListener('click', async () => {
  const button = $('#train-button'); $('#global-error').textContent = ''; button.disabled = true; button.innerHTML = '<span>◌</span> Training…';
  try {
    const dataset = $('#dataset-select').value === 'or' ? orDataset : JSON.parse($('#custom-dataset').value);
    const result = await api('/api/train', { method: 'POST', body: JSON.stringify({ name: $('#model-name').value, input_size: Number($('#input-size').value), layers: state.layers, learning_rate: Number($('#learning-rate').value), epochs: Number($('#epochs').value), dataset }) });
    $('#result-panel').hidden = false; $('#result-engine').textContent = `${result.engine} ${result.engine_version}`; $('#result-model').textContent = result.summary.name; $('#result-params').textContent = result.summary.parameters; $('#training-report').textContent = result.report;
    const predictionsRoot = $('#prediction-results'); predictionsRoot.replaceChildren();
    dataset.forEach((sample, i) => {
      const row = document.createElement('span'); row.className = 'prediction';
      const value = document.createElement('b'); value.textContent = result.predictions[i];
      const output = document.createElement('small'); output.textContent = `(${Number(result.outputs[i]).toFixed(4)})`;
      row.append(document.createTextNode(`[${sample.input.join(', ')}] → `), value, document.createTextNode(' '), output);
      predictionsRoot.append(row);
    });
    $('#result-panel').scrollIntoView({ behavior: 'smooth', block: 'center' });
  } catch (error) { $('#global-error').textContent = error.message; }
  finally { button.disabled = false; button.innerHTML = '<span>▶</span> Train with tota'; }
});

function messageElement(text, className = '') {
  const element = document.createElement('p'); element.textContent = text; element.className = className; return element;
}
async function loadModels() {
  const root = $('#models-grid'); root.replaceChildren(messageElement('Loading…'));
  try {
    const data = await api('/api/models'); root.replaceChildren();
    if (!data.models.length) return root.append(messageElement('Brak zapisanych modeli. Wytrenuj pierwszy model.'));
    data.models.forEach(model => {
      const card = document.createElement('article'); card.className = 'model-card';
      const meta = document.createElement('span'); meta.textContent = `tota model · ${model.layers} layer(s)`;
      const title = document.createElement('h3'); title.textContent = model.name;
      const details = document.createElement('p'); details.textContent = `${model.parameters} parameters · Input ${model.input_size}`;
      const button = document.createElement('button'); button.textContent = 'Run prediction →';
      button.addEventListener('click', () => selectModel(model.id, Number(model.input_size)));
      card.append(meta, title, details, button); root.append(card);
    });
  } catch (error) { root.replaceChildren(messageElement(error.message, 'error')); }
}
function selectModel(id, inputSize) { state.selectedModel = id; $('#predict-title').textContent = `Test · ${id}`; $('#predict-input').placeholder = Array(inputSize).fill('0').join(', '); $('#predict-panel').hidden = false; $('#predict-panel').scrollIntoView({behavior:'smooth'}); }
$('#predict-form').addEventListener('submit', async event => {
  event.preventDefault(); const root = $('#predict-result');
  try {
    const input = $('#predict-input').value.split(',').map(value => Number(value.trim()));
    const result = await api(`/api/models/${state.selectedModel}/predict`, {method:'POST',body:JSON.stringify({input})});
    const output = document.createElement('div'); output.className = 'prediction-output';
    const label = document.createTextNode('Class: '); const value = document.createElement('b'); value.textContent = result.class;
    output.append(label, value, document.createElement('br'), document.createTextNode(`Output: ${result.output.map(v=>Number(v).toFixed(6)).join(', ')}`));
    root.replaceChildren(output);
  } catch(error) { root.replaceChildren(messageElement(error.message, 'error')); }
});
$('#refresh-models').addEventListener('click', loadModels);

$$('.nav-item').forEach(button => button.addEventListener('click', () => { $$('.nav-item').forEach(item => item.classList.remove('active')); button.classList.add('active'); const view=button.dataset.view; $('#create-view').hidden=view!=='create'; $('#models-view').hidden=view!=='models'; $('#view-title').textContent=view==='create'?'Create model':'My models'; if(view==='models') loadModels(); }));

renderLayers();
(async () => { try { const health = await fetch('/api/health').then(response => response.json()); $('#engine-version').textContent = `${health.engine} ${health.engine_version}`; } catch {} })();
