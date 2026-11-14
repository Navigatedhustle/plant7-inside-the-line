#!/usr/bin/env python3
"""Generate isolated counterfactual databases. Never mutate the original fixture."""
import json,sys
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=['no_anomaly','different_tool','missing_video','inconclusive_sequence','supplier_issue']

def build():
 out=ROOT/'data/scenarios';out.mkdir(exist_ok=True)
 for name in SCENARIOS:
  path=out/(name+'.duckdb')
  if path.exists():path.unlink()
  with duckdb.connect(str(path)) as c:
   c.execute("ATTACH ? AS source (READ_ONLY)",[str(ROOT/'data/mes.duckdb')])
   for table in ['units','station_events','torque_results','defects','first_pass_yield','downtime']:
    c.execute(f'CREATE TABLE {table} AS SELECT * FROM source.{table}')
   c.execute('DETACH source')
   if name=='no_anomaly':
    c.execute("UPDATE torque_results SET angle_deg=90,passed=true WHERE line=3")
    c.execute("UPDATE units SET first_pass=true WHERE unit_id IN (SELECT unit_id FROM defects WHERE code='JOINT_SEATING')")
    c.execute("DELETE FROM defects WHERE code='JOINT_SEATING'")
    c.execute("UPDATE first_pass_yield SET fpy_pct=96,first_pass_units=192 WHERE line=3 AND production_date=DATE '2026-11-10' AND shift=2")
   if name=='different_tool':
    c.execute("UPDATE torque_results SET tool_id=CASE WHEN tool_id='T40-B' THEN 'T40-A' ELSE 'T40-B' END WHERE line=3")
   if name=='supplier_issue':
    c.execute("UPDATE torque_results SET angle_deg=90,passed=true WHERE line=3")
    c.execute("UPDATE torque_results SET angle_deg=108,passed=false WHERE unit_id IN (SELECT unit_id FROM units WHERE supplier_lot='LOT-062' AND shift=2 AND unit_id LIKE '%0041')")
    c.execute("UPDATE units SET first_pass=true WHERE unit_id IN (SELECT unit_id FROM defects WHERE code='JOINT_SEATING')")
    c.execute("DELETE FROM defects WHERE code='JOINT_SEATING'")
    c.execute("INSERT INTO defects SELECT 'SUP-'||unit_id,unit_id,line,40,shift,built_at+INTERVAL 90 SECOND,'BRACKET_DIMENSION','inspection_pending' FROM units WHERE supplier_lot='LOT-062' AND shift=2 AND unit_id LIKE '%0041'")
    c.execute("UPDATE units SET first_pass=false WHERE unit_id IN (SELECT unit_id FROM defects WHERE code='BRACKET_DIMENSION')")
    c.execute("DELETE FROM first_pass_yield")
    c.execute('INSERT INTO first_pass_yield SELECT production_date,line,shift,count(*),count(*) FILTER(WHERE first_pass),100.0*avg(first_pass::INTEGER) FROM units GROUP BY production_date,line,shift')
  print(name,path.stat().st_size)
 (out/'manifest.json').write_text(json.dumps({'version':1,'source':'mes.duckdb','datasets':SCENARIOS,'method':'scripts/build_scenarios.py','synthetic':True},indent=2))
if __name__=='__main__':build()
