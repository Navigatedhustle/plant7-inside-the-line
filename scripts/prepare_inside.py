#!/usr/bin/env python3
"""Prepare small local demo artifacts from checked in sources, without network or models."""
import shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_scenarios import build
if not (ROOT/'data/scenarios/manifest.json').exists():build()
for src,dest in [('static/inside/assembly.mp4','data/video/inside-line.mp4'),('static/inside/assembly.json','data/video/inside-line.json'),('static/inside/assembly-occluded.mp4','data/video/inside-line-occluded.mp4'),('docs/captures/replay-run.json','runs/inside-replay.json')]:
 if not (ROOT/dest).exists() and (ROOT/src).exists():
  (ROOT/dest).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/src,ROOT/dest)
print('Inside the Line local artifacts ready')
