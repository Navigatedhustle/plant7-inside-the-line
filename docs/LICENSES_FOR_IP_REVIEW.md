# License inventory for HP IP Marketing Review

Status: Owner-authorized private GitHub and email handoff requested 14 November 2026. The previous local-only delivery note is superseded by that explicit instruction. HP IP Marketing Review has not been completed or approved. This inventory identifies terms; private delivery does not assert public distribution approval or grant a new open-source licence.

Automotive extension: static/vehicle-body.svg is original illustrative artwork authored for this local fictional demo. The automotive JavaScript and CSS add no third-party asset, font or runtime dependency. No real automaker design, logo or production CAD was imported. The original implementation and artwork remain subject to HP IP Marketing Review.

## Models and recipes

| Artifact | License / terms | Use and source |
| --- | --- | --- |
| nvidia/Qwen3.8-Flash-Next-NVFP4 | NVIDIA Open Model License and Qwen Community License 1.0 | Proposed loaded brain. [Card](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4), [base license](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE). Pinned revision in config/models.json. |
| nvidia/Cosmos-Reason2-8B | NVIDIA Open Model License | Gated vision model; not downloaded without approved access. [Terms and gate](https://huggingface.co/nvidia/Cosmos-Reason2-8B). |
| nvidia/Qwen3.8-27B-NVFP4 | Apache 2.0 | Provisional tool worker. [Card](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4). |
| openai/gpt-oss-120b | Apache 2.0 | Downloaded worker challenger. [Card](https://huggingface.co/openai/gpt-oss-120b). |
| Qwen/Qwen3-Embedding-0.6B | Apache 2.0 | Embedding model. [Card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B). |
| Qwen/Qwen3-Reranker-0.6B | Apache 2.0 | Reranker. [Card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B). |
| Qwen/Qwen3.8-27B | Apache 2.0 | BF16 reference researched; no reference weights downloaded. [Card](https://huggingface.co/Qwen/Qwen3.8-27B). |
| nvidia/GLM-5.3-Flash-NVFP4 | MIT | Researched and rejected for simultaneous capacity; no checkpoint downloaded. [Card](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4). |
| deepseek-ai/DeepSeek-V4.1-Flash | MIT | Rejected by capacity; no checkpoint downloaded. [Card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash). |
| nvidia/GLM-5.3-Flash-FP4-Local | NVIDIA Open Model Agreement; MIT base | Researched, not adopted. [Card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local). |
| nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB | OpenMDW 1.1 | Researched, not adopted. [Card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB). |
| capetron GB300 GLM recipe | MIT | Read and archived as provenance; its systemd installation was not applied. [Repository](https://github.com/capetron/glm-5.3-flash-dgx-station-gb300). |
| Qwen reranker chat template | Apache 2.0 | Copied from upstream vLLM. [Source](https://github.com/vllm-project/vllm/blob/main/examples/pooling/score/template/qwen3_reranker.jinja). Local copy in config. |
| NVIDIA VSS blueprint | Apache 2.0 plus repository license notices | Architectural reference only, not bundled implementation. [Repository](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization). |

Kimi and very large Qwen variants were not downloaded or executed. They are mentioned only as untested scale-out examples. Public model cards and metadata archived under docs/research retain their upstream provenance.

## Containers and existing driver

Selected model and media image: vllm/vllm-openai@sha256:851ef53f3318114d3b93d5fe6f075069d91b7e88d4694cff1e165ef0b903b906.

Rejected release used for architecture and CUDA checks: vllm/vllm-openai@sha256:2cc49b81319f7a66a33dd8bd63a7bfddae079122b33ce51989b6828a1f038c37.

All p7 containers use one of these two images. vLLM source is Apache 2.0, but that does not make the whole image Apache licensed. The image includes Ubuntu packages under their individual licenses, NVIDIA CUDA components under the applicable CUDA EULA and third-party notices, and Python dependencies with separate terms. [vLLM license](https://github.com/vllm-project/vllm/blob/main/LICENSE), [CUDA terms](https://docs.nvidia.com/cuda/eula/index.html).

The selected image package/version inventory is in docs/research/container-packages.txt. docs/CONTAINER_LICENSE_INVENTORY.json additionally records 283 container Python distributions and 489 OS packages, with declared license labels and notice paths; 126 OS packages require reading the full notice rather than relying on a machine-readable label. Its FFmpeg binary reports GPL version 2 or later, archived in container-ffmpeg-license.txt. Keep these notices with any redistribution review. The original host driver is mounted read-only and not modified or copied into the repository.

A full transitive image license clearance remains an IP review task; this report does not certify every upstream binary for marketing redistribution.

## Python, browser and JavaScript

Installed Python distributions and their declared license expressions, classifiers and project URLs are enumerated individually in [PYTHON_LICENSE_INVENTORY.json](PYTHON_LICENSE_INVENTORY.json). Versions are pinned in requirements.lock. This includes FastAPI, Uvicorn, OpenAI client, httpx, DuckDB, sqlglot, NumPy, PyArrow, LanceDB, rank-bm25, ReportLab, qrcode, Pillow, PyAV, dotenv, PyYAML and transitive dependencies.

Playwright is a development-only browser QA dependency under Apache 2.0. Its local Chromium download includes Chromium BSD terms and separate third-party notices. It is not an application runtime dependency or an exported browser asset. [Playwright license](https://github.com/microsoft/playwright/blob/main/LICENSE), [Chromium license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE).

The guided interface bundles Three.js 0.180.0 (MIT) and uPlot 1.6.32 (MIT) locally. Their full notices are in static/inside/licenses/; version and provenance records are in ASSET_PROVENANCE.md. The preserved legacy interface uses original application JavaScript and native SVG charts. Icons are text glyphs. No external font files are distributed: CSS uses the machine's local Arial/Helvetica font stack. There are no font, icon or CDN requests.

## Data and generated media

mes.duckdb, maintenance_log.csv, shift_notes.md, controlled instructions, FMEA, PPAP summary and distractor records are original fictional fixtures generated locally. No external manufacturing dataset is included.

All bundled MP4 clips are original procedural animations generated with Python, Pillow and the local H.264 encoder. They depict a generic fixture and moving tool marker, not real people or customer footage. No generative world model video was produced. Codec patent and distribution considerations should be included in normal review of the final show packaging.

Real mock-station footage is not yet supplied. Its facility permission, releases if people appear, source ownership and permitted marketing uses must be added before a live show. The UI and README visibly label the current footage as development placeholders.

Original project code, synthetic records and generated visuals have not been assigned an external open-source license. The owner authorized this private repository/email handoff; broader publication and marketing clearance remain separate.
