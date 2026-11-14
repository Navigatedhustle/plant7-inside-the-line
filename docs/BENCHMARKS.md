# Measured workload and validation

Measured on 2026-11-14 UTC on this HP ZGX Fury. Raw source records are in docs/captures and full run traces remain under runs/. Model configuration was unchanged: four resident roles, exact revisions and serving caps in config/models.json. Actual /v1/models IDs after a complete restart are in captures/restarted-health.json. The configured Cosmos endpoint is unavailable; **these are telemetry/document investigation results, not validated full multimodal vision performance**.

## Three consecutive hero runs after the stopped-service startup check

These used the actual synthetic database, exact cohort query, local SQL worker, hybrid retrieval, brain synthesis and a second brain audit. Queue delay was measured separately. Prior resident requests warmed kernels and context; this is not a cold-model-load latency claim.

| Run ID | First useful source s | Complete s | Queue delay s | Result |
| --- | ---: | ---: | ---: | --- |
| 8f30316d8df34004b8f8d0e392ca6968 | 0.131 | 5.057 | 0.0005 | completed |
| 4b5e55236b0d430dbc1c038b53ace47b | 0.133 | 4.616 | 0.0005 | completed |
| 907afb00b8c7436bbdc3eb52146461ff | 0.127 | 3.716 | 0.0005 | completed |

An earlier warmed sequence measured first evidence at 0.131 to 0.175 seconds and completion at 3.468 to 3.735 seconds; those real trace IDs remain on disk. Startup plus model loading is not included in investigation times. The original general agent baseline failed its answer audit after 58.765 seconds; it was not accepted as a successful replay. Early new-workflow trials also exposed causal overclaims and cross-dataset leakage. Those were rejected for acceptance; source filtering, typed output constraints and an additional audit were introduced. Model interpretation still requires human review.

The new replay source is a real successful local run with its unavailable vision result preserved, not a fabricated all-source investigation. Exact acceptance scope is included in captures/replay-run.json. The separate original all-three-source golden gate remains unpassed.

## Bounded 1, 8 and 20 request tests

Warmed four-role local lineup, five varied manufacturing questions, actual retrieved evidence context. Exact per-call input token counts, generated tokens and TTFT are stored in run traces. Stage execution limit is two investigations. Test window is first submission through the final terminal state, including queueing, tools and audits. It is not a decoder-only throughput window. No vision decode took place.

| Submitted | Completed | Failed | Canceled | Maximum running | Maximum queued | Duration s | Completed requests/s | Generated tokens/s over whole window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 0 | 1 | 0 | 4.140 | 0.242 | 150.7 |
| 8 | 8 | 0 | 0 | 2 | 6 | 19.192 | 0.417 | 255.7 |
| 20 | 20 | 0 | 0 | 2 | 18 | 48.734 | 0.410 | 242.6 |

Sampled device memory high water during this test: **202829 MiB (212.682 GB decimal)**, sampled approximately twice a second using nvidia-smi. It includes device allocations and cache, not only weight tensors. This is a sampled peak, not a guaranteed instantaneous maximum. App process kernel high water and current per-role/device measurements are in captures/runtime-memory.json. No allocation or full-context concurrency claim is inferred from the configured context cap.

The 20 request action submits actual varied work; it does not mean 20 simultaneous decodes. The original separate endpoint microbenchmark remains in the earlier Git history and WORKER_BENCHMARKS.md; its higher token-only rates must not be substituted for the end-to-end rates above. No whole-plant capacity or comparison against another GPU is claimed.

## Functional and visual validation

The behavioral suite passes 38 tests, including original SQL safety tests, exact hotspot IDs/timestamps, complete cohort identity/counts, alternate datasets, missing video, idempotent simulated holds, read only source preservation, mobile authorization rejection, cancellation, replay isolation, unsafe media paths and model-failure behavior. See tests/test_inside_line.py.

Actual Playwright Chromium checks and viewport screenshots cover all five chapters at 1920 by 1080, 1440 by 900 and 1366 by 768. The complete browser result is captures/browser-audit.json. Functional checks exercise scene controls, a real local run, video/tool cursor and gaps, unit passport, named simulated approval, exports, refresh recovery, replay badge, SSE cursor, wall/mobile separation, keyboard, reduced motion and WebGL fallback. Earlier browser checks found and repaired refresh persistence, clip overlay capture and navigation selector issues. Only the final successful browser audit is counted as acceptance.

Rendering is measured in headless Chromium on Fury with SwiftShader and a capped render loop. It is **not the actual presenter laptop**. Observed software browser samples were around 27 to 30 FPS during development; the dedicated foreground samples are in render-measurements.json (overview mean 28.28 FPS, assembly 30.00 FPS, evidence 30.00 FPS). Pixel ratio adapts downward below 24 FPS. The requested 30 FPS on the physical presenter laptop remains unmeasured and requires onsite rehearsal. Screenshot inspection is not a substitute for that measurement.

The isolated real workflow test in captures/offline-workflow.json denied external socket destinations and completed using only 127.0.0.1. The controlled browser test denied external destinations, loaded local assets and exercised the workflow with no external page requests. No host network was unplugged or reconfigured. These checks support only their tested application scope, not an audited privacy guarantee.

A complete stop/start using the existing scripts closed all project app/proxy ports and restarted the four available pinned containers plus the app. The vision checkpoint was explicitly blocked and start_all returned exit 2 for that reason. No unrelated workloads, drivers, caches, SSH or Tailscale settings were changed. The app remains available at http://127.0.0.1:8097.

The final brief is approximately three kilobytes of Markdown and links the exact machine-readable manifest instead of appending hundreds of unit rows. The 8D draft retains suspected/pending status and the same manifest link. The checked in sample exports and short walkthrough were captured from the actual UI workflow, not assembled as static mockups.
