# Plant 7: Inside the Line — quick start

This bundle contains the five-step synthetic investigation, browser scene, original evidence and a clearly labelled captured local run. It contains no passwords, browser sessions, private sharing settings or model weights. Review `docs/KNOWN_LIMITATIONS.md` and `docs/LICENSES_FOR_IP_REVIEW.md` before external distribution. Vision and camera accuracy are not accepted.

## Fastest handoff: recorded walkthrough

Use Linux with Python 3.12. Docker, a GPU and Node are unnecessary for this mode. Internet is needed once to install the pinned Python dependencies. A modern browser with WebGL is recommended; a functional 2D fallback is included.

```bash
sha256sum -c plant7-inside-the-line.tar.gz.sha256
tar -xzf plant7-inside-the-line.tar.gz
cd plant7-inside-the-line
./scripts/install.sh
./scripts/open_desktop.sh
```

The installer creates a virtual environment inside this folder and a launch entry in the application menu. You may also open `Plant 7.desktop`; some Linux desktops require marking a new launcher as trusted. Run the shell command if the desktop blocks it. Keep the folder at its installed location; if moved, rerun installation to recreate its environment and shortcut. Do not copy a virtual environment between machines.

Use the single blue button or the right arrow/space key through the story. The first step starts the investigation or the labelled recording. The next step plays the synthetic evidence clip. Continue to the exact unit scope, then the decision and token economics. The final button resets the story for the next audience. Source inspection, a unit passport and explicit simulated containment are optional. There is no credential-entry screen. Every browser receives an isolated demo session; refresh resumes it.

Recorded mode makes no inference requests. Its token counts and timings belong to the captured run, not the current machine. It cannot demonstrate live GPU throughput. No failure silently becomes a live success or an unlabelled replay.

## Live inference on another Fury

This pinned deployment targets the tested Linux ARM64 SM 10.3 Fury GPU stack with at least 240000 MiB GPU memory, Python 3.12, Docker access and the NVIDIA container runtime. Different Fury configurations need separate model/memory validation. Run the read-only preflight before a large transfer:

```bash
python3 scripts/doctor.py --pre-install
```

If the target already has a transferred Plant 7 folder containing `models/` and the matching `logs/download-*.json` checkpoint records, install using that folder:

```bash
./scripts/install.sh --mode live --model-source /path/to/plant7-source
```

This copies the four pinned accessible checkpoints into this installation; allow roughly 157 GB plus a 20 GiB disk reserve, the serving image, Python dependencies and model caches. It verifies revision records and weight byte totals; it does not replace a full model-file hash audit. Existing valid destination checkpoints are reused. Interrupted copies remain in `models/ROLE.installing` for inspection. Existing mismatched weights are never overwritten.

The exact pinned serving image must also be present. To transfer it between compatible Furies, use `docker save` on the source and `docker load` on the target for the digest in `config/models.json`. No serving configuration or NVIDIA driver changes are made by the installer.

Alternatively, explicitly request downloads of the four accessible pinned models and the serving image:

```bash
./scripts/install.sh --mode live --download-models
```

Vision is excluded. The installer does not search for credentials or download gated vision checkpoints. Launch only after installation succeeds:

```bash
./scripts/start_all.sh
./scripts/healthcheck.sh
./scripts/open_desktop.sh
```

Startup is serialized and reuses this installation's running services. It verifies readiness before opening the browser. Live startup can take several minutes while models load and compile. Progress is visible in the terminal and `logs/launch.log`. A missing required role is an actionable failure. Unavailable vision does not fail the working telemetry/document slice. `./scripts/healthcheck.sh --full` checks the separately blocked full multimodal gate.

## Offline Python installation

Obtain wheels for the target's Linux architecture and Python 3.12 using `requirements.lock`, then use:

```bash
./scripts/install.sh --wheelhouse /path/to/wheels
```

This disables Python package-index requests. To use the wheelhouse while downloading live model/image assets, add `--mode live --download-models`; upstream asset downloads still need internet. Live offline installation also needs `--mode live --model-source /path/to/plant7-source` and the preloaded pinned Docker image. Browser runtime assets are bundled; no browser CDN or Node installation is needed. Development browser checks additionally require Playwright Chromium (`.venv/bin/python -m playwright install chromium`).

## Recovery and sharing

- Open `http://127.0.0.1:8097/` on the installed machine. If no desktop is available, startup prints this URL.
- Run `.venv/bin/python scripts/doctor.py` for installation checks, or add `--live` for GPU, Docker, image and weight checks.
- Run `./scripts/healthcheck.sh` for the running application. Refresh reconnects to saved evidence without rerunning the investigation. Failed runs expose retry and an explicitly labelled recorded walkthrough.
- Use `./scripts/start_all.sh --mode replay` to rehearse without loading models. It opens with the recorded-mode URL when used with `--open`. It does not unload any models already resident.
- App-only restart: `.venv/bin/python scripts/restart_app.py`. Stop this installation: `./scripts/stop_all.sh`. These commands verify project ownership and do not stop other projects.
- Port conflicts are reported; unrelated listeners are never killed. One live Plant 7 installation per host uses ports 8097, 8001–8005 and 8013. A recorded installation can use a different application port: `P7_PORT=18097 ./scripts/start_all.sh`; use the same variable for its launcher and health check.
- Each installation generates new control credentials and sessions. Keep `runtime/`, `.env`, `logs/` and `models/` out of a source handoff. Build a new allowlisted bundle using `scripts/package_demo.py --output /path/to/new-release` in the development checkout.
- Remote access uses the machine's already authorized LAN or tailnet address. No Tailscale setup, public tunnel, firewall change or public hosting is performed. “What runs on Fury” supplies following-display and mobile links scoped to the current session.

The final value screen shows actual generation-call tokens (worker, synthesis, audit), measured run time and zero external model API calls for that workflow. Its editable USD rates and volume are illustrative arithmetic. They exclude embeddings/reranking, local hardware, electricity and operations; they are not a provider quote, validated savings or a comparison of model quality.
