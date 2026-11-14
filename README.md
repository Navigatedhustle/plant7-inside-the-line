# Plant 7: Inside the Line

A local automotive investigation demonstration on HP ZGX Fury. Original browser factory and vehicle cutaway, read only synthetic evidence, actual local model inference, traceable inspection scope and explicitly simulated containment.

**Vision is unavailable.** The working local slice investigates telemetry and documents. The synthetic clip demonstrates the presentation workflow, not validated camera sequence recognition. Full multimodal and customer camera footage acceptance remain blocked. No production or safety system is controlled. This private release is shared at the owner’s explicit request; prior HP IP Marketing Review remains pending and no public distribution approval or endorsement is claimed.

For a completely fresh Fury, start with the [PDF installation guide](docs/Plant7-Fresh-Fury-Guide.pdf) or its [copyable command source](docs/FRESH_FURY.md). The [v1.1.0 release](https://github.com/Navigatedhustle/plant7-inside-the-line/releases/tag/v1.1.0) supplies the application and offline Linux ARM64/Python 3.12 wheels. [QUICKSTART.md](QUICKSTART.md) provides the shorter path. `./scripts/install.sh` installs the clearly labelled recorded walkthrough without GPU or Docker. The live install checks the compatible Fury GPU stack, the four pinned accessible checkpoints and the serving image. Credentials, sessions, machine-specific GPU bindings and weights are excluded from the release bundle.

```bash
./scripts/start_all.sh
./scripts/open_desktop.sh
./scripts/healthcheck.sh
```

The new guided story uses **one blue button** (or right arrow / space). It starts the local investigation while entering Station 40, plays the synthetic clip with its source cursor, then advances through the exact scope to the decision and measured token economics. Optional clicks inspect an actual fastener, unit passport, evidence or explicitly simulated containment. There is no presenter sign-in or credential entry; each browser receives an automatically isolated session capability. Refresh resumes the same browser session. Recorded mode is clearly labelled before starting and throughout use.

Everything fits without page or panel scrolling at the tested 1920×1080, 1440×900, 1366×768 and 1280×720 desktop viewports. The final value screen shows server-reported generation tokens for this run, the measured investigation time and an editable illustrative token-charge comparison. Hardware, electricity, operations, embedding/reranking tokens and model equivalence are excluded; no savings or total ownership cost is asserted.

Routes `/`, `/wall?session=ID`, `/m?session=ID`, `/compute`, `/health` and `/legacy` remain available. “What runs on Fury” links the current session's read-only following display and mobile view. Existing private tailnet access remains https://hp-zgx-fury-showcase.taild25e44.ts.net:8443. No public tunnel or new sharing configuration was enabled.

Startup verifies the selected working slice before opening a browser and serializes repeated launch attempts. The known unavailable vision role does not fail the telemetry/document slice. `./scripts/healthcheck.sh --full` retains the separate full multimodal acceptance gate. Failures remain visible with retry or a deliberately selected labelled recording.

Prepare containment still requires a completed local result, an exact unit draft and a named simulation approval. It changes only the browser's demo session. Captured replay never runs inference or increments live token usage.

Local UI rebuild, with dependencies already scoped under node_modules and .tools:

```bash
./scripts/build_ui.sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_guided_ui.py
```

The committed browser bundle needs no build tools or external runtime assets to serve. Regenerate isolated counterfactual fixtures with `.venv/bin/python scripts/build_scenarios.py`; this does not replace the original MES. Preserve the existing models and endpoints in config/models.json.

Read [BUILD_STATUS](docs/BUILD_STATUS.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [BASELINE](docs/BASELINE.md), [BENCHMARKS](docs/BENCHMARKS.md), [KNOWN_LIMITATIONS](docs/KNOWN_LIMITATIONS.md), [RESEARCH](docs/RESEARCH.md), [ASSET_PROVENANCE](docs/ASSET_PROVENANCE.md), [FOOTAGE_GUIDE](docs/FOOTAGE_GUIDE.md) and [TALK_TRACK](docs/TALK_TRACK.md). Actual screenshots, short capture, source trace and sample brief/8D exports are in docs/captures.

The private release contains curated source and generated synthetic demo assets. Source-machine logs, credentials, sessions, virtual environments, model weights and host-specific GPU bindings are excluded. Original local recovery checkpoints remain documented in BUILD_STATUS.md on the development machine. Do not run unrelated showcase restoration workflows as part of this project.
