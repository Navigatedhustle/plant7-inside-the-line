# Model research and selection
Research date: 13 November 2026. Repository metadata and model cards are archived under research/. No checkpoint was downloaded before this report. A remote file size is not a measured device allocation. GB below means decimal 10^9 bytes; GiB means 2^30 bytes. The GPU reports 256703 MiB, or approximately 269.17 GB, while the product specification states 252 GB. Planning below conservatively uses 252 GB.

## Decision
The original GLM lineup is rejected for simultaneous serving. GLM weights alone are 204.439 GB. Adding the publisher's 32 GB Cosmos minimum and the smaller official Qwen worker's 21.922 GB already requires 258.361 GB, before retrieval, brain KV, worker KV, or graphs. The 92 percent conservative ceiling is 231.84 GB.

Proposed brain: nvidia/Qwen3.8-Flash-Next-NVFP4. It has a 125B backbone with 6B activated, plus 51B n-gram embeddings and 4B MTP. Its 132.680 GB mixed checkpoint provides enough space for a full separate vision and SQL stack. Cap context at 262144 tokens; do not enable MTP. This is a capacity driven swap, with performance acceptance still pending. Its license differs from the worker's Apache license. [Card](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4), [file metadata](https://huggingface.co/api/models/nvidia/Qwen3.8-Flash-Next-NVFP4?blobs=true), [license](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE).

## Verified identities and remote checkpoint sizes
Root safetensors totals come from each repository's API with blobs=true, archived with immutable revision. They exclude alternative formats in subdirectories and tokenizer/config overhead. Actual local disk sizes remain unmeasured until download. Packed tensor element counts must not be treated as the original parameter count.

