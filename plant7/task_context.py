"""Public task intent and engineering purpose, not private model reasoning."""


def query_task(sql):
    text = ' '.join(sql.lower().split())
    grouping = text.split('group by', 1)[1].split('order by', 1)[0] if 'group by' in text else ''
    if 'supplier_lot' in grouping and 'unit_id' not in grouping:
        return {'task': 'Compare supplier lots and production scope',
                'value': 'Test whether the lot change tracks the loss across the relevant bodies and lines.'}
    if 'downtime' in text:
        return {'task': 'Check stoppages against the incident window',
                'value': 'Keep an unrelated conveyor event from driving the Line 3 containment decision.'}
    if 'first_pass_yield' in text or ('first_pass' in text and 'torque_results' not in text
                                    and any(name in text for name in ('count(', 'sum(', 'avg('))):
        return {'task': 'Measure yield and rejection counts',
                'value': 'Establish the size and location of the loss before investigating a cause.'}
    if 'torque_results' in text:
        return {'task': 'Link tool and bolt results to body serials',
                'value': 'Separate bolt-level exceptions from distinct affected units and their shipping records.'}
    if 'defects' in text:
        return {'task': 'Separate the recorded rejection causes',
                'value': 'Avoid treating every first-pass reject as the same fastening problem.'}
    if 'station_events' in text:
        return {'task': 'Inspect the unit route through the line',
                'value': 'Locate the recorded reject without mistaking a later station pass for Quality release.'}
    return {'task': 'Define the unit cohort and time window',
            'value': 'Give Quality a traceable population to review without guessing which bodies belong in scope.'}


def tool_task(name, arguments):
    if name == 'query_mes':
        return query_task(arguments.get('sql', ''))
    return {
        'search_docs': {'task': 'Find the controlled process evidence',
                        'value': 'Ground the investigation in the WI, PFMEA and maintenance records.'},
        'search_video': {'task': 'Check visible fastening sequence',
                         'value': 'Compare observed bolt order with the required process; a camera cannot establish preload.'},
        'long_context_review': {'task': 'Cross-check the complete process documents',
                                'value': 'Check qualifications and reaction requirements that an isolated passage could omit.'},
        'draft_8d': {'task': 'Prepare the proposed Quality handoff',
                     'value': 'Carry findings, open checks and evidence links into a reviewable 8D proposal.'}
    }.get(name, {'task': 'Inspect the requested evidence', 'value': 'Keep conclusions tied to inspectable records.'})


def next_check(evidence):
    returned = sum('error' not in item['result'] for item in evidence.values())
    return {'task': 'Choose the next evidence check' if evidence else 'Plan the checks for this question',
            'value': 'Relate the production, process and visual evidence before proposing a containment scope.',
            'basis': f'{returned} successful tool responses available; this is task intent, not a verified conclusion.'}


AUDIT_TASK = {'task': 'Check claims before proposing containment',
              'value': 'Challenge unsupported counts, causal claims and citations before an engineer uses the answer.'}
