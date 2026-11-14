# SQL tool worker comparison

Twenty structured tool calls against the same seeded DuckDB. Accuracy compares result sets, not SQL strings. Model errors count as failures. Different standalone memory reservations are used for the challenger; latency is not an all-model concurrency result.

| Model | Correct / 20 | Median request latency s |
| --- | ---: | ---: |
| nvidia/Qwen3.8-27B-NVFP4 | 20 / 20 | 4.686 |
| openai/gpt-oss-120b | 19 / 20 | 2.888 |

Accuracy first, latency second winner: nvidia/Qwen3.8-27B-NVFP4.

The smaller Qwen worker remains the selected lineup candidate, subject to the complete hero acceptance.

The gpt-oss failure was case 13: it applied a lower date bound but omitted the upper bound for one day of downtime, returning five later days as well. This is an execution-result mismatch, not a parser failure. Both candidates returned real completions for all 20 cases.

Both comparison runs used eager execution. Qwen thinking was disabled; gpt-oss used low reasoning. The latency numbers above belong to those actual runs on the original seeded fixture at commit e3932ca. The final fixture moves the fourteen days to October 30 through November 12 and corrects tool identity, causal timing and shipment chronology. Re-executing both models' saved SQL against that final fixture still scores 20/20 and 19/20 (runs/worker-rescore-final.json). This rescore reuses the measured SQL; it is not a new latency measurement or a new model generation.
