'use strict';

// All data and model requests stay on this app's origin. No external UI dependencies.
const $ = id => document.getElementById(id);
const colors = {brain:'#004BDF', vision:'#000000', worker:'#687CAC', embed:'#8795B5', rerank:'#A9B6D0'};
const roleNames = {brain:'REASONING', vision:'VISION', worker:'SQL WORKER', embed:'RETRIEVAL', rerank:'RERANKER'};
const toolNames = {query_mes:'Production records', search_docs:'Controlled plant records', search_video:'Station video', long_context_review:'Full document cross check', draft_8d:'Proposed 8D'};
const evidence = new Map();
const activeModels = new Map();
const activeTools = new Map();
const rateSamples = [];
let config, chartData, selectedPoint, currentRun, controller, currentUnits;
let running = false, completeCoverage = false, lastElapsed = null, timer, toastTimer;
let unitsRequest = 0;

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = value;
  if (className) element.className = className;
  return element;
}
function number(value, digits = 1) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' :
    Number(value).toLocaleString('en-GB', {maximumFractionDigits:digits});
}
function fixed(value, digits = 1) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}
function shortModel(role) {
  return (config?.models[role]?.repo.split('/')[1] || role).replace(/-NVFP4$/, '').replace(/-/g, ' ');
}
function dateLabel(day) {
  return new Date(day + 'T12:00:00Z').toLocaleDateString('en-GB', {weekday:'short', day:'numeric', month:'short', timeZone:'UTC'});
}
function toast(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6500);
}
function setStatus(message, blocked = false) {
  $('run-status').textContent = message;
  $('run-status').classList.toggle('blocked', blocked);
}
function investigationError(message) {
  if (/JSON|citation|audit|round limit/i.test(message)) return 'The model response did not pass validation. Collected evidence remains available for inspection.';
  if (/time.*limit|budget|timeout/i.test(message)) return 'The investigation reached its time limit. Collected evidence remains available for inspection.';
  return message;
}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
  });
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = response.statusText; }
    throw Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}