| Role | Exact repository | Parameters / active | Stored precision | Weight GB | Governing license and sources |
| --- | --- | --- | --- | ---: | --- |
| Original brain, rejected lineup | nvidia/GLM-5.3-Flash-NVFP4 | 320B / 18B | mixed NVFP4, BF16 exclusions; FP8 KV config | 204.439108056 | MIT; [card](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4), [files](https://huggingface.co/api/models/nvidia/GLM-5.3-Flash-NVFP4?blobs=true) |
| Proposed brain | nvidia/Qwen3.8-Flash-Next-NVFP4 | 125B backbone / 6B; 51B embedding plus 4B MTP | NVFP4 experts, BF16 other layers, FP8 embedding and MTP | 132.680249378 | NVIDIA Open Model License plus Qwen Community License 1.0; [card](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4), [files](https://huggingface.co/api/models/nvidia/Qwen3.8-Flash-Next-NVFP4?blobs=true) |
| Vision, access blocked | nvidia/Cosmos-Reason2-8B | 8B class; API reports 8.767B dense tensors | BF16 | 17.534339368 | NVIDIA Open Model License; [card and access gate](https://huggingface.co/nvidia/Cosmos-Reason2-8B), [metadata](https://huggingface.co/api/models/nvidia/Cosmos-Reason2-8B?blobs=true) |
| Selected worker | nvidia/Qwen3.8-27B-NVFP4 | 27B dense / all active | mixed NVFP4 and FP8 | 21.921697280 | Apache 2.0; [card](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4), [files](https://huggingface.co/api/models/nvidia/Qwen3.8-27B-NVFP4?blobs=true) |
| Worker BF16 reference | Qwen/Qwen3.8-27B | 27B class; 27.781B tensors | BF16 | 55.563006776 | Apache 2.0; [card](https://huggingface.co/Qwen/Qwen3.8-27B), [files](https://huggingface.co/api/models/Qwen/Qwen3.8-27B?blobs=true) |
| Worker challenger | openai/gpt-oss-120b | 117B / 5.1B | MXFP4 experts; BF16 other tensors | 65.248893184 | Apache 2.0; [card](https://huggingface.co/openai/gpt-oss-120b), [files](https://huggingface.co/api/models/openai/gpt-oss-120b?blobs=true) |
| Retrieval | Qwen/Qwen3-Embedding-0.6B | 0.596B dense / all active | BF16 | 1.191586416 | Apache 2.0; [card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [files](https://huggingface.co/api/models/Qwen/Qwen3-Embedding-0.6B?blobs=true) |
| Reranker | Qwen/Qwen3-Reranker-0.6B | 0.596B dense / all active | BF16 | 1.191588280 | Apache 2.0; [card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B), [files](https://huggingface.co/api/models/Qwen/Qwen3-Reranker-0.6B?blobs=true) |

The compact retrieval pair provides instruction-aware retrieval and pair scoring without consuming tens of gigabytes. Hybrid lexical matching preserves station and tool identifiers. Model-specific embedding instructions and yes/no reranker semantics must be retained. Selection is an engineering choice, not a claim of benchmark superiority.

## Initial simultaneous sizing plan
These are explicit planning reservations, not measured inference results. Live UI must report actual allocations and may display these only as a labeled plan.

| Model | Weights GB | KV reservation GB | Graphs, state, workspace GB | Total GB | vLLM fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8 Flash Next | 132.680 | 20 | 8 | 160.680 | 0.64 |
| Cosmos Reason 2 | 17.534 | 8 | 9 | 34.534 | 0.14 |
| Qwen3.8 27B | 21.922 | 5 | 3 | 29.922 | 0.12 |
| Embedding | 1.192 | 0 | 1.2 | 2.392 | 0.01 |
| Reranker | 1.192 | 0 | 1.2 | 2.392 | 0.01 |
| Total | 174.520 | 33 | 22.4 | 229.920 | 0.92 |

This initial sizing plan totaled 229.920 GB. It is superseded by runtime observations below: vLLM fills its cache reservation against the device-reported capacity rather than the nominal product capacity. Fractions total 0.92 and are enforced; they do not predict exact final process memory. If a model cannot load or concurrency exhausts cache, lower concurrency or revise the lineup and rerun acceptance. Never enable CPU weight offload or swap to conceal a fit failure.

From the proposed brain config, full-attention K/V alone at FP8 is 12 layers × 2 K/V × 2 heads × 256 dimensions = 12288 bytes per token, about 3.22 GB for one 262144-token sequence. Indexer state, linear attention state, multiple requests, alignment, and runtime overhead are additional; the reservation deliberately exceeds that lower bound. [Config](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/blob/main/config.json). A 256K cap leaves less aggregate cache pressure than a 1M cap, but does not imply twenty simultaneous full-context sessions.

## Original GLM recipe
Read before selecting alternatives: [capetron recipe](https://github.com/capetron/glm-5.3-flash-dgx-station-gb300). The MIT recipe pins digest 8e138f4eac3a39cbab573e11cebe7cadacc939745003d0fd2b460b5576c1015b, TP1, context 1048576, max sequences 256, utilization 0.94, chunked prefill, prefix caching, glm47 tool parser, glm45 reasoning parser, and no MTP. Its 0.94 allocation and public bind are unsuitable for this stack. Use 127.0.0.1 and combined fractions at most 0.92.

Its NUMA finding matters: file cache can occupy HBM node 1. Clear cache before model startup and bind bulk downloads to CPU memory node 0. Do not bind inference containers to node 0. We did not install its systemd unit, delete its prior containers, or modify the machine. Publisher throughput numbers are not this project's benchmarks. [Service](https://github.com/capetron/glm-5.3-flash-dgx-station-gb300/blob/main/systemd/glm53-flash.service), [prestart](https://github.com/capetron/glm-5.3-flash-dgx-station-gb300/blob/main/systemd/glm53-flash-prestart.sh).

## Serving verification
The selected release tag vllm/vllm-openai:v0.25.1-aarch64 resolves to arm64 Linux digest sha256:2cc49b81319f7a66a33dd8bd63a7bfddae079122b33ce51989b6828a1f038c37. Manifest is archived. Pull and runtime smoke test are pending; this is not yet an image-used claim.

Official vLLM documentation supports architecture-specific aarch64 tags and recommends CUDA 13 for GB300. [Docker deployment](https://docs.vllm.ai/en/stable/deployment/docker/). Model cards document Blackwell testing; Qwen worker explicitly lists GB300. The proposed brain requires upstream commit d4d703caf908786416585ceb1f369e2e0363358b or newer without MTP. Verify installed model registry and commit before downloading its weights. Architecture support, kernel support, and a successful inference request are separate checks.

Cosmos publisher minimum: 32 GB and vLLM at least 0.11.0. Blackwell platforms include GB200 and DGX Spark, supporting the Arm deployment path, but this station has not been tested by this project. [Publisher inference instructions](https://github.com/nvidia-cosmos/cosmos-reason2/blob/main/README.md).

Reason 2 uses mm_processor_kwargs.size.shortest_edge and longest_edge rather than Reason 1 videos_kwargs.min_pixels/max_pixels. Values cannot be renamed mechanically because semantics changed. Frame timing is supplied through video metadata; procedural timestamps remain a human development aid. [Migration](https://github.com/nvidia-cosmos/cosmos-reason2/blob/main/docs/troubleshooting.md). The gated config could not be read without a token; do not claim complete config verification or download it while blocked.

## Rejections and new-release check
DeepSeek V4.1 Flash: MIT, 552B backbone, 8B active during prefill and 16B during decoding, plus 196B conditional-memory parameters. Even an idealized 4-bit 552B backbone alone is 276 GB, above the nominal HBM capacity before scales, vision, or KV. The published mixed checkpoint totals 510.297 GB. Rejected by capacity without downloading or spending benchmark time. [Card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash), [file metadata](https://huggingface.co/api/models/deepseek-ai/DeepSeek-V4.1-Flash?blobs=true).

GLM-5.3-Flash-FP4-Local is 176.710 GB in remote weights but has NVIDIA Open Model Agreement terms and requires a special compressed-scale runtime not yet upstream according to its card. Do not substitute it into the verified original recipe. Not adopted. [Card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local).

The bounded new-release check queried newest 30 repositories each from nvidia, Qwen, zai-org, and deepseek-ai and reviewed public search through 13 November. Archived recent-*.json files show only NVIDIA Kimi K3.1 Pro and MetricTrail created after 1 November in that sample. Updated dates are not release dates. Nemotron 3.5 Bolt was updated 7 November but its card reports an October release; its 24.084 GB IQ2 checkpoint, 74B/9B architecture, OpenMDW 1.1 terms and additional kernel requirements make it a separate candidate, not a verified upgrade. No post-November-1 swap has passed the same fit, runtime, and task tests. [Bolt card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB). This is a bounded check, not proof that no other release exists.

Kimi K3/K3.1 and Qwen3.8 2.4T are excluded from execution as requested. Do not download or claim two-node operation has been demonstrated.

## Hardware panel sources
Nano: 128 GB unified memory, 273 GB/s; [HP QuickSpecs](https://h20195.www2.hp.com/v2/getpdf.aspx/c09212373.pdf). Fury: 252 GB HBM3e at up to 7.1 TB/s, 496 GB LPDDR5X at 396 GB/s, 748 GB coherent; [HP specifications](https://www.hp.com/ar-es/workstations/ai-stations.html). These are specification maxima, not measured bandwidth in this demo.

## Worker selection gate
Benchmark the NVFP4 Qwen worker against gpt-oss-120b on the same 20 prompts, database, seed and deterministic result checks. Rank execution accuracy first, then median end-to-end latency. Pending real runs, Qwen was provisional until the real comparison below; it is now selected on fixture accuracy. A gpt-oss win requires a new simultaneous memory budget; its extra 43.327 GB cannot silently replace the current worker. No quality or latency winner is reported yet.

## Runtime verification update
The first release image was pulled and tested. It lacks Qwen4Exp and Glm5Next, so it is rejected for the proposed brain. The newer nightly-aarch64 resolves to **sha256:851ef53f3318114d3b93d5fe6f075069d91b7e88d4694cff1e165ef0b903b906**, vLLM **0.34.0rc1.dev398+g153dc0464**, CUDA **13.0**. This is the selected exact image actually pulled and used for checks. Its registry includes Qwen4ExpForConditionalGeneration, Glm5NextForConditionalGeneration, Qwen3_5ForConditionalGeneration and GptOssForCausalLM. A real GB300 CUDA tensor allocation and reduction returned 16.0. These are runtime checks, not model inference benchmarks.

Docker has no NVIDIA runtime registered. Without changing the daemon or drivers, the project passed through four existing NVIDIA device nodes and mounted installed driver libraries read-only under /usr/local/nvidia/lib64. The exact arguments are in config/gpu_args.json; results are archived in research/nightly-runtime-check.txt. This is a project-local fallback, not a claim that the machine has a configured NVIDIA Container Toolkit. No system CUDA or driver files were changed. Checkpoint inference and all-model concurrency remain unverified.

## Local checkpoint disk measurements
The actual downloaded directories were measured after download, including tokenizer/config metadata. Brain: 132.734501367 GB logical, 132.734701568 GB allocated. Worker: 21.945285459 GB logical, 21.945417728 GB allocated. Embedding: 1.207473160 GB logical, 1.207554048 GB allocated. Reranker: 1.207475374 GB logical, 1.207574528 GB allocated. Worker challenger: 65.276862558 GB logical, 65.277063168 GB allocated. Exact records: logs/download-ROLE.json. Cosmos remains undownloaded pending access.

The first eager GPU-resident brain startup logged 120.54 GiB model memory and 2680895 KV tokens. Its PLE table explicitly reported weight_device=cuda:0 and pinned=False, with Engram CPU offload disabled. A real six-token JSON smoke response completed, but this tiny cold request is not a representative decode benchmark. The final serving configuration enables decode CUDA graphs without Torch compilation; it must be remeasured rather than inheriting the eager smoke result.

Access update: a token is now present and valid. Cosmos authorization returned HTTP 403 because that account is not on the authorized list. This is a model gate, not an absent-token failure.

## Worker decision from real tool calls
Qwen NVFP4: 20/20 correct, median 4.686 seconds. gpt-oss: 19/20 correct, median 2.888 seconds. Select Qwen on accuracy first. Both ran eager mode against the same database with named tool calls and a 512-token cap; Qwen thinking was disabled and gpt-oss reasoning was low. These are observed task results for this small fixture, not general quality claims. Full outcomes: docs/WORKER_BENCHMARKS.md and runs/worker-*.json.

After the comparison, the synthetic generator's Monday drift onset was corrected to the recorded 10:05 tool return time, preserving the Tuesday signal and four-point shift drop. The worker cases do not query Monday torque and their expected values remain unchanged. Regenerated fixture and causal-order tests were verified separately.

## Observed memory with four models resident
The available KV pools logged by the selected runtime are 38.08 GiB for the brain, 10.09 GiB for the worker, 1.15 GiB for embeddings and 1.14 GiB for reranking. These are actual startup reports, not the initial KV assumptions. Source excerpts: research/memory-ROLE.txt.

| Loaded role | Logged model load GiB | Logged available KV GiB | Sampled peak process GB |
| --- | ---: | ---: | ---: |
| Brain | 120.54 | 38.08 | 172.422 |
| Worker | 18.96 | 10.09 | 32.730 |
| Embedding | 1.12 | 1.15 | 3.431 |
| Reranker | 1.12 | 1.14 | 3.433 |

Device peak during the four-model endpoint tests was 212.084 GB. Adding the initial 34.534 GB vision weight/cache/workspace allowance gives 246.618 GB as a sizing calculation versus nominal 252 GB. This is not a full-stack measurement: Cosmos has not loaded, and its final allocation must be measured. Using its complete 0.14 fraction against the reported device capacity would reserve about 37.68 GB. Model file bytes, loaded tensor memory and total process memory differ; unused vision/MTP tensors, contexts, caches and workspaces account for those differences. Pooling servers also allocate their own cache and CUDA context. Do not present the initial 229.920 GB plan as measured memory.

The decode CUDA graph configuration was successfully started and benchmarked. Brain PLE remained on CUDA. Project containers now mount only their own checkpoint, cache, socket, video and configuration paths; the project .env is not mounted. All inference containers have network none.
