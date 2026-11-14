#!/usr/bin/env python3
"""Execute one shell command, recording the exact command, output, and status locally."""
import subprocess, sys, datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1]
command=sys.argv[1]
log=root/'logs/build.log'
with log.open('a') as f:
 f.write(f"\n[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] COMMAND {command}\n")
 f.flush()
 result=subprocess.run(['/bin/bash','-o','pipefail','-c',command],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 f.write(result.stdout)
 f.write(f"\nEXIT {result.returncode}\n")
print(result.stdout,end='')
sys.exit(result.returncode)
