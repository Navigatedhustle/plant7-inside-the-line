"""Integration checks for source identity, derived scope and isolated demo actions."""
import asyncio,json,uuid
from pathlib import Path
import httpx
import pytest
from plant7 import inside_line as inside
from plant7.app import app
from plant7.mes import query_mes


def test_evidence_identity_timestamp_and_component_mapping():
 result=asyncio.run(inside.fastener('B3'))
 assert result['source_id']=='P7-20261110-32-0021-B3'
 assert result['unit_id']=='P7-20261110-32-0021'
 assert result['timestamps']==['2026-11-10T14:42:43Z']
 assert result['component_id']==inside.ENTITY_MAP['B3']['component_id']
 assert result['observed_fact']['bolt']==3


def test_cohort_counts_and_ids_are_one_complete_query_result():
 view=inside.snapshot('hero');rows=view['cohort']
 assert len(rows)==539==len({x['unit_id'] for x in rows})
 assert sum(view['counts'].values())==len(rows)
 assert view['exception_count']==sum(x['outside_limit_bolts']>0 for x in rows)==8
 assert all(x['tool_id']=='T40-B' for x in rows)
 assert all(x['joint_condition']=='insufficient_evidence' for x in rows)
 assert query_mes(view['queries']['cohort'])['truncated'] is False


def test_counterfactual_data_changes_tool_cohort_and_supplier_scope():
 normal=inside.snapshot('no_anomaly');other=inside.snapshot('different_tool');supplier=inside.snapshot('supplier_issue')
 assert normal['cohort']==[] and normal['exception_count']==0
 assert all(x['tool_id']=='T40-A' for x in other['cohort'])
 assert {x['line'] for x in supplier['cohort']}=={1,2,3,4}
 assert supplier['exception_count']==16
 assert 'broader lot genealogy unresolved' in supplier['scope']


def test_missing_video_is_missing_not_a_generated_observation():
 result=asyncio.run(inside.vision_evidence({'scenario':'missing_video'}))
 assert result['status']=='missing' and result['observation'] is None


def test_demo_approval_idempotence_and_read_only_source(monkeypatch,tmp_path):
 monkeypatch.setattr(inside,'RUNTIME',tmp_path)
 sid=uuid.uuid4().hex;rid=uuid.uuid4().hex
 inside.atomic(inside.session_path(sid),{'session_id':sid,'revision':0,'stage':{},'drafts':{},'holds':{}})
 data=inside.snapshot('hero');before=query_mes('SELECT count(*) AS n FROM units WHERE status=\'held\'')['rows']
 inside.JOBS[rid]={'run_id':rid,'session_id':sid,'status':'completed','mode':'live_local','data':data}
 async def scenario():
  draft=await inside.prepare(sid,inside.HoldDraft(run_id=rid),inside.TOKEN)
  assert draft['unit_ids']==[r['unit_id'] for r in data['cohort']]
  approval=inside.Approval(draft_id=draft['draft_id'],approved_by='Demo reviewer',confirmation='SIMULATE HOLD')
  a=await inside.confirm(sid,approval,inside.TOKEN);b=await inside.confirm(sid,approval,inside.TOKEN)
  assert a==b and len(inside.session(sid)['holds'])==539
  await inside.reset(sid,inside.TOKEN)
  assert inside.session(sid)['holds']=={}
 asyncio.run(scenario())
 assert query_mes('SELECT count(*) AS n FROM units WHERE status=\'held\'')['rows']==before
 inside.JOBS.pop(rid)


def test_mobile_cannot_control_or_bootstrap_presenter():
 async def scenario():
  transport=httpx.ASGITransport(app=app,client=('192.168.5.8',1234))
  async with httpx.AsyncClient(transport=transport,base_url='http://plant7') as c:
   r=await c.get('/api/stage/bootstrap');assert r.json()['presenter'] is False
   assert 'presenter_key' not in r.json()
   assert (await c.post('/api/stage/sessions')).status_code==403
   assert (await c.patch('/api/stage/sessions/'+uuid.uuid4().hex,json={'chapter':4})).status_code==403
   assert (await c.post('/api/demo-counter/start')).status_code==403
 asyncio.run(scenario())