function setTab(name) {
  const records = name === 'records';
  $('documents').hidden = !records;
  $('units').hidden = records;
  for (const [id, active] of [['show-docs', records], ['show-units', !records]]) {
    $(id).classList.toggle('active', active);
    $(id).setAttribute('aria-selected', String(active));
  }
}
function scrollTrace() { $('trace').scrollTop = $('trace').scrollHeight; }
function traceEvent(event) {
  if (event.type === 'model_done') {
    const entry = activeModels.get(event.role);
    if (entry) {
      entry.classList.add('done');
      const measurement = event.measurement;
      entry.append(node('div', number(measurement.elapsed_s) + ' s · ' + number(measurement.tokens_per_second, 0) + ' tok/s', 'meta'));
      activeModels.delete(event.role);
    }
    return;
  }
  if (!['model_start', 'tool_start', 'error'].includes(event.type)) return;
  $('trace').querySelector('.trace-empty')?.remove();
  const entry = node('div', '', 'trace-step');
  const heading = node('div', '', 'trace-role');
  heading.append(node('span', event.type === 'error' ? 'INVESTIGATION INCOMPLETE' : roleNames[event.role] || 'LOCAL TOOL'),
    node('span', number(event.elapsed_s) + ' s'));
  entry.append(heading, node('div', event.message || event.task || toolNames[event.tool] || event.activity, 'activity'));
  if (event.type === 'model_start') {
    activeModels.set(event.role, entry);
    $('current-model').textContent = shortModel(event.role);
    $('current-activity').textContent = event.task || event.activity.charAt(0).toUpperCase() + event.activity.slice(1) + '.';
    $('trace-context').textContent = event.value || 'Connect the returned evidence and decide what still needs checking.';
    $('current-activity').title = event.basis || 'Public task intent, not private model reasoning.';
  }
  if (event.type === 'tool_start') {
    entry.dataset.started = event.elapsed_s;
    activeTools.set(event.tool, entry);
    $('current-model').textContent = shortModel(event.role);
    $('current-activity').textContent = event.task || toolNames[event.tool];
    $('trace-context').textContent = event.value || 'Return inspectable evidence for the engineering review.';
  }
  if (event.type === 'error') entry.classList.add('error');
  $('trace').append(entry);
  scrollTrace();
}
function updateCoverage() {
  for (const [id, tools] of [
    ['coverage-data', ['query_mes']], ['coverage-video', ['search_video']],
    ['coverage-docs', ['search_docs', 'long_context_review']]
  ]) {
    const matches = [...evidence.values()].filter(item => tools.includes(item.tool));
    const returned = matches.some(item => !item.result.error &&
      (item.tool !== 'search_video' || item.result.clips?.length) &&
      (item.tool !== 'search_docs' || item.result.passages?.length));
    $(id).classList.toggle('returned', returned);
    $(id).classList.toggle('unavailable', !returned && matches.length > 0);
    $(id).querySelector('i').textContent = returned ? '✓' : matches.length ? '!' : '—';
    $(id).title = returned ? 'Evidence returned in this investigation' : matches.length ? 'Source unavailable or empty' : 'Awaiting source evidence';
  }
}
function sourceDescription(item) {
  const result = item.result;
  if (result.error) return 'Unavailable · inspect the recorded error';
  if (item.tool === 'query_mes') return number(result.rows.length, 0) + ' returned rows' + (result.truncated ? ' · row limit reached' : '');
  if (item.tool === 'search_docs') return number(result.passages.length, 0) + ' cited passages';
  if (item.tool === 'search_video') return number(result.clips.length, 0) + ' timestamped clips';
  if (item.tool === 'long_context_review') return number(result.documents.length, 0) + ' complete documents';
  return 'Open the returned evidence';
}
function renderSources() {
  const grid = node('div', '', 'source-grid');
  for (const [id, item] of evidence) {
    const card = node('button', '', 'source-card' + (item.result.error ? ' failed' : ''));
    card.id = id;
    card.append(node('span', id + ' / ' + (item.result.error ? 'UNAVAILABLE' : 'RETURNED'), 'source-ref'),
      node('strong', toolNames[item.tool] || item.tool), node('span', sourceDescription(item), 'source-meta'));
    card.onclick = () => openEvidence(id);
    grid.append(card);
  }
  $('documents').replaceChildren(grid);
  $('source-count').textContent = [...evidence.values()].filter(item => !item.result.error).length;
}
function highlightedPassage(value) {
  const paragraph = node('div');
  for (const line of value.split('\n')) {
    paragraph.append(node(/star pattern|reference fixture|recalibrat|angle channel/i.test(line) ? 'mark' : 'span', line), document.createTextNode('\n'));
  }
  return paragraph;
}
function resultTable(rows, columns) {
  const table = node('table', '', 'unit-table');
  const head = node('thead');
  const tr = node('tr');
  for (const key of columns) tr.append(node('th', key.replace(/_/g, ' ')));
  head.append(tr); table.append(head);
  const body = node('tbody');
  for (const row of rows) {
    const line = node('tr');
    for (const key of columns) line.append(node('td', row[key] === null ? '—' : String(row[key])));
    body.append(line);
  }
  table.append(body);
  return table;
}
function openEvidence(id) {
  const item = evidence.get(id);
  if (!item) return;
  $('evidence-detail-label').textContent = id + ' / RETURNED SOURCE';
  $('evidence-detail-title').textContent = toolNames[item.tool] || item.tool;
  const box = $('evidence-detail'); box.replaceChildren();
  const result = item.result;
  if (result.error) box.append(node('p', result.error, 'detail-review'));
  else if (item.tool === 'query_mes') {
    box.append(node('pre', result.sql, 'detail-sql'));
    const status = node('p', '', 'detail-meta'); box.append(status);
    const wrap = node('div', '', 'detail-table-wrap'); box.append(wrap);
    let shown = Math.min(100, result.rows.length);
    const draw = () => {
      wrap.replaceChildren(resultTable(result.rows.slice(0, shown), result.columns));
      status.textContent = number(shown, 0) + ' of ' + number(result.rows.length, 0) + ' returned rows shown. ' +
        (result.truncated ? 'Query output reached the row limit; these are not a population total.' : 'Read only MES query.');
    };
    draw();
    if (shown < result.rows.length) {
      const more = node('button', 'Show more returned rows ↗', 'text-button');
      more.onclick = () => { shown = Math.min(shown + 100, result.rows.length); draw(); more.hidden = shown === result.rows.length; };
      box.append(more);
    }
    if (result.review) box.append(node('p', 'SQL review: ' + result.review, 'detail-meta'));
  } else if (item.tool === 'search_docs') {
    box.append(node('p', result.mode, 'detail-meta'));
    for (const passage of result.passages) {
      const article = node('article', '', 'detail-passage');
      article.append(node('div', passage.id, 'citation'), highlightedPassage(passage.text)); box.append(article);
    }
  } else if (item.tool === 'long_context_review') {
    box.append(node('p', 'Model cross check. Interpretations still require engineering review.', 'detail-meta'));
    box.append(node('p', result.review, 'detail-review'));
    for (const document of result.documents) {
      const detail = node('details', '', 'detail-document');
      detail.append(node('summary', document.id), node('pre', document.text)); box.append(detail);
    }
  } else if (item.tool === 'search_video') {
    for (const clip of result.clips) {
      const article = node('article', '', 'detail-passage');
      const button = node('button', (clip.flagged_timestamp || clip.timestamp).replace('T', ' ') + ' · Watch clip ↗', 'text-button');
      button.onclick = () => { selectClip(clip, id); $('evidence-dialog').close(); };
      article.append(button, node('p', clip.caption)); box.append(article);
    }
  } else box.append(node('pre', JSON.stringify(result, null, 2), 'detail-sql'));
  $('evidence-dialog').showModal();
}
function selectClip(clip, id, button) {
  const video = $('video');
  video.onloadedmetadata = () => {
    video.currentTime = clip.flagged_second ?? 0;
    video.play().catch(() => {});
  };
  video.src = '/media/' + clip.chunk.replace(/^data\/video\//, '');
  $('video-state').textContent = id + ' / ' + (clip.flagged_timestamp ? 'VLM FLAGGED TIMESTAMP' : 'RETURNED VIDEO EVIDENCE');
  $('video-caption').textContent = clip.caption;
  $('video-note').textContent = (clip.flagged_timestamp || clip.timestamp).replace('T', ' ') + ' · Review the visible sequence against the instruction.';
  for (const child of $('clip-buttons').children) child.classList.toggle('active', child === button);
}
function addEvidence(event) {
  evidence.set(event.evidence_id, {tool:event.tool, result:event.result});
  const entry = activeTools.get(event.tool);
  if (entry) {
    entry.classList.add('done');
    entry.append(node('div', event.result.error ? 'Source unavailable · ' + event.evidence_id :
      number(event.elapsed_s - Number(entry.dataset.started)) + ' s · ' + event.evidence_id, 'meta'));
    activeTools.delete(event.tool);
  }
  if (event.tool === 'search_docs' && !event.result.error) $('retrieval-mode').textContent = event.result.mode;
  if (event.tool === 'search_video' && !event.result.error) {
    const hadClips = $('clip-buttons').children.length > 0;
    event.result.clips.forEach((clip, index) => {
      const button = node('button', (clip.flagged_timestamp || clip.timestamp).replace('T', ' ').slice(11) + ' ↗');
      button.onclick = () => selectClip(clip, event.evidence_id, button);
      $('clip-buttons').append(button);
      if (!hadClips && index === 0) selectClip(clip, event.evidence_id, button);
    });
  }
  if (event.tool === 'search_video' && event.result.error) {
    $('video-state').textContent = 'VISION EVIDENCE UNAVAILABLE';
    $('video-caption').textContent = 'The visible sequence has not been verified.';
    $('video-note').textContent = 'No observation has been substituted. See the source error.';
  }
  renderSources(); updateCoverage(); scrollTrace();
}
function citationText(container, value) {
  for (const part of value.split(/(\[E\d+\])/g)) {
    if (/^\[E\d+\]$/.test(part)) {
      const id = part.slice(1, -1), button = node('button', part, 'citation-link');
      button.title = 'Inspect source ' + id; button.onclick = () => openEvidence(id); container.append(button);
    } else container.append(document.createTextNode(part));
  }
}
function renderAnswer(value) {
  const box = $('answer'); box.replaceChildren(); box.classList.remove('answer-idle');
  const parts = value.split(/(?:^|\n)(Findings?|Evidence|Contain now|Open checks):\s*/i);
  if (parts.length < 3) { citationText(box, value); return; }
  if (parts[0].trim()) citationText(box, parts[0]);
  for (let i = 1; i < parts.length; i += 2) {
    const section = node('div', '', 'answer-section'); section.append(node('strong', parts[i]));
    const content = node('div'); citationText(content, parts[i + 1] || ''); section.append(content); box.append(section);
  }
}
function setRunning(value) {
  running = value; document.body.classList.toggle('investigating', value);
  $('ask').disabled = value; $('question').disabled = value; $('stop').hidden = !value;
  for (const preset of $('presets').children) preset.disabled = value;
  $('replay').disabled = value || !config.replay_available;
  $('ask').firstElementChild.textContent = value ? 'Investigating' : 'Investigate';
  $('ask').setAttribute('aria-busy', String(value));
}
async function investigate(question) {
  if (!config) { toast('Connecting to the local application. Try again in a moment.'); return; }
  if (running) return;
  if (!question.trim()) { toast('Enter a manufacturing question to begin.'); $('question').focus(); return; }
  controller = new AbortController(); currentRun = null; lastElapsed = null; completeCoverage = false;
  evidence.clear(); activeModels.clear(); activeTools.clear();
  $('question').value = question;
  for (const id of ['trace', 'documents', 'clip-buttons', 'answer']) $(id).replaceChildren();
  $('source-count').textContent = '0'; $('retrieval-mode').textContent = 'Gathering cited records';
  $('answer').classList.remove('answer-idle');
  $('answer').append(node('p', 'The investigation is working through the evidence. Proposed findings will appear here.', 'meta'));
  $('agent-time').textContent = '—'; $('agent-time-label').textContent = 'Agent · measuring this run';
  $('report').disabled = true; setTab('records'); updateCoverage();
  $('focus-answer').disabled = true; $('focus-answer').setAttribute('aria-pressed', 'false'); $('focus-answer').textContent = '↗';
  $('focus-answer').title = 'Expand findings'; $('focus-answer').setAttribute('aria-label', 'Expand findings');
  document.querySelector('.evidence-panel').classList.remove('focus-findings');
  $('replay-badge').hidden = !$('replay').checked;
  $('trace-label').textContent = $('replay').checked ? 'THE RECORDED INVESTIGATION' : 'THE LIVE INVESTIGATION';
  $('current-model').textContent = 'CONNECTING TO LOCAL MODELS';
  $('current-activity').textContent = 'Following the evidence.';
  setStatus('Gathering production data, visual evidence and controlled records.'); setRunning(true);
  document.dispatchEvent(new CustomEvent('p7:run-start', {detail:{question, replay:$('replay').checked}}));
  const start = performance.now();
  timer = setInterval(() => { $('clock').textContent = number((performance.now() - start) / 1000) + ' s'; }, 100);
  let failed = false, answered = false, stopped = false, serverDone = false;
  try {
    const response = await fetch('/api/investigate', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question, replay:$('replay').checked}), signal:controller.signal});
    if (!response.ok) { const error = await response.json(); throw Error(error.detail); }
    const reader = response.body.getReader(), decoder = new TextDecoder(); let buffer = '';
    const consume = part => {
      const line = part.split('\n').find(line => line.startsWith('data: '));
      if (!line) return;
      const event = JSON.parse(line.slice(6));
      currentRun = event.run_id; lastElapsed = event.elapsed_s; traceEvent(event);
      document.dispatchEvent(new CustomEvent('p7:run-event', {detail:event}));
      if (event.type === 'done') serverDone = true;
      if (event.type === 'start' && event.replay) {
        $('question').value = event.question;
        setStatus('Replaying the original question, evidence and recorded timing.');
      }
      if (event.type === 'evidence') addEvidence(event);
      if (event.type === 'answer') {
        answered = true; completeCoverage = Boolean(event.complete_sources); renderAnswer(event.text);
        $('report').disabled = !completeCoverage;
        $('focus-answer').disabled = false;
        setStatus(completeCoverage ? 'Data, video and documents returned evidence. Review the citations before acting.' :
          'Incomplete evidence. Sequence and full root cause are not accepted. The 8D report remains locked.', !completeCoverage);
      }
      if (event.type === 'error') {
        failed = true; setStatus(investigationError(event.message), true);
        if (!answered) renderAnswer('No accepted finding was produced. You can still inspect the sources collected above.');
      }
    };
    while (true) {
      const {done, value} = await reader.read();
      if (done) { buffer += decoder.decode(); if (buffer.trim()) consume(buffer); break; }
      buffer += decoder.decode(value, {stream:true}); let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) { consume(buffer.slice(0, boundary)); buffer = buffer.slice(boundary + 2); }
    }
    if (!answered && !failed) { failed = true; setStatus('The stream ended without a completed finding. Inspect the returned sources.', true); }
  } catch (error) {
    stopped = error.name === 'AbortError'; failed = !stopped;
    setStatus(stopped ? 'Stopped. Collected evidence remains available on this screen.' : error.message, true);
    if (!stopped) toast(error.message);
  } finally {
    clearInterval(timer); setRunning(false);
    const elapsed = serverDone && lastElapsed !== null ? lastElapsed : (performance.now() - start) / 1000;
    $('clock').textContent = number(elapsed) + ' s';
    $('agent-time').textContent = number(elapsed) + ' s';
    $('agent-time-label').textContent = $('replay').checked ? 'Replay · recorded time' :
      stopped ? 'Stopped · measured time' : failed ? 'Failed · measured time' : completeCoverage ? 'Agent · measured time' : 'Incomplete · measured time';
    $('current-model').textContent = $('replay').checked ? 'RECORDED RUN' : 'LOCAL INVESTIGATION';
    $('current-activity').textContent = stopped ? 'Investigation stopped.' : failed || !completeCoverage ? 'Open checks remain.' : 'Ready for your review.';
    $('trace-context').textContent = 'Inspect the evidence. A proposed finding still needs engineering judgement.';
    document.dispatchEvent(new CustomEvent('p7:run-end', {detail:{elapsed_s:elapsed, failed, stopped,
      answered, complete_sources:completeCoverage, replay:$('replay').checked, run_id:currentRun}}));
  }
}

