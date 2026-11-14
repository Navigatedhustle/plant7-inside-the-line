# Code walkthrough

This is a local development build. Read logs/blockers.md before making performance or completeness claims. A green application server does not imply the models or investigation passed acceptance.

The browser sends a question to FastAPI. agent.py asks the brain which tools to use. Each tool result receives an evidence identifier. The browser draws those results as they arrive. The run JSON preserves the actual requests, evidence, timings, errors and final response. No framework hides the loop.

| File | What it does and where to look |
| --- | --- |
| plant7/settings.py | Defines local paths, the model manifest and preset questions. source_paths lists the controlled documents that retrieval may read. |
| plant7/clients.py | complete streams an OpenAI compatible request from a fixed loopback endpoint. It counts only server reported tokens. embeddings and rerank call the separate pooling models. |
| plant7/mes.py | validate_sql applies the SELECT boundary, table list and function list. query_mes executes in a read-only DuckDB connection with a timer and row cap. schema supplies column names to the models. |
| plant7/retrieval.py | passages splits source records. build_docs_index embeds them into LanceDB. search_docs combines BM25 and dense ranks, then asks the reranker. It returns the real retrieval mode, including degraded modes. |
| plant7/video.py | chunk_video runs FFmpeg inside the project media container. ingest_video asks Cosmos to describe each chunk, embeds its actual captions and writes the index. search_video filters camera and time before vector ranking. |
| plant7/agent.py | investigate is the central loop. reviewed_query obtains worker SQL and brain approval. draft_report checks the eight sections and their evidence references. Errors remain visible evidence, never invented answers. |
| plant7/telemetry.py | snapshot reads GPU and system counters. probe reads actual model health and generation-token totals. Memory attribution uses project container cgroups; unassigned memory is shown separately. |
| plant7/proxy.py | main binds local API ports. forward connects to each model's Unix socket. Containers have no IP network. The embedding port also routes reranking to its own model. |
| plant7/app.py | FastAPI routes questions, SSE events, charts, reports, health and mobile QR. live_events tracks sessions. loadtest starts twenty actual varied investigations. public_url selects the local network address unless explicitly configured. |
| plant7/audit.py | run journals subprocess arguments, output and status. It is shared by lifecycle and media commands. |
| static/index.html | The single desktop and mobile screen, evidence areas and dialogs. It references local assets only. |
| static/style.css | The square white and pale blue design, Arial and Helvetica stack, projector layout and mobile rules. No font or icon service is called. |
| static/app.js | investigate parses SSE, addEvidence draws citations, drawChart plots actual database rows, and poll updates measured telemetry. It uses textContent for model text. |
| static/health.js | Refreshes endpoint and artifact readiness without concealing unavailable models. |
| config/models.json | Immutable checkpoint revisions, exact container digest, ports and memory fractions. Changing a role requires a new simultaneous memory budget and acceptance. |
| config/gpu_args.json | Read-only mounts of the already installed driver and explicit device access. These arguments work around the absent Docker NVIDIA runtime without editing host configuration. |
| config/qwen3_reranker.jinja | Upstream Apache licensed formatting for original Qwen reranker scoring. Preserve the model's yes/no classification semantics. |
| config/worker_cases.json | Twenty questions and reference SELECTs. Scoring compares results, not spelling or SQL string similarity. |
| config/value.yaml | The only illustrative value assumptions. Manual time and planned cache reservations are editable, not observed savings. |
| scripts/log_command.py | Records each build command and exit status under logs. Use it around manual project commands. |
| scripts/bootstrap_pip.py | Bootstrapped project-local pip because host ensurepip was unavailable. It is setup support, not part of a live investigation. |
| scripts/generate_data.py | make_database creates the seeded fictional fixture, write_documents creates the evidence records, and make_videos draws clearly marked development clips. |
| scripts/download_models.py | Retrieves only pinned checkpoints into models, on CPU NUMA node 0 when invoked as documented. A gated model without HF_TOKEN is skipped and recorded. |
| scripts/manage.py | Starts the largest model first, waits for health, records container IDs and protects ownership. The same module starts the local proxy and app. stop touches only labeled project containers and recorded project process identities. |
| scripts/ingest_video.py | Builds the document index and ingests generated clips or a specified project-local MP4 with its camera metadata. |
| scripts/benchmark.py | Measures endpoint batches at one, eight and twenty clients. It writes raw measurements and the benchmark document; blocked roles have no invented metrics. |
| scripts/benchmark_workers.py | Scores real structured query_mes calls against the twenty reference result sets and records latency and errors. |
| scripts/healthcheck.py | Checks the app, model endpoints, video index and accepted golden trace. Exit 2 means the full show is not ready. |
| scripts/accept_golden.py | Runs the hero question and checks timing and evidence coverage. An inspected, passing real trace can be explicitly selected for the replay. The assistant or operator can inspect it; this is not a separate permission request. |
| scripts/start_all.sh | Runs model startup and then the app. It prints the local URL and preserves a nonzero model startup status. |
| scripts/stop_all.sh | Stops this project's models, media worker, proxy and application while retaining containers, images and checkpoints. |
| scripts/benchmark.sh | Runs the real endpoint benchmark through the command journal. |
| scripts/healthcheck.sh | Runs the readiness checker through the journal. |
| scripts/restore_previous.sh | Stops this project first, then invokes the recorded prior service restoration. |
| scripts/restore_previous.py | Replays the captured prior argv, working directory and nonsecret runtime configuration. It avoids duplicate exact processes and waits for each previous model's health before continuing. Restoration is not run during this build. |
| tests/test_safety_and_fixture.py | Checks external IO rejection, write rejection, path access and the four-point incident fixture. |
| requirements.lock | Exact installed Python versions. Browser QA dependencies, when present, are development tools only. |
| README.md and docs | Operator commands, sources, measurements, presenter script and IP review inventory. |
| docs/research | Archived public cards, configs, file metadata and runtime checks. These are provenance, not runnable scripts. |
| data and runs | Generated local database, video, indexes and actual traces. They are intentionally ignored by Git and reproducible or locally retained. |
| logs | Preflight evidence, stopped services, commands, download measurements and blockers. No passwords or tokens are intentionally recorded. |

