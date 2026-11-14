#!/usr/bin/env python3
"""Restart only the exact project application process; inference remains resident."""
import json,os,signal,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.manage import start_app
p=ROOT/'runtime/app.json'
if p.exists():
 state=json.loads(p.read_text());proc=Path('/proc')/str(state['pid'])
 try:
  info=(proc/'stat').read_text().rsplit(')',1)[1].split()
  if info[19]==state['start_ticks'] and info[0]!='Z':
   if proc.stat().st_uid!=os.getuid() or (proc/'cwd').resolve()!=ROOT or b'plant7.app:app' not in (proc/'cmdline').read_bytes():raise RuntimeError('Ownership could not be verified')
   os.kill(state['pid'],signal.SIGTERM)
   for _ in range(80):
    try:
     if (proc/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':break
    except FileNotFoundError:break
    time.sleep(.25)
   else:raise RuntimeError('App did not stop gracefully')
 except FileNotFoundError:pass
 p.unlink()
start_app()