function svgNode(tag, attrs, value) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, val] of Object.entries(attrs)) element.setAttribute(key, val);
  if (value !== undefined) element.textContent = value;
  return element;
}
function chartDefinition() {
  const kind = $('chart-type').value, isFPY = kind === 'fpy';
  return {kind, isFPY, rows:isFPY ? chartData.fpy : chartData.torque,
    key:isFPY ? 'fpy_pct' : kind === 'angle' ? 'angle_deg' : 'torque_nm',
    groupKey:isFPY ? 'shift' : 'tool_id', unit:isFPY ? '%' : kind === 'angle' ? '°' : 'Nm'};
}
function setSignal(row, definition = chartDefinition()) {
  selectedPoint = {row, kind:definition.kind};
  const previous = definition.rows.filter(item => item[definition.groupKey] === row[definition.groupKey] &&
    item.production_date < row.production_date).at(-1);
  $('signal-value').textContent = fixed(row[definition.key]); $('signal-unit').textContent = definition.unit;
  const group = definition.isFPY ? 'Shift ' + row.shift : row.tool_id;
  $('signal-date').textContent = dateLabel(row.production_date) + ' · ' + group + ' · MES';
  if (previous) {
    const change = row[definition.key] - previous[definition.key];
    $('signal-change').textContent = (change > 0 ? '+' : change < 0 ? '−' : '') + fixed(Math.abs(change)) +
      (definition.isFPY ? ' pp' : ' ' + definition.unit) + ' vs previous ' + (definition.isFPY ? 'same shift' : 'tool day');
  } else $('signal-change').textContent = definition.isFPY ? 'Measured first pass yield' : 'Measured daily tool mean';
  document.dispatchEvent(new CustomEvent('p7:selection', {detail:{date:row.production_date,
    shift:definition.isFPY ? row.shift : null, tool_id:definition.isFPY ? null : row.tool_id}}));
}
function drawChart() {
  if (!chartData) return;
  const definition = chartDefinition(), {rows, key, groupKey, isFPY} = definition;
  if (!rows.length) return;
  if (!selectedPoint || selectedPoint.kind !== definition.kind) {
    const initial = isFPY ? rows.reduce((a, b) => b[key] < a[key] ? b : a) :
      rows.find(row => row.production_date === selectedPoint?.row.production_date && row.tool_id === 'T40-B') || rows[0];
    setSignal(initial, definition);
  }
  const svg = $('chart'); svg.replaceChildren(); $('chart-tooltip').hidden = true;
  const width = svg.clientWidth || 720, height = svg.clientHeight || 245;
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
  const dates = [...new Set(rows.map(row => row.production_date))], groups = [...new Set(rows.map(row => row[groupKey]))];
  const values = rows.map(row => row[key]), padding = isFPY ? 4 : definition.kind === 'angle' ? 1.5 : .08;
  const lo = isFPY ? Math.max(0, Math.floor(Math.min(...values) / 4) * 4 - 4) : Math.min(...values) - padding;
  const hi = isFPY ? Math.min(100, Math.max(...values) + padding) : Math.max(...values) + padding;
  const bottom = height - 29;
  const x = day => 43 + dates.indexOf(day) * (width - 59) / Math.max(1, dates.length - 1);
  const y = value => bottom - (value - lo) / Math.max(.001, hi - lo) * (bottom - 15);
  const palette = ['#004BDF', '#000000', '#8795B5'];
  for (let i = 0; i < 4; i++) {
    const value = lo + (hi - lo) * i / 3, yy = y(value);
    svg.append(svgNode('line', {x1:38,x2:width-10,y1:yy,y2:yy,stroke:'#FFFFFF','stroke-width':1}),
      svgNode('text', {x:30,y:yy+4,'text-anchor':'end','font-size':11,fill:'#000'}, number(value, isFPY ? 0 : 2)));
  }
  for (const index of [...new Set([0, Math.round((dates.length - 1) / 3), Math.round((dates.length - 1) * 2 / 3), dates.length - 1])]) {
    svg.append(svgNode('text', {x:x(dates[index]),y:height-7,'text-anchor':'middle','font-size':11,fill:'#000'}, dateLabel(dates[index]).split(' ').slice(1).join(' ')));
  }
  const selection = selectedPoint.row;
  svg.append(svgNode('line', {x1:x(selection.production_date),x2:x(selection.production_date),y1:10,y2:bottom+3,stroke:'#000','stroke-opacity':.18,'stroke-dasharray':'3 4'}));
  $('chart-legend').replaceChildren();
  groups.forEach((group, index) => {
    const subset = rows.filter(row => row[groupKey] === group), color = palette[index % palette.length], offset = isFPY ? (index - 1) * 4 : 0;
    const points = subset.map(row => (x(row.production_date) + offset) + ',' + y(row[key]));
    if (group === selection[groupKey]) svg.append(svgNode('polygon', {points:(x(subset[0].production_date)+offset)+','+bottom+' '+points.join(' ')+' '+(x(subset.at(-1).production_date)+offset)+','+bottom,fill:'#FFFFFF','fill-opacity':.24}));
    svg.append(svgNode('polyline', {points:points.join(' '),fill:'none',stroke:color,'stroke-width':group === selection[groupKey] ? 2.7 : 1.7,'stroke-linejoin':'round'}));
    for (const row of subset) {
      const active = row === selection;
      const dot = svgNode('circle', {cx:x(row.production_date)+offset,cy:y(row[key]),r:active?6:3.2,fill:color,stroke:active?'#FFFFFF':color,'stroke-width':active?2:0,
        tabindex:0,role:'button','aria-label':row.production_date+' '+(isFPY?'Shift ':'')+group+' '+fixed(row[key])+definition.unit});
      const label = dateLabel(row.production_date) + ' · ' + (isFPY ? 'Shift ' : '') + group + ' · ' + fixed(row[key]) + definition.unit;
      dot.append(svgNode('title', {}, label));
      const tooltip = () => { $('chart-tooltip').textContent = label; $('chart-tooltip').hidden = false; };
      dot.onpointerenter = tooltip; dot.onfocus = tooltip;
      dot.onpointerleave = dot.onblur = () => { $('chart-tooltip').hidden = true; };
      dot.onclick = () => { setSignal(row, definition); drawChart(); inspectSelected(); };
      dot.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); dot.onclick(); } };
      svg.append(dot);
    }
    const legend = node('span'), mark = node('i', '', 'legend-mark'); mark.style.background = color;
    legend.append(mark, document.createTextNode(isFPY ? 'Shift ' + group : group)); $('chart-legend').append(legend);
  });
}
async function inspectSelected() {
  if (!selectedPoint) return;
  const {row, kind} = selectedPoint, request = ++unitsRequest;
  const query = new URLSearchParams({date:row.production_date});
  if (kind === 'fpy') query.set('shift', row.shift);
  else query.set('tool_id', row.tool_id);
  setTab('units'); $('units').replaceChildren(node('p', 'Reading the selected production records…', 'meta'));
  try {
    const data = await api('/api/units?' + query);
    if (request !== unitsRequest) return;
    currentUnits = {data, label:dateLabel(row.production_date) + ' · ' + (kind === 'fpy' ? 'Shift ' + row.shift : row.tool_id + ' · all shifts')};
    renderUnits();
  } catch (error) { if (request === unitsRequest) { $('units').replaceChildren(node('p', error.message, 'meta')); toast(error.message); } }
}
function renderUnits() {
  const {data, label} = currentUnits, box = $('units'); box.replaceChildren();
  const heading = node('div', '', 'unit-heading'); heading.append(node('span', label));
  const select = node('select'); select.setAttribute('aria-label', 'Filter unit shipping status');
  for (const [value, caption] of [['all','All statuses'],['shipped','Shipped'],['held','Held']]) {
    const option = node('option', caption); option.value = value; select.append(option);
  }
  heading.append(select); box.append(heading);
  const count = node('div', '', 'unit-count'), wrap = node('div', '', 'unit-table-wrap'); box.append(count, wrap);
  const draw = () => {
    const rows = data.rows.filter(row => select.value === 'all' || row.status === select.value);
    count.textContent = number(rows.length, 0) + ' shown / ' + number(data.rows.length, 0) + ' returned units' +
      (data.truncated ? ' · query row limit reached' : '') + ' · Shipping status is not Quality disposition.';
    const display = rows.map(row => ({unit:row.unit_id, status:row.status, 'first pass':row.first_pass?'Pass':'Reject', lot:row.supplier_lot}));
    const table = resultTable(display, ['unit','status','first pass','lot']);
    [...table.querySelectorAll('tbody tr')].forEach((line, index) => {
      const button = node('button', rows[index].unit_id, 'unit-open');
      button.onclick = () => window.Automotive?.openUnit(rows[index].unit_id);
      line.firstElementChild.replaceChildren(button);
    });
    for (const td of table.querySelectorAll('td')) if (td.textContent === 'held') td.classList.add('held');
    wrap.replaceChildren(table);
  };
  select.onchange = draw; draw();
}

