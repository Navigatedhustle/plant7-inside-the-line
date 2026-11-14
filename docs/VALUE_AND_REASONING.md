# Explain the engineering value

The comparison is about the investigation work: gathering production records, joining bolt results to bodies, reviewing footage, finding controlled documents, defining a review scope and preparing an evidence-linked handoff. Quality retains the containment and release decisions.

The home screen now puts the illustrative manual baseline beside the measured current attempt. See the work expands six task-by-task comparisons, with a current state for each source or handoff. This preserves the automotive workcell and live Fury telemetry while explaining how those capabilities support an engineering decision.

## Before and after without an invented saving

config/value.yaml supplies the manual baseline, the illustrative manual tasks, their assisted counterparts and the acceptance target. The default 180 minutes is an illustrative assumption, not a measured plant study. The 120 second target comes from the demo acceptance requirement and is labeled as a target, not a result.

The AI attempt timer is measured. Running, stopped, failed, incomplete, replayed and source-complete attempts carry distinct labels. No elapsed attempt is automatically called a completed investigation. No speedup, time saved, ROI or cost saving is calculated. An equivalent accepted case and an appropriate manual baseline would be needed to support such a claim.

The comparison also distinguishes the direct read-only unit passport from an agent conclusion. A working passport does not satisfy video verification, establish physical preload, define the entire calibration-exposure population or authorize release.

## What the model is checking and why

plant7/task_context.py supplies public task intent for actual orchestration stages. Labels describe the operation being attempted; they do not expose private model thoughts or assert that a hypothesis was verified.

| Observable task | Engineering purpose |
| --- | --- |
| Measure yield and rejection counts | Establish the denominator, loss and affected scope. |
| Link tool and bolt results to serials | Keep bolt-level records separate from distinct bodies and shipping state. |
| Review query scope, joins and counts | Challenge a cohort or counting error before executing a worker's SELECT. |
| Check stoppages or supplier groups | Test competing explanations instead of assigning a cause from proximity alone. |
| Retrieve and cross-check controlled records | Use the current process requirement and recorded maintenance history. |
| Check visible fastening sequence | Compare observed work with the instruction without inferring force or preload from appearance. |
| Check claims and citations | Challenge unsupported counts or causal statements before a proposed handoff. |

The left trace shows the model, specific task, why it matters, actual duration and reported decode throughput. Initial planning and later tool selection are labeled as choosing evidence checks. A model call completing does not mean the plant question or Quality decision is resolved.

## Tokenomics that can be defended

The left ledger shows known input tokens, known generated tokens and returned timing records for this view. Token use opens exact totals and per-model counts. The compact ledger rounds only its display; the detail view retains exact returned counts.

Counts come from server usage in model_done events and returned evidence/report timing records. Entries are deduplicated by model role and measurement timestamp, so a worker timing repeated inside its SQL evidence is not billed twice in this view. Prompt counts include repeated or cached context on each request; they are not an estimate of unique evidence volume or new prefill compute.

Interrupted requests, failures without returned timing, and pooling usage are excluded. The ledger is labeled known/reported usage, not a complete billing system. The live station throughput on the right covers the sampled model endpoints; this view's token ledger covers its own returned request records. These scopes and denominators differ.

Tokens describe model work, not the number of accepted findings. No hardware, energy, staffing or operating-cost estimate is included. Replay usage is labeled recorded and is not presented as current inference.

## Verification and limits

scripts/check_value_ui.py checks the configured baseline, unmeasured state, six comparison tasks, target labeling, mobile layout and absence of external page requests. Its --live option uses real local inference, checks the public task/purpose fields, verifies deduplication against actual returned timings, then stops the attempt and confirms it cannot appear as a completed time-saving result. Results are retained in logs/value-ui-check.json.

Existing Cosmos and answer-validation blockers remain. This presentation improvement does not manufacture a golden run, accepted answer, production connector, financial result or completed containment.
