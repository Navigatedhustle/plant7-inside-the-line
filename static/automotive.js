'use strict';

// Direct MES exploration is separate from the agent's cited investigation and acceptance.
(() => {
  let context = null, requestVersion = 0, unitVersion = 0, sequenceTimer;
  let currentView = 'trace';
  const scopeText = scope => dateLabel(scope.date) + ' · ' + (scope.shift ? 'Shift ' + scope.shift : 'All shifts') + (scope.tool_id ? ' · ' + scope.tool_id : '');

  async function loadContext(scope) {
    const version = ++requestVersion;
    context = null;
    $('open-workcell').disabled = $('engineering-header').disabled = $('vehicle-map').disabled = true;
    $('joint-exceptions').textContent = 'Reading traceability';
    const params = new URLSearchParams({date:scope.date});
    if (scope.shift) params.set('shift', scope.shift);
    if (scope.tool_id) params.set('tool_id', scope.tool_id);
    try {
      const result = await api('/api/automotive/context?' + params);
      if (version !== requestVersion) return;
      context = result;
      $('joint-spec').textContent = number(result.summary.spec_nm, 0) + ' Nm';
      $('joint-pattern').textContent = result.required_sequence.length ? result.required_sequence.join(' → ') : 'See controlled WI';
      const count = result.summary.recorded_exception_units;
      $('joint-exceptions').textContent = number(count, 0) + ' units outside recorded limits';
      $('open-workcell').disabled = $('engineering-header').disabled = $('vehicle-map').disabled = false;
    } catch (error) {
      if (version !== requestVersion) return;
      $('joint-spec').textContent = $('joint-pattern').textContent = '—';
      $('joint-exceptions').textContent = 'Traceability unavailable';
      $('open-workcell').title = error.message;
    }
  }

  function metric(value, label, caption) {
    const box = node('div', '', 'engineering-metric');
    box.append(node('strong', number(value, 0)), node('span', label));
    if (caption) box.append(node('small', caption));
    return box;
  }
  function queryDetails(queries) {
    const detail = node('details', '', 'engineering-queries');
    detail.append(node('summary', 'Inspect the read-only source queries'));
    for (const sql of queries) detail.append(node('pre', sql, 'detail-sql'));
    return detail;
  }
  function unitTable(rows, columns) {
    const table = resultTable(rows, columns);
    [...table.querySelectorAll('tbody tr')].forEach((tr, index) => {
      const button = node('button', rows[index].unit_id, 'unit-open');
      button.onclick = () => openUnit(rows[index].unit_id);
      tr.firstElementChild.replaceChildren(button);
    });
    return table;
  }
  function openWorkflow() {
    if (!context) return;
    $('engineering-scope').textContent = 'LINE 3 / STATION 40 / ' + scopeText(context.scope);
    renderWorkflow(currentView);
    $('engineering-dialog').showModal();
  }
  function renderWorkflow(view) {
    clearInterval(sequenceTimer); currentView = view;
    const content = $('engineering-content'); content.replaceChildren();
    for (const button of document.querySelectorAll('[data-engineering-view]')) {
      const active = button.dataset.engineeringView === view;
      button.classList.toggle('active', active); button.setAttribute('aria-selected', String(active));
      if (active) content.setAttribute('aria-labelledby', button.id);
    }
    if (view === 'trace') renderTraceability(content);
    else if (view === 'process') renderProcess(content);
    else renderDeployment(content);
  }
  function renderTraceability(content) {
    const summary = context.summary;
    const lead = node('div', '', 'engineering-lead');
    const illustration = node('img'); illustration.src = '/static/vehicle-body.svg'; illustration.alt = 'Illustrative generic body and Station 40 fixture bracket';
    const copy = node('div'); copy.append(node('span', 'BODY ASSEMBLY / FIXTURE FASTENING', 'label'),
      node('h3', 'Locate the joint. Trace the bodies.'),
      node('p', 'This view joins the selected production scope to the recorded bolt results. Select a serial to inspect its tool, four fastening results, station history and defect disposition.'),
      node('small', 'Illustrative geometry. The numbers come from synthetic MES records. This is not an AI finding.'));
    lead.append(illustration, copy); content.append(lead);
    const metrics = node('div', '', 'engineering-metrics');
    metrics.append(metric(summary.units_built, 'Bodies in scope'),
      metric(summary.first_pass_rejects, 'First pass rejects', 'All recorded rejection causes'),
      metric(summary.recorded_exception_units, 'Recorded joint exceptions', 'Distinct units, not bolt count'),
      metric(summary.shipped_exception_units, 'Exception units shipped', number(summary.held_exception_units, 0) + ' exception units held'));
    content.append(metrics);
    const header = node('div', '', 'engineering-subhead');
    header.append(node('h3', 'Which serials need a Quality review?'), node('span', scopeText(context.scope), 'meta'));
    content.append(header);
    content.append(node('p', 'The list contains units outside recorded torque or angle limits in this scope. It is not the complete containment population: calibration exposure and the last verified good check need separate review.', 'engineering-notice'));
    if (context.exceptions.length) {
      const wrap = node('div', '', 'engineering-table-wrap');
      wrap.append(unitTable(context.exceptions, ['unit_id','tool_id','status','outside_limit_bolts','min_nm','max_nm','min_angle','max_angle']));
      content.append(wrap, node('p', number(context.exceptions.length, 0) + ' shown / ' + number(summary.recorded_exception_units, 0) + ' recorded exception units. Display limit ' + context.exceptions_display_limit + '. Source: read-only synthetic MES.', 'detail-meta'));
    } else content.append(node('p', 'No recorded torque or angle exceptions were returned for this scope. This does not establish physical joint condition.', 'engineering-notice'));
    const next = node('button', 'Check the process requirement ↗', 'engineering-action');
    next.onclick = () => renderWorkflow('process'); content.append(next, queryDetails(context.queries));
  }

  // The reference diagram teaches the WI sequence; it is never presented as video observation.
  function jointGraphic(torque = [], sequence = [], onSelect) {
    const svg = svgNode('svg', {viewBox:'0 0 320 250',role:'img','aria-label':'Illustrative four bolt fixture bracket; positions are not engineering CAD'});
    svg.append(svgNode('path', {d:'M54 35H266V215H54Z',fill:'#FFFFFF',stroke:'#000000','stroke-width':1.5}),
      svgNode('path', {d:'M54 35L75 18H287V198L266 215M266 35L287 18',fill:'none',stroke:'#8795B5','stroke-width':1.2}));
    const positions = {1:[89,72],2:[231,72],3:[231,178],4:[89,178]};
    if (sequence.length === 4) svg.append(svgNode('polyline', {
      points:sequence.map(bolt => positions[bolt]?.join(',')).filter(Boolean).join(' '),
      fill:'none',stroke:'#004BDF','stroke-width':1.6,'stroke-dasharray':'5 5'}));
    for (const [key, position] of Object.entries(positions)) {
      const bolt = Number(key), result = torque.find(row => row.bolt === bolt), failed = result && !result.passed;
      const group = svgNode('g', {'data-bolt':bolt,class:'joint-bolt' + (failed?' outside-limit':''),
        tabindex:onSelect?0:-1,role:onSelect?'button':'group',
        'aria-label':'Bolt ' + bolt + (result?' · '+result.actual_nm+' Nm · '+result.angle_deg+' degrees · '+(result.passed?'within recorded limits':'outside recorded limits'):' · required position')});
      group.append(svgNode('circle', {cx:position[0],cy:position[1],r:22,fill:failed?'#004BDF':'#FFFFFF',stroke:'#004BDF','stroke-width':2}),
        svgNode('text', {x:position[0],y:position[1]+5,'text-anchor':'middle','font-size':17,fill:failed?'#FFFFFF':'#004BDF','font-weight':700},bolt));
      if (result) group.append(svgNode('text', {x:position[0],y:position[1]+(bolt>=3?57:40),'text-anchor':'middle','font-size':11,fill:'#000000'},fixed(result.angle_deg)+'°'));
      if (onSelect) {
        group.onclick = () => onSelect(result, group);
        group.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); group.onclick(); } };
      }
      svg.append(group);
    }
    return svg;
  }
  function renderProcess(content) {
    const lead = node('div', '', 'process-lead');
    const reference = node('div', '', 'process-reference');
    const svg = jointGraphic([], context.required_sequence); reference.append(svg);
    reference.append(node('span', 'REFERENCE GEOMETRY · REQUIRED SEQUENCE', 'eyebrow'));
    const copy = node('div', '', 'process-copy');
    copy.append(node('span', 'WI-L3-S40 / STEP 6', 'label'), node('h3', 'Required by the process.\nCheck against the evidence.'),
      node('p', context.sequence_instruction, 'instruction-quote'),
      node('p', 'This diagram shows the controlled instruction. It does not show an observed operator sequence. Compare the requirement with actual timestamped video before concluding that a step was skipped.', 'engineering-notice'));
    const sequenceStatus = node('p', 'Required sequence: ' + context.required_sequence.join(' → '), 'sequence-status');
    const play = node('button', 'Walk through step 6 ↗', 'engineering-action');
    play.disabled = context.required_sequence.length !== 4;
    play.onclick = () => {
      clearInterval(sequenceTimer); let index = 0;
      const step = () => {
        for (const marker of svg.querySelectorAll('[data-bolt]')) marker.classList.toggle('sequence-active', Number(marker.dataset.bolt) === context.required_sequence[index]);
        sequenceStatus.textContent = 'WI reference · position ' + (index+1) + ' of ' + context.required_sequence.length + ' · bolt ' + context.required_sequence[index];
        index++;
        if (index >= context.required_sequence.length) clearInterval(sequenceTimer);
      };
      step(); sequenceTimer = setInterval(step, 900);
    };
    copy.append(play, sequenceStatus); lead.append(reference, copy); content.append(lead);
    const sources = node('div', '', 'process-sources');
    for (const record of context.documents) {
      const detail = node('details', '', 'detail-document');
      detail.append(node('summary', record.id), highlightedPassage(record.text)); sources.append(detail);
    }
    content.append(sources, node('h3', 'What does maintenance actually record?'));
    const maintenance = node('div', '', 'engineering-table-wrap');
    maintenance.append(resultTable(context.maintenance, ['timestamp','asset_id','action','note'])); content.append(maintenance);
    content.append(node('p', 'Source: data/maintenance_log.csv. Missing reference paperwork is not proof that a check was never performed. Quality must establish the applicable containment window.', 'engineering-notice'));
  }
  function renderDeployment(content) {
    const header = node('div', '', 'deployment-intro');
    header.append(node('span', 'DEPLOYMENT PATTERN / NOT LIVE PRODUCTION CONNECTORS', 'label'),
      node('h3', 'Connect the systems.\nKeep the investigation local.'),
      node('p', 'Plant 7 demonstrates the handoffs with local synthetic records and files. Production MES, tool-controller, video and QMS integrations are not configured.'));
    content.append(header);
    const flow = node('div', '', 'deployment-flow');
    for (const [source, adapter, output] of [
      ['MES + fastening controller','Read-only query adapter','Unit serial → tool → individual bolt results'],
      ['Work instructions + PFMEA','Local retrieval + full document review','Process requirement → cited passage'],
      ['Station camera / video archive','Local MP4 ingest + vision endpoint','Visible sequence → timestamped observation'],
      ['Quality review workflow','Evidence-linked proposed 8D','Containment proposal → human disposition']
    ]) {
      const row = node('div', '', 'deployment-row');
      row.append(node('strong', source), node('span', adapter), node('span', '↗', 'deployment-arrow'), node('p', output)); flow.append(row);
    }
    content.append(flow);
    const boundary = node('div', '', 'engineering-boundary');
    boundary.append(node('span', 'THE HUMAN DECISION STAYS EXPLICIT', 'label'),
      node('p', 'The demo does not place holds, change tool programs, approve a release or write into a production system. Proposed containment needs Quality review. An 8D remains unavailable until the required investigation evidence is complete.'));
    content.append(boundary);
    const action = node('button', 'See the local model stack ↗', 'engineering-action');
    action.onclick = () => { $('engineering-dialog').close(); $('why-header').click(); }; content.append(action);
  }

  async function openUnit(unitId) {
    const version = ++unitVersion;
    $('passport-title').textContent = unitId;
    $('passport-content').replaceChildren(node('p', 'Reading the unit and its fastening trace…', 'meta'));
    if (!$('passport-dialog').open) $('passport-dialog').showModal();
    try {
      const passport = await api('/api/automotive/unit/' + encodeURIComponent(unitId));
      if (version !== unitVersion) return;
      renderPassport(passport);
    } catch (error) { if (version === unitVersion) $('passport-content').replaceChildren(node('p', error.message, 'engineering-notice')); }
  }
  function renderPassport(passport) {
    const box = $('passport-content'); box.replaceChildren();
    const unit = passport.unit, first = passport.torque[0];
    const identity = node('div', '', 'passport-identity');
    for (const [label, value] of [['Body / production','Generic SUV · '+dateLabel(unit.production_date)+' · Shift '+unit.shift],
      ['Tool',first?.tool_id || 'No recorded tool'],['Supplier lot',unit.supplier_lot],['Shipping record',unit.status],
      ['First pass record',unit.first_pass?'Pass':'Reject'],['Shipped at',unit.shipped_at?.replace('T',' ') || 'Not recorded']]) {
      const field = node('div'); field.append(node('span',label),node('strong',value)); identity.append(field);
    }
    box.append(node('p', 'SYNTHETIC UNIT SERIAL / NOT A PRODUCTION VIN', 'eyebrow'), identity);
    const joint = node('div', '', 'passport-joint'), detail = node('div', '', 'passport-bolt-detail');
    const showBolt = (row, marker) => {
      if (!row) return;
      for (const element of graphic.querySelectorAll('[data-bolt]')) element.classList.toggle('selected-bolt', element === marker);
      detail.replaceChildren(node('span','STATION 40 / BOLT '+row.bolt,'label'),
        node('h3',row.passed?'Inside recorded limits.':'Outside recorded limits.'),
        node('p','Torque '+fixed(row.actual_nm,3)+' Nm · allowed '+number(row.lower_nm)+'–'+number(row.upper_nm)+' Nm','bolt-reading'),
        node('p','Angle '+fixed(row.angle_deg,3)+'° · allowed '+number(row.angle_lower_deg)+'–'+number(row.angle_upper_deg)+'°','bolt-reading'),
        node('p',row.timestamp.replace('T',' ')+' · '+row.tool_id,'detail-meta'),
        node('p',passport.disposition_notice,'engineering-notice'));
    };
    const graphic = jointGraphic(passport.torque, [], showBolt);
    const visual = node('div', '', 'passport-bracket'); visual.append(graphic, node('span','Illustrative bolt locations. Filled blue = outside recorded limits.','meta'));
    joint.append(visual, detail); box.append(joint);
    if (first) showBolt(first, graphic.querySelector('[data-bolt="'+first.bolt+'"]'));
    box.append(node('h3','The fastening record'));
    const wrap = node('div', '', 'engineering-table-wrap');
    wrap.append(resultTable(passport.torque, ['bolt','tool_id','spec_nm','actual_nm','angle_deg','passed'])); box.append(wrap);
    box.append(node('h3','The route through the line'));
    const route = node('div', '', 'station-route');
    for (const event of passport.route) {
      const step = node('div','',event.passed?'':'route-flag');
      step.append(node('span','STATION'),node('strong',event.station),node('small',event.passed?'Recorded pass':'Recorded reject')); route.append(step);
    }
    box.append(route, node('h3','Recorded defect disposition'));
    if (passport.defects.length) {
      const defects = node('div', '', 'engineering-table-wrap');
      defects.append(resultTable(passport.defects,['station','code','disposition','timestamp'])); box.append(defects);
    } else box.append(node('p','No defect record was returned for this unit.','detail-meta'));
    box.append(node('p','Station passes and shipping status do not constitute a Quality release. Source: read-only synthetic MES.','engineering-notice'),queryDetails(passport.queries));
  }

  document.addEventListener('p7:selection', event => loadContext(event.detail));
  $('open-workcell').onclick = $('engineering-header').onclick = $('vehicle-map').onclick = openWorkflow;
  $('close-engineering').onclick = () => $('engineering-dialog').close();
  $('close-passport').onclick = () => $('passport-dialog').close();
  $('engineering-dialog').addEventListener('close', () => clearInterval(sequenceTimer));
  const tabs = [...document.querySelectorAll('[data-engineering-view]')];
  tabs.forEach((button,index) => {
    button.id = 'engineering-tab-' + button.dataset.engineeringView;
    button.onclick = () => renderWorkflow(button.dataset.engineeringView);
    button.onkeydown = event => {
      if (!['ArrowLeft','ArrowRight'].includes(event.key)) return;
      event.preventDefault(); const target = tabs[(index+(event.key==='ArrowRight'?1:tabs.length-1))%tabs.length]; target.click(); target.focus();
    };
  });
  window.Automotive = {openUnit, openWorkflow};
  if (typeof selectedPoint !== 'undefined' && selectedPoint) loadContext({date:selectedPoint.row.production_date,
    shift:selectedPoint.kind==='fpy'?selectedPoint.row.shift:null, tool_id:selectedPoint.kind==='fpy'?null:selectedPoint.row.tool_id});
})();