function drawRateHistory(value) {
  rateSamples.push(value); if (rateSamples.length > 40) rateSamples.shift();
  const svg = $('throughput-chart'); svg.replaceChildren();
  const valid = rateSamples.filter(value => value !== null && value !== undefined);
  if (!valid.length) return;
  const max = Math.max(1, ...valid);
  svg.append(svgNode('line', {x1:0,x2:260,y1:30,y2:30,stroke:'#FFFFFF'}));
  const points = rateSamples.map((value, index) => value === null || value === undefined ? null :
    (index * 260 / Math.max(1, rateSamples.length - 1)) + ',' + (29 - 26 * value / max));
  let segment = [];
  const flush = () => { if (segment.length) svg.append(svgNode('polyline', {points:segment.join(' '),fill:'none',stroke:'#004BDF','stroke-width':1.5})); segment = []; };
  for (const point of points) { if (point) segment.push(point); else flush(); } flush();
}
async function poll() {
  try {
    const data = await api('/api/telemetry'), ready = data.models.filter(model => model.healthy).length;
    document.dispatchEvent(new CustomEvent('p7:telemetry', {detail:data}));
    const allReady = ready === data.models.length;
    $('hbm').textContent = number(data.gpu.used_gb); $('hbm-capacity').textContent = number(data.gpu.total_gb, 0) + ' GB device';
    $('gpu-load').textContent = number(data.gpu.utilization_pct, 0) + '% GPU';
    $('sessions').textContent = number(data.active_sessions, 0); $('tps').textContent = number(data.total_tokens_per_second, 0);
    $('network').textContent = number(data.network.transmitted_bytes_since_start, 0);
    $('network-scope').textContent = (data.network.interface || 'Unknown interface') + ' · since ' +
      new Date(data.network.baseline_at * 1000).toLocaleTimeString('en-GB') + '. Includes control traffic; does not classify payloads. Remote viewers receive UI evidence.';
    $('ram').textContent = number(data.ram.available_gb, 0) + ' GB coherent system RAM available';
    $('health-label').textContent = ready + ' / ' + data.models.length + ' ready';
    $('system-status').textContent = allReady ? 'Models ready' : ready + ' / ' + data.models.length + ' ready';
    $('system-dot').classList.toggle('ready', allReady);
    const missing = data.models.filter(model => !model.healthy).map(model => roleNames[model.role].toLowerCase());
    $('readiness-text').textContent = allReady ? 'All local model endpoints are ready. Findings still require evidence and engineering review.' :
      ready + ' of ' + data.models.length + ' local endpoints ready · ' + missing.join(', ') + ' unavailable. Investigation coverage will be incomplete.';
    $('hbm-bar').replaceChildren(); $('memory-models').replaceChildren();
    for (const [role, gb] of Object.entries(data.gpu.by_model_gb)) {
      const segment = node('div'); segment.style.width = 100 * gb / data.gpu.total_gb + '%'; segment.style.background = colors[role] || '#8C8C8C';
      segment.title = role + ' · ' + number(gb) + ' GB'; $('hbm-bar').append(segment);
      const row = node('div', '', 'memory-row'), label = node('span', role === 'other or file cache' ? 'Other / file cache' : role.charAt(0).toUpperCase() + role.slice(1));
      const swatch = node('i', '', 'swatch'); swatch.style.background = colors[role] || '#8C8C8C'; label.prepend(swatch);
      const model = data.models.find(model => model.role === role);
      const rate = model ? config?.models[role]?.runner === 'pooling' ? 'pooling' : number(model.tokens_per_second, 0) + ' t/s' : '';
      row.append(label, node('span', number(gb) + ' GB'), node('span', rate, 'per-model-rate'));
      $('memory-models').append(row);
    }
    for (const model of data.models.filter(model => !model.healthy && !(model.role in data.gpu.by_model_gb))) {
      const row = node('div', '', 'memory-row missing-model');
      row.append(node('span', model.role.charAt(0).toUpperCase() + model.role.slice(1)), node('span', 'Unavailable'), node('span', '— t/s', 'per-model-rate'));
      $('memory-models').append(row);
    }
    $('model-rates').replaceChildren();
    for (const model of data.models) {
      const row = node('div', '', 'model-row' + (model.healthy ? '' : ' unavailable'));
      const dot = node('i', '', 'status-dot' + (model.healthy ? ' ready' : ''));
      const name = node('span', shortModel(model.role), 'model-name'); name.title = model.model;
      const rate = model.healthy ? config?.models[model.role]?.runner === 'pooling' ? 'Pooling' : number(model.tokens_per_second, 0) + ' tok/s' : 'Unavailable';
      row.append(dot, name, node('span', rate)); $('model-rates').append(row);
    }
    drawRateHistory(data.total_tokens_per_second);
    const jobs = Object.values(data.jobs);
    const job = jobs.at(-1);
    $('load').disabled = running || !allReady || Boolean(job?.running);
    if (job) $('load-status').textContent = job.completed + ' completed · ' + job.failed + ' failed · ' + (job.running ? 'real requests running' : number(job.elapsed_s) + ' s measured');
    else $('load-status').textContent = allReady ? '20 real investigations. Measured throughput.' : 'Requires every model endpoint. ' + missing.join(', ') + ' unavailable.';
  } catch {
    $('system-status').textContent = 'Connection lost'; $('health-label').textContent = 'Telemetry unavailable';
    $('readiness-text').textContent = 'Live telemetry is unavailable. Check the application connection.';
    $('system-dot').classList.remove('ready'); $('load').disabled = true;
    for (const id of ['hbm','tps','sessions','network','gpu-load','hbm-capacity']) $(id).textContent = '—';
    $('memory-models').replaceChildren(node('p', 'Measurements unavailable', 'meta'));
    $('model-rates').replaceChildren(node('p', 'Endpoint status is unknown', 'meta'));
    $('hbm-bar').replaceChildren(); $('ram').textContent = 'System memory measurement unavailable';
    drawRateHistory(null);
  } finally { setTimeout(poll, 1000); }
}
function comparison() {
  const models = Object.values(config.models), total = models.reduce((sum, model) => sum + model.weight_bytes / 1e9, 0);
  const box = $('comparison'); box.replaceChildren();
  const legend = node('div', '', 'comparison-legend');
  for (const model of models) {
    const item = node('span'), mark = node('i', '', 'swatch'); mark.style.background = colors[model.role];
    item.append(mark, document.createTextNode(model.role + ' · ' + number(model.weight_bytes / 1e9) + ' GB')); legend.append(item);
  }
  box.append(legend);
  for (const [label, capacity] of [['Single workstation GPU',96], ['ZGX Nano unified',128], ['Fury HBM',252], ['Fury coherent total',748]]) {
    const row = node('div', '', 'capacity'), heading = node('div', '', 'capacity-heading');
    heading.append(node('span', label + ' / ' + capacity + ' GB'), node('span', number(total) + ' GB weights' + (total > capacity ? ' · exceeds capacity' : ' · before cache and workspace')));
    const track = node('div', '', 'capacity-track'), blocks = node('div', '', 'capacity-weights');
    for (const model of models) { const block = node('div'); block.style.width = model.weight_bytes / 1e9 / 8 + '%'; block.style.background = colors[model.role]; block.title = model.repo; blocks.append(block); }
    const limit = node('div', '', 'limit'); limit.style.left = capacity / 8 + '%'; track.append(blocks, limit); row.append(heading, track); box.append(row);
  }
}

