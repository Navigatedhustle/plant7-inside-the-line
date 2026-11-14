'use strict';

// Explain the public work and account only for returned server measurements.
// This is not a model thought trace, a cost estimator, or a time-saving claim.
(() => {
  const measurements = new Map();
  const sourceStates = new Map();
  let settings, telemetry, interval, startedAt, replay = false, active = false, reportProduced = false;
  let elapsed = null, outcome = 'Not measured. Run an investigation to measure this attempt.';

  function view(name) {
    const comparison = name === 'value';
    $('value-summary').hidden = !comparison; $('answer').hidden = comparison;
    for (const [id, selected] of [['show-value',comparison],['show-finding',!comparison]]) {
      $(id).classList.toggle('active', selected); $(id).setAttribute('aria-selected', String(selected));
    }
    if (comparison) {
      document.querySelector('.evidence-panel').classList.remove('focus-findings');
      $('focus-answer').setAttribute('aria-pressed','false'); $('focus-answer').textContent = '↗';
      $('focus-answer').title = 'Expand findings'; $('focus-answer').setAttribute('aria-label','Expand findings');
    }
  }
  function measuredElapsed(value) {
    elapsed = value;
    const text = number(value) + ' s';
    $('agent-time').textContent = text; $('comparison-ai-time').textContent = text;
  }
  function setOutcome(value, verdict) {
    outcome = value;
    $('agent-time-label').textContent = value; $('comparison-status').textContent = value;
    $('comparison-verdict').textContent = verdict;
  }
  function addMeasurement(measurement) {
    if (!measurement || !measurement.role || !Number.isFinite(measurement.at)) return;
    const key = measurement.role + ':' + measurement.at;
    measurements.set(key, measurement);
  }
  function knownTotal(rows, key) {
    const values = rows.map(row => row[key]).filter(value => Number.isFinite(value) && value >= 0);
    return values.length ? values.reduce((sum,value) => sum+value,0) : null;
  }
  function usage() {
    const rows = [...measurements.values()];
    return {input:knownTotal(rows,'prompt_tokens'), output:knownTotal(rows,'completion_tokens'),
      calls:rows.length || null, rows};
  }
  function renderUsage() {
    const total = usage();
    const compact = value => value === null ? '—' : new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:1}).format(value);
    $('run-input-tokens').textContent = compact(total.input);
    $('run-output-tokens').textContent = compact(total.output);
    $('run-model-calls').textContent = number(total.calls,0);
    $('token-scope').textContent = (replay ? 'Recorded usage. ' : 'Known server usage. ') +
      (total.calls ? 'Repeated context included; pooling and unreported calls excluded.' : 'Run to measure.');
    if (!$('tokens-dialog').open) return;
    const totals = $('token-totals'); totals.replaceChildren();
    for (const [label,value] of [['Known input tokens',total.input],['Known generated tokens',total.output],['Returned timing records',total.calls]]) {
      const box = node('div','','token-total'); box.append(node('span',label),node('strong',number(value,0))); totals.append(box);
    }
    const roles = [...new Set(total.rows.map(row => row.role))];
    const rows = roles.map(role => {
      const entries = total.rows.filter(row => row.role === role);
      return {model:shortModel(role), 'reported calls':entries.length,
        'known input tokens':knownTotal(entries,'prompt_tokens') ?? 'Unknown',
        'known generated tokens':knownTotal(entries,'completion_tokens') ?? 'Unknown'};
    });
    $('token-role-usage').replaceChildren(rows.length ? resultTable(rows,['model','reported calls','known input tokens','known generated tokens']) :
      node('p','No returned generative timing record is available in this view yet.','meta'));
    $('token-detail-scope').textContent = (replay?'These are recorded measurements from the replay. ':'') +
      'Only returned generative timing records are counted, once per model and timestamp. Prompt usage can include cached or repeated context and is counted on each request. Interrupted or unreported failed calls, embeddings and reranking are excluded. No hardware, power, staffing or operating-cost estimate is included.';
  }
  function hasEvidence(tool) {
    return [...sourceStates.values()].some(item => item.tool === tool && !item.result.error &&
      (tool !== 'search_video' || item.result.clips?.length) && (tool !== 'search_docs' || item.result.passages?.length));
  }
  function workState(source) {
    if (source === 'passport') return $('open-workcell')?.disabled ? ['Traceability not available','pending'] :
      ['Read-only unit passport available · separate from the AI conclusion',''];
    if (source === 'report') {
      if (reportProduced) return ['Proposed report returned · Quality review required',''];
      if ($('report').textContent.includes('Drafting')) return ['Draft generation in progress · review still required','pending'];
      return $('report').disabled ? ['Locked · required investigation evidence incomplete','pending'] :
        ['Draft action available · engineering and Quality review required',''];
    }
    if (source === 'scope') return ['Containment boundary and disposition still require Quality review','pending'];
    if (source === 'docs' && hasEvidence('long_context_review')) return ['Complete documents returned · inspect the cross-check',''];
    const tool = {data:'query_mes',docs:'search_docs',video:'search_video'}[source];
    if (hasEvidence(tool)) return ['Evidence returned in this attempt · inspect its citations',''];
    const attempted = [...sourceStates.values()].some(item => item.tool === tool);
    if (attempted) return ['Attempted · no usable evidence returned for this source','pending'];
    if (source === 'video' && telemetry?.models.some(model => model.role === 'vision' && !model.healthy)) return ['Unavailable · vision endpoint is down','pending'];
    return [active?'Waiting for this source check':'Not yet checked in this view','pending'];
  }
  function renderWork() {
    if (!settings) return;
    $('comparison-manual-time').textContent = number(settings.manual_investigation_minutes,0) + ' min';
    $('comparison-ai-time').textContent = elapsed === null ? 'Not measured' : number(elapsed) + ' s';
    $('comparison-status').textContent = outcome;
    $('value-target').textContent = 'Acceptance target: under ' + number(settings.acceptance_target_seconds,0) +
      ' seconds with the required evidence. This target is not a measured result. ' + settings.comparison_scope;
    const content = $('work-comparison'); content.replaceChildren();
    for (const stage of settings.manual_workflow || []) {
      const row = node('div','','work-row'), before = node('div','','work-before'), after = node('div','','work-after');
      const state = workState(stage.source);
      before.append(node('p',stage.before));
      after.append(node('p',stage.after),node('p',stage.decision,'decision'),node('span',state[0],'work-state '+state[1]));
      row.append(node('h3',stage.task),before,after); content.append(row);
    }
  }
  function configure(configuration) {
    settings = configuration.value;
    $('manual-time').textContent = number(settings.manual_investigation_minutes,0) + ' min';
    renderWork(); renderUsage();
  }
  function collectEvent(event) {
    if (event.type === 'model_done') addMeasurement(event.measurement);
    if (event.type === 'evidence') {
      sourceStates.set(event.evidence_id,{tool:event.tool,result:event.result});
      addMeasurement(event.result.measurement);
      for (const measurement of event.result.inference_measurements || []) addMeasurement(measurement);
      for (const clip of event.result.clips || []) addMeasurement(clip.live_measurement);
    }
    if (event.type === 'answer') view('result');
    if (event.type === 'answer_review' && !event.approved) setOutcome('Draft returned for correction. No reviewed result yet.','No validated time saving.');
    if (replay && Number.isFinite(event.elapsed_s)) measuredElapsed(event.elapsed_s);
    renderUsage(); if ($('work-dialog').open) renderWork();
  }

  document.addEventListener('p7:configuration', event => configure(event.detail));
  document.addEventListener('p7:telemetry', event => { telemetry = event.detail; if ($('work-dialog').open) renderWork(); });
  document.addEventListener('p7:run-start', event => {
    measurements.clear(); sourceStates.clear(); replay = event.detail.replay; active = true; reportProduced = false; startedAt = performance.now();
    clearInterval(interval); elapsed = null; view('value');
    setOutcome(replay?'Recorded attempt · measurements will follow the trace.':'Measuring the attempt · no accepted finding yet.','An elapsed time is not a validated time saving.');
    $('agent-time').textContent = replay?'Recorded run':'Measuring';
    if (!replay) interval = setInterval(() => measuredElapsed((performance.now()-startedAt)/1000),100);
    renderUsage(); renderWork();
  });
  document.addEventListener('p7:run-event', event => collectEvent(event.detail));
  document.addEventListener('p7:run-end', event => {
    const result = event.detail; active = false; clearInterval(interval); measuredElapsed(result.elapsed_s);
    const prefix = result.replay?'Recorded attempt · ':'';
    if (result.stopped) setOutcome(prefix+'Stopped attempt · not a completed investigation.','Not comparable to a completed manual case.');
    else if (result.failed) setOutcome(prefix+'Failed validation · no accepted finding.','Not comparable to a completed manual case.');
    else if (!result.complete_sources) setOutcome(prefix+'Incomplete evidence · open checks remain.','No validated time saving.');
    else setOutcome(prefix+'Sources returned · engineering review required.','Manual baseline is an assumption; time saving is not validated.');
    $('trace-context').textContent = result.failed ? 'Keep unsupported claims out of the Quality handoff. The returned sources remain available for inspection.' :
      'Use the linked evidence to review the scope and open checks. Quality owns containment and release.';
    renderWork(); renderUsage();
  });
  document.addEventListener('p7:report', event => { reportProduced = true; addMeasurement(event.detail.measurement); renderUsage(); if ($('work-dialog').open) renderWork(); });
  document.addEventListener('p7:show-result', () => view('result'));
  $('show-value').onclick = () => view('value'); $('show-finding').onclick = () => view('result');
  for (const id of ['show-value','show-finding']) $(id).onkeydown = event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); const other = id==='show-value'?'show-finding':'show-value'; $(other).click(); $(other).focus(); }
  };
  $('compare-work').onclick = () => { renderWork(); $('work-dialog').showModal(); };
  $('open-tokens').onclick = () => { $('tokens-dialog').showModal(); renderUsage(); };
  $('close-work').onclick = () => $('work-dialog').close(); $('close-tokens').onclick = () => $('tokens-dialog').close();
  $('work-run').onclick = () => { $('work-dialog').close(); $('hero').click(); };
  $('work-trace').onclick = () => { $('work-dialog').close(); window.Automotive?.openWorkflow(); };
  window.P7Value = {usageSnapshot:() => ({...usage(), replay, active, outcome})};
  if (typeof config !== 'undefined' && config) configure(config);
})();
