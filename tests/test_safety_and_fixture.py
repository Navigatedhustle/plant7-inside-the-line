"""Behavioral checks for the SQL trust boundary and the planted fixture."""
import asyncio
import pytest
from sqlglot.errors import ParseError
from plant7.mes import query_mes, validate_sql
from plant7.retrieval import long_context_documents


@pytest.mark.parametrize('sql', [
    'DELETE FROM units', 'SELECT 1; DELETE FROM units', 'PRAGMA database_list',
    "SELECT * FROM read_csv_auto('/etc/passwd')", "SELECT read_text('/etc/passwd')",
    "SELECT * FROM glob('/home/*')", "SELECT getenv('HF_TOKEN')", 'SELECT * INTO x FROM units',
    'SELECT * FROM information_schema.tables', 'SELECT * FROM other.units',
    "SELECT repeat('x',1000000000)", 'WITH x AS (SELECT 1) SELECT * FROM x',
])
def test_reject_writes_external_io_and_unbounded_functions(sql):
    with pytest.raises((ValueError, ParseError)):
        validate_sql(sql)


def test_incident_is_four_points_and_local_to_one_shift():
    result = query_mes("SELECT shift,fpy_pct FROM first_pass_yield WHERE line=3 AND production_date=DATE '2026-11-10' ORDER BY shift")
    assert [row['fpy_pct'] for row in result['rows']] == [96.0, 92.0, 96.0]
    others = query_mes("SELECT line,fpy_pct FROM first_pass_yield WHERE line IN (1,2,4) AND shift=2 AND production_date=DATE '2026-11-10'")
    assert all(row['fpy_pct'] == 96 for row in others['rows'])


def test_containment_query_finds_shipped_units_without_claiming_defect():
    result = query_mes("SELECT count(*) AS n FROM units u JOIN torque_results t USING(unit_id) WHERE t.line=3 AND t.tool_id='T40-B' AND u.status='shipped' AND u.production_date=DATE '2026-11-10'")
    assert result['rows'][0]['n'] > 0


def test_long_context_rejects_arbitrary_file_reads():
    with pytest.raises(ValueError):
        long_context_documents(['../../.env'])
    docs = long_context_documents(['docs/work_instructions/WI-L3-S40.md'])
    assert 'STAR PATTERN' in docs[0]['text']


def test_angle_change_occurs_after_recorded_tool_return():
    result = query_mes("SELECT round(avg(angle_deg),2) AS angle FROM torque_results WHERE line=3 AND tool_id='T40-B' AND timestamp>=CAST('2026-11-09 06:00:00' AS TIMESTAMP) AND timestamp<CAST('2026-11-09 09:15:00' AS TIMESTAMP)")
    assert result['rows'][0]['angle'] < 92
    result = query_mes("SELECT round(avg(angle_deg),2) AS angle FROM torque_results WHERE line=3 AND tool_id='T40-B' AND timestamp>=CAST('2026-11-09 11:00:00' AS TIMESTAMP) AND timestamp<CAST('2026-11-09 12:00:00' AS TIMESTAMP)")
    assert result['rows'][0]['angle'] > 96


def test_tool_ids_identify_one_line_and_torque_flags_match_unit_fpy():
    result = query_mes('SELECT count(*) AS n FROM (SELECT tool_id FROM torque_results GROUP BY tool_id HAVING count(DISTINCT line)>1) AS x')
    assert result['rows'][0]['n'] == 0
    result = query_mes('SELECT count(*) AS n FROM torque_results t JOIN units u USING(unit_id) WHERE NOT t.passed AND u.first_pass')
    assert result['rows'][0]['n'] == 0


def test_fixture_has_no_future_shipments_at_scenario_snapshot():
    result = query_mes("SELECT count(*) AS n FROM units WHERE status='shipped' AND shipped_at>CAST('2026-11-13 18:00:00' AS TIMESTAMP)")
    assert result['rows'][0]['n'] == 0


@pytest.mark.parametrize('answer', ['I will check the records later.', 'The tool failed [E999].'])
def test_model_cannot_approve_missing_or_invented_citations(monkeypatch, answer):
    import json
    from plant7 import agent
    async def response(*args, **kwargs):
        return {'content': json.dumps({'approved': True, 'answer': answer, 'issues': []})}, {}
    monkeypatch.setattr(agent, 'complete', response)
    checked, _ = asyncio.run(agent.verify_answer('What happened?', answer,
        {'E1': {'tool': 'query_mes', 'result': {'rows': [{'count': 8}]}}}))
    assert checked['approved'] is False


def test_partial_run_cannot_generate_or_export_a_report(monkeypatch):
    from fastapi import HTTPException
    from plant7 import app as backend
    monkeypatch.setattr(backend, 'read_run', lambda _: {'events': [
        {'type': 'answer', 'text': 'Incomplete [E1]', 'complete_sources': False}]})
    for operation in (backend.report('f' * 32), backend.export_report('f' * 32, 'pdf')):
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation)
        assert error.value.status_code == 409


def test_chart_drilldowns_match_shift_and_daily_tool_grain():
    from plant7.app import units
    shift = asyncio.run(units('2026-11-10', shift=2))
    tool = asyncio.run(units('2026-11-10', tool_id='T40-B'))
    assert len(shift['rows']) == 200
    assert len(tool['rows']) == 300
    assert len({row['unit_id'] for row in tool['rows']}) == 300
    assert not tool['truncated']


@pytest.mark.parametrize('options', [{'date':'not-a-date'}, {'date':'2026-11-10','shift':4},
    {'date':'2026-11-10','tool_id':"T40-B' OR 1=1 --"}])
def test_drilldown_rejects_invalid_scope(options):
    from fastapi import HTTPException
    from plant7.app import units
    with pytest.raises(HTTPException) as error:
        asyncio.run(units(**options))
    assert error.value.status_code == 400


def test_automotive_traceability_counts_distinct_units_not_bolts():
    from plant7.automotive import context
    view = context('2026-11-10', shift=2)
    summary = view['summary']
    assert summary['units_built'] == 200
    assert summary['first_pass_rejects'] == 16
    assert summary['recorded_exception_units'] == summary['angle_exception_units'] == 8
    assert summary['torque_exception_units'] == 0
    assert summary['shipped_exception_units'] == 5 and summary['held_exception_units'] == 3
    assert len(view['exceptions']) == 8
    assert all(row['outside_limit_bolts'] == 4 for row in view['exceptions'])
    assert view['required_sequence'] == [1, 3, 2, 4]
    assert summary['spec_nm'] == 40 and summary['lower_nm'] == 38 and summary['upper_nm'] == 42


def test_automotive_scope_and_unit_passport_preserve_recorded_evidence():
    from plant7.automotive import context, unit_passport
    assert context('2026-11-10', tool_id='T40-A')['summary']['recorded_exception_units'] == 0
    passport = unit_passport('P7-20261110-32-0041')
    assert passport['unit']['status'] == 'shipped'
    assert len(passport['torque']) == 4 and all(not row['passed'] for row in passport['torque'])
    assert len(passport['route']) == 9
    assert passport['defects'][0]['disposition'] == 'reference_check_pending'
    assert unit_passport('P7-20261110-32-9999') is None
    with pytest.raises(ValueError):
        unit_passport("P7-' OR 1=1 --")
