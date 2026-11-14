# Baseline before Inside the Line

Accessed 2026-11-14 UTC. Actual project: `/home/gb300/plant7-investigator`. No repository AGENTS.md exists; `/home/gb300/AGENTS.md` applies. The unrelated Fury showcase remains paused and untouched.

Rollback commit: `298a2f7`. Branch: `upgrade/inside-the-line-20261114`. User modification preserved: `logs/build.log`. Private recovery bundle and patch: `/home/gb300/plant7-upgrade-checkpoints/pre-inside-line.bundle` and `pre-inside-line.patch`. These contain tracked source history and the existing log diff, not .env, weights or recordings. No credentials were inspected.

Read README, architecture, model manifest, start/stop/health/benchmark/manage/ingest/accept scripts, current UI and tests before editing. Existing 27 tests pass with `.venv/bin/python -m pytest -q`. Direct pytest entrypoint fails import discovery; use python -m.

App PID 3117687 owned by this project, port 8097 on existing LAN binding. Proxy PID 2867328, ports 8001 through 8005 and challenger 8013 loopback. Four vLLM project containers resident. Model IDs and configured limits are in config/models.json. No serving flags or model weights changed. Vision is absent, not replaced with fabricated output. Existing clips are 960 by 540 procedural markers at 6 fps, 30 seconds each. No usable pixel based vision acceptance exists.

Endpoints preserved: /api/investigate (POST SSE), /api/config, /api/health, /api/telemetry, /api/charts, /api/units, /api/automotive/context, /api/automotive/unit/{id}, /api/evidence/{run}/{id}, /api/report/{run}, /api/report/{run}.{format}, /api/loadtest. Source data: 33600 units, read only DuckDB with sqlglot AST/function/table allowlists, 5 second timeout and 1000 row cap.

Screenshot: docs/captures/baseline.png. Baseline investigation captured in runs, timing appended below after completion. No cache cleanup, OS, driver, network, other project or tailnet changes.

Health at inspection:

```json
{
  "app": true,
  "ready": false,
  "models_ready": false,
  "models": [
    {
      "role": "brain",
      "model": "nvidia/Qwen3.8-Flash-Next-NVFP4",
      "port": 8001,
      "healthy": true,
      "tokens_per_second": 0.0
    },
    {
      "role": "vision",
      "model": "nvidia/Cosmos-Reason2-8B",
      "port": 8002,
      "healthy": false,
      "tokens_per_second": null,
      "error": "Server disconnected without sending a response."
    },
    {
      "role": "worker",
      "model": "nvidia/Qwen3.8-27B-NVFP4",
      "port": 8003,
      "healthy": true,
      "tokens_per_second": 0.0
    },
    {
      "role": "embed",
      "model": "Qwen/Qwen3-Embedding-0.6B",
      "port": 8004,
      "healthy": true,
      "tokens_per_second": 0.0
    },
    {
      "role": "rerank",
      "model": "Qwen/Qwen3-Reranker-0.6B",
      "port": 8005,
      "healthy": true,
      "tokens_per_second": 0.0
    }
  ],
  "database": true,
  "documents_index": true,
  "video_index": false,
  "golden_run": false
}
```

Device / host at inspection:

```
name, memory.used [MiB], memory.total [MiB]
NVIDIA GB300, 202825 MiB, 256703 MiB
               total        used        free      shared  buff/cache   available
Mem:           743Gi       275Gi       201Gi       1.1Gi       308Gi       468Gi
Swap:             0B          0B          0B
```

Baseline hero run `1ce909d13d584805b368c50310cbc5d0`: first evidence 2.204 seconds; ended after 58.765 seconds with answer audit rejection/tool round limit. This is not a successful investigation and was not selected as replay. Its actual trace remains in runs/. This observed issue motivates the bounded presentation workflow and stricter causal wording.