$('ask-form').onsubmit = event => { event.preventDefault(); investigate($('question').value); };
$('stop').onclick = () => controller?.abort();
$('hero').onclick = () => { if (config) { $('chart-type').value = 'fpy'; drawChart(); selectPreset(config.hero); investigate(config.hero); } };
$('question').oninput = () => selectPreset($('question').value);
function selectPreset(question) { for (const button of $('presets').children) button.classList.toggle('active', button.dataset.question === question); }
$('chart-type').onchange = drawChart;
$('inspect-point').onclick = inspectSelected;
$('show-docs').onclick = () => setTab('records'); $('show-units').onclick = () => setTab('units');
for (const id of ['show-docs', 'show-units']) $(id).onkeydown = event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault(); const other = id === 'show-docs' ? 'show-units' : 'show-docs'; $(other).click(); $(other).focus();
  }
};
$('focus-answer').onclick = () => {
  document.dispatchEvent(new CustomEvent('p7:show-result'));
  const focused = document.querySelector('.evidence-panel').classList.toggle('focus-findings');
  $('focus-answer').textContent = focused ? '↙' : '↗'; $('focus-answer').setAttribute('aria-pressed', String(focused));
  $('focus-answer').setAttribute('aria-label', focused ? 'Return to evidence board' : 'Expand findings');
  $('focus-answer').title = focused ? 'Return to evidence board' : 'Expand findings';
};
$('replay').onchange = () => { $('replay-badge').hidden = !$('replay').checked; };
for (const id of ['why', 'why-header']) if ($(id)) $(id).onclick = () => { if (config) { comparison(); $('why-dialog').showModal(); } };
for (const [button, dialog] of [['close-why','why-dialog'],['close-report','report-dialog'],['close-evidence','evidence-dialog'],['close-video','video-dialog'],['close-qr','qr-dialog']]) $(button).onclick = () => $(dialog).close();
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } });
$('open-qr').onclick = () => $('qr-dialog').showModal();
$('expand-video').onclick = () => {
  const original = $('video'), video = node('video'); video.controls = true; video.muted = true; video.playsInline = true; video.src = original.currentSrc || original.src;
  const time = original.currentTime; original.pause(); video.onloadedmetadata = () => { video.currentTime = time; };
  $('expanded-video').replaceChildren(video, node('p', $('video-caption').textContent)); $('video-dialog').showModal();
};
$('video-dialog').addEventListener('close', () => { const expanded = $('expanded-video').querySelector('video'); if (expanded) { $('video').currentTime = expanded.currentTime; expanded.pause(); expanded.removeAttribute('src'); expanded.load(); } });
$('load').onclick = async () => { try { $('load').disabled = true; await api('/api/loadtest', {}); toast('20 real investigations started. Watch live sessions and throughput.'); } catch (error) { $('load-status').textContent = error.message; toast(error.message); } };
$('report').onclick = async () => {
  if (!currentRun || !completeCoverage) return;
  try {
    $('report').disabled = true; $('report').textContent = 'Drafting 8D…';
    const report = await api('/api/report/' + currentRun, {});
    document.dispatchEvent(new CustomEvent('p7:report', {detail:report}));
    $('report-text').textContent = report.markdown; $('report-md').href = '/api/report/' + currentRun + '.md'; $('report-pdf').href = '/api/report/' + currentRun + '.pdf'; $('report-dialog').showModal();
  } catch (error) { setStatus('8D generation blocked: ' + error.message, true); toast(error.message); }
  finally { $('report').disabled = !completeCoverage; $('report').textContent = 'Draft 8D report ↗'; }
};
$('counter-start').onclick = async () => { try { await api('/api/demo-counter/start', {}); toast('Interface counter reset. The new baseline timestamp is shown beside the measured bytes.'); } catch (error) { toast(error.message); } };
$('present').onclick = async () => {
  const enabled = !document.body.classList.contains('presentation-mode');
  document.body.classList.toggle('presentation-mode', enabled); $('present').setAttribute('aria-pressed', String(enabled));
  $('present').textContent = enabled ? 'Exit presentation' : '⛶ Present';
  try { if (enabled && !document.fullscreenElement) await document.documentElement.requestFullscreen?.(); else if (!enabled && document.fullscreenElement) await document.exitFullscreen(); } catch { /* The presentation layout also works without browser fullscreen. */ }
};
document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement) { document.body.classList.remove('presentation-mode'); $('present').setAttribute('aria-pressed', 'false'); $('present').textContent = '⛶ Present'; } });
document.addEventListener('keydown', event => {
  const editing = ['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName);
  if (event.key === '/' && !editing && !document.querySelector('dialog[open]')) { event.preventDefault(); $('question').focus(); $('question').select(); }
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !document.querySelector('dialog[open]')) { event.preventDefault(); if (!running) $('ask-form').requestSubmit(); }
});
new ResizeObserver(() => { if (chartData) drawChart(); }).observe(document.querySelector('.chart-wrap'));
(async () => {
  try {
    config = await api('/api/config'); $('question').value = config.hero; $('hero').dataset.question = config.hero;
    document.dispatchEvent(new CustomEvent('p7:configuration', {detail:config}));
    const captions = ['Torque drift', 'Suspect units', 'Compare shifts', 'Since Monday'];
    config.presets.slice(1).forEach((question, index) => {
      const button = node('button', captions[index] || 'Question ' + (index + 2), 'preset'); button.type = 'button'; button.dataset.question = question; button.title = question;
      button.onclick = () => {
        if (index === 0 || index === 2) { $('chart-type').value = index === 0 ? 'angle' : 'fpy'; drawChart(); }
        selectPreset(question); investigate(question);
      }; $('presets').append(button);
    });
    $('replay').disabled = !config.replay_available;
    $('replay').title = config.replay_available ? 'Replay the accepted real run with recorded timing' : 'Unavailable until a real investigation passes acceptance';
    $('replay-status').textContent = $('replay').title;
    $('manual-time').textContent = number(config.value.manual_investigation_minutes, 0) + ' min';
    $('mobile-link').href = $('qr-link').href = config.public_url + '/m';
    poll(); chartData = await api('/api/charts'); drawChart();
  } catch (error) { setStatus('Connection problem: ' + error.message, true); toast(error.message); }
})();