## Three likely failure points

1. A model will not start. Run scripts/healthcheck.sh and inspect logs/failure-ROLE.log or the relevant p7 container's logs. Verify the pinned image, the checkpoint byte total and free HBM. Qwen Flash Next must log CUDA placement for its PLE embedding; CPU placement is a failed requirement. Check node 1 FilePages after heavy IO. An authenticated operator can clear page cache. Do not pin inference to node 0 or change drivers.

2. Retrieval cannot produce visual or document evidence. Confirm the embedding and Cosmos endpoints, then run ingest_video.py through the journal. A missing approved token blocks Cosmos. Check data/video camera metadata, the actual chunk captions and data/index. BM25 fallback is visible and does not count as a full hybrid demonstration. Missing video remains incomplete.

3. The investigation is wrong, slow or incomplete. Open runs/RUN_ID.json. Follow each tool result to its SQL, caption or cited source. Check whether the worker drafted the right columns and the brain reviewed them. Compare with config/worker_cases.json. Errors and the 115 second timeout remain explicit. Do not promote a failed trace to golden_run.json. Benchmark real endpoints before tuning context or concurrency.

Mechanical citations do not guarantee that a claim follows from a source. Quality engineers must assess causal interpretation, containment scope and disposition before real operational use.

Additional operator helpers: scripts/set_hf_token.py securely prompts in the user's terminal and writes only the ignored project .env with mode 0600. scripts/verify_hf_access.py downloads a tiny pinned gated configuration to test permission without printing the token. scripts/compare_workers.py runs the paired real worker benchmark, stops only labeled project model containers between candidates, and restores the lineup. scripts/check_ui.py checks desktop and mobile interaction, screenshots, JavaScript errors and external page requests using local Playwright.

The final fixture is explicitly historical as of November 13 at 18:00 UTC. Tests check that torque pass flags agree with unit first pass status, tool identities are unique across lines, shipments precede the scenario time, and drift starts only after the maintenance release. retrieval.corpus_signature detects changed source files so a stale dense index cannot silently count as hybrid retrieval.

agent.context_result bounds raw rows sent to the model while retaining complete returned results on the evidence board. A bounded sample is never a population count. verify_answer performs a second real brain request to check the proposed answer against evidence, remove unsupported numerical claims and state missing sources. This adds measured inference time; it is not a guarantee of correctness. Report requests use a constrained JSON schema for exactly eight cited sections. Reports are generated only when requested.

scripts/license_inventory.py extracts Python and operating system package metadata from the selected container. The resulting license inventory includes unresolved package notices for IP review rather than claiming all transitive licenses are cleared.

plant7/task_context.py maps observable query and tool operations to a public task and engineering purpose. agent.py attaches these labels to SSE events without changing the model's prompts or exposing private reasoning. static/value.js consumes the run events, deduplicates returned timing records by role and timestamp, and updates the comparison and token ledger. config/value.yaml holds the illustrative manual workflow and baseline. static/value.css provides the comparison layout. scripts/check_value_ui.py verifies assumption labeling, known token counts, actual task events and stopped-attempt handling. See VALUE_AND_REASONING.md for the measurement limits.

plant7/automotive.py adds direct, read-only exploration. context counts distinct units before returning the recorded exception sample, source queries, WI, PFMEA and maintenance records. unit_passport validates a synthetic serial, then returns its unit, four fastening records, route and defects. These API views do not call the agent or satisfy its acceptance gate. static/automotive.js listens for p7:selection from the chart, refreshes scoped records, and opens the engineering and passport dialogs. jointGraphic uses actual bolt values in a passport and the WI's required sequence in the separate process reference; those two meanings are explicitly labeled. static/automotive.css lays out the views, and static/vehicle-body.svg is original illustrative artwork. scripts/check_automotive_ui.py verifies the interactions using real fixture queries with no model substitution.

The presentation UI now keeps a Map of returned evidence. renderSources creates source cards and openEvidence opens the original query, rows, passages or complete documents. citationText makes answer citations open those same sources. inspectSelected preserves chart grain: shift-level yield opens a shift, while a daily tool mean opens the selected tool over all shifts. An incrementing request identifier prevents a slower earlier chart click from overwriting the latest selection. setRunning handles request state and Stop uses AbortController. Presentation mode requests fullscreen with a layout fallback. No new external JavaScript libraries were added. See UI_GUIDE.md for the operator flow.