def test_canceled_job_stays_canceled(monkeypatch,tmp_path):
 monkeypatch.setattr(inside,'save_job',lambda j:None)
 rid=uuid.uuid4().hex;inside.JOBS[rid]={'run_id':rid,'status':'queued','mode':'live_local','events':[],'_start':0}
 async def scenario():
  task=asyncio.create_task(asyncio.sleep(30));inside.TASKS[rid]=task
  result=await inside.cancel(rid,inside.TOKEN)
  assert result['status']=='canceled'
  assert not any(e['type']=='report_ready' for e in inside.JOBS[rid]['events'])
 asyncio.run(scenario());inside.JOBS.pop(rid);inside.TASKS.pop(rid)


def test_replay_does_not_call_a_model_or_count_live_usage(monkeypatch,tmp_path):
 # Use an actual captured trace if available; mechanically exercise the isolated branch.
 from plant7.clients import MEASUREMENTS
 path=inside.ROOT/'runs/inside-replay.json'
 if not path.exists():pytest.skip('Captured replay acceptance pending')
 before=len(MEASUREMENTS)
 async def forbidden(*args,**kwargs):raise AssertionError('Replay attempted model call')
 monkeypatch.setattr(inside,'complete',forbidden)
 async def scenario():
  transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1234))
  async with httpx.AsyncClient(transport=transport,base_url='http://plant7',headers={'X-Presenter-Key':inside.TOKEN}) as c:
   s=(await c.post('/api/stage/sessions')).json();r=await c.post('/api/stage/sessions/'+s['session_id']+'/jobs',json={'replay':True})
   assert r.status_code==200
   replay=(await c.get('/api/stage/jobs/'+r.json()['run_id'])).json()
   assert replay['mode']=='captured_replay' and replay['recorded_run_id']
   assert all(e['replay'] for e in replay['events'])
   assert all(e['run_id']==replay['run_id'] for e in replay['evidence'])
 asyncio.run(scenario());assert len(MEASUREMENTS)==before


def test_media_ingest_checks_decodable_pixels_and_blocks_outside_paths(tmp_path):
 from plant7.video import validate_media
 with pytest.raises(ValueError):validate_media('/etc/passwd')
 metadata=validate_media(inside.ROOT/'data/video/inside-line.mp4')
 assert metadata['width']==960 and metadata['fps']==10


def test_model_failure_has_no_accepted_answer(monkeypatch):
 async def broken(*a,**kw):raise RuntimeError('Injected endpoint unavailable')
 monkeypatch.setattr(inside,'complete',broken);monkeypatch.setattr(inside,'save_job',lambda j:None)
 import time
 job={'run_id':uuid.uuid4().hex,'scenario':'hero','status':'queued','mode':'live_local','events':[],'evidence':[],'_start':time.monotonic(),'question':'Check evidence'}
 asyncio.run(inside.execute(job))
 assert job['status']=='failed' and 'answer' not in job
 assert any(e['type']=='error' for e in job['events'])
 assert not any(e['type']=='report_ready' for e in job['events'])


def test_preserved_investigation_api_rejects_overflow_before_model_work(monkeypatch):
 from plant7 import app as backend
 monkeypatch.setattr(backend,'PENDING_LEGACY',24)
 async def scenario():
  transport=httpx.ASGITransport(app=app,client=('192.168.5.9',1234))
  async with httpx.AsyncClient(transport=transport,base_url='http://plant7') as c:
   response=await c.post('/api/investigate',json={'question':'Compare the tool evidence'})
   assert response.status_code==429
   assert backend.PENDING_LEGACY==24
 asyncio.run(scenario())
