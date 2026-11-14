"""Read-only automotive traceability views over the same synthetic MES evidence."""
import csv
import datetime
import re

from .mes import query_mes
from .settings import ROOT


def scope_where(date, shift=None, tool_id=None):
    """Validate scope before composing literals for the existing SELECT sandbox."""
    day = datetime.date.fromisoformat(date)
    if shift is not None and shift not in (1, 2, 3):
        raise ValueError('Choose shift 1, 2 or 3')
    if tool_id is not None and tool_id not in ('T40-A', 'T40-B'):
        raise ValueError('Choose a Line 3 Station 40 tool')
    clauses = [f"u.production_date=DATE '{day}'", 'u.line=3', 't.line=3', 't.station=40']
    if shift is not None:
        clauses.append(f'u.shift={shift}')
    if tool_id:
        clauses.append(f"t.tool_id='{tool_id}'")
    return ' AND '.join(clauses)


def process_documents():
    ids = ['docs/work_instructions/WI-L3-S40.md', 'docs/fmea/PFMEA-L3-S40.md']
    return [{'id': key, 'text': (ROOT / key).read_text()} for key in ids]


def maintenance_records(tool_id=None):
    with (ROOT / 'data/maintenance_log.csv').open() as source:
        return [row for row in csv.DictReader(source) if row['line'] == '3' and row['station'] == '40'
                and (not tool_id or row['asset_id'] == tool_id)]


def context(date, shift=None, tool_id=None):
    where = scope_where(date, shift, tool_id)
    joined = ' FROM units u JOIN torque_results t USING(unit_id) WHERE ' + where
    # DISTINCT unit IDs avoid counting the four bolt records as four vehicles.
    summary = query_mes('''SELECT COUNT(DISTINCT u.unit_id) AS units_built,
        COUNT(DISTINCT CASE WHEN NOT u.first_pass THEN u.unit_id END) AS first_pass_rejects,
        COUNT(DISTINCT CASE WHEN NOT t.passed THEN u.unit_id END) AS recorded_exception_units,
        COUNT(DISTINCT CASE WHEN t.angle_deg<t.angle_lower_deg OR t.angle_deg>t.angle_upper_deg THEN u.unit_id END) AS angle_exception_units,
        COUNT(DISTINCT CASE WHEN t.actual_nm<t.lower_nm OR t.actual_nm>t.upper_nm THEN u.unit_id END) AS torque_exception_units,
        COUNT(DISTINCT CASE WHEN NOT t.passed AND u.status='shipped' THEN u.unit_id END) AS shipped_exception_units,
        COUNT(DISTINCT CASE WHEN NOT t.passed AND u.status='held' THEN u.unit_id END) AS held_exception_units,
        MIN(t.spec_nm) AS spec_nm, MIN(t.lower_nm) AS lower_nm, MAX(t.upper_nm) AS upper_nm,
        MIN(t.angle_lower_deg) AS angle_lower_deg, MAX(t.angle_upper_deg) AS angle_upper_deg''' + joined)
    exceptions = query_mes('''SELECT u.unit_id,u.status,u.shift,u.first_pass,u.supplier_lot,t.tool_id,
        COUNT(*) AS outside_limit_bolts,ROUND(MIN(t.actual_nm),3) AS min_nm,
        ROUND(MAX(t.actual_nm),3) AS max_nm,ROUND(MIN(t.angle_deg),3) AS min_angle,
        ROUND(MAX(t.angle_deg),3) AS max_angle''' + joined + ''' AND NOT t.passed
        GROUP BY u.unit_id,u.status,u.shift,u.first_pass,u.supplier_lot,t.tool_id
        ORDER BY u.unit_id LIMIT 25''')
    documents = process_documents()
    instruction = next((line for line in documents[0]['text'].splitlines() if line.startswith('6. ')),
                       'Step 6 was not found in the controlled instruction. Review the source document.')
    sequence = [int(value) for value in re.findall(r'bolt\s+(\d+)', instruction)]
    return {'scope': {'date': date, 'shift': shift, 'tool_id': tool_id, 'line': 3, 'station': 40},
            'summary': summary['rows'][0], 'exceptions': exceptions['rows'],
            'exceptions_display_limit': 25, 'queries': [summary['sql'], exceptions['sql']],
            'documents': documents, 'required_sequence': sequence, 'sequence_instruction': instruction,
            'maintenance': maintenance_records(tool_id),
            'source': 'Read-only synthetic MES and controlled local process records. Not an AI finding.',
            'geometry': 'Illustrative generic body and fixture. Not engineering CAD.'}


def unit_passport(unit_id):
    if not re.fullmatch(r'P7-\d{8}-[1-4][1-3]-\d{4}', unit_id):
        raise ValueError('Invalid synthetic unit serial')
    unit = query_mes(f"SELECT * FROM units WHERE unit_id='{unit_id}' AND line=3")
    if not unit['rows']:
        return None
    torque = query_mes(f"SELECT * FROM torque_results WHERE unit_id='{unit_id}' AND line=3 AND station=40 ORDER BY bolt")
    route = query_mes(f"SELECT station,timestamp,cycle_seconds,passed FROM station_events WHERE unit_id='{unit_id}' AND line=3 ORDER BY station")
    defects = query_mes(f"SELECT station,code,disposition,timestamp FROM defects WHERE unit_id='{unit_id}' AND line=3 ORDER BY timestamp")
    return {'unit': unit['rows'][0], 'torque': torque['rows'], 'route': route['rows'],
            'defects': defects['rows'], 'queries': [result['sql'] for result in (unit, torque, route, defects)],
            'documents': process_documents(), 'source': 'Read-only synthetic MES. Unit serial, not a production VIN.',
            'disposition_notice': 'Recorded results and shipping status do not establish joint preload or Quality release.'}
