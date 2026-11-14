# Research and original design interpretation

All URLs below were opened and read on **2026-11-14 UTC**. They were available unless noted. These references inform an original fictional operational visualization. No geometry, logos, footage or proprietary assets from these companies were copied. No endorsement, popularity claim, validated digital twin or production integration is implied.

| Official reference | Observed context | Original implementation decision |
| --- | --- | --- |
| https://newsroom.porsche.com/it_CH/2024/innovation/porsche-spatial-computing-apple-vision-pro-38051.html | Spatial media presentation removes exterior layers and isolates vehicle systems. Available. | Browser cutaway, body opacity, bracket isolation and stable fastener selection. Original procedural SUV, no Porsche assets. |
| https://www.apple.com/newsroom/2024/04/apple-vision-pro-brings-a-new-era-of-spatial-computing-to-business/ | Race Engineer connects spatial context, telemetry and video. Available. | One explicit UTC cursor for clip, scene and discrete tool readings. Show gaps rather than invent aligned samples. No headset. |
| https://newsroom.porsche.com/en/2024/innovation/porsche-mhp-shopfloor-training-apple-vision-pro-36011.html | Spatial shopfloor instructions support step by step understanding. Available. | Compare WI Step 6 requirement with visible synthetic author motion and separately unavailable model sequence evaluation. |
| https://www.nvidia.com/en-us/case-studies/bmw-group-develop/ | FactoryExplorer uses Omniverse and OpenUSD for collaborative planning. Available. | Plant to station to bracket navigation, with explicit browser rendering and illustrative geometry. No Omniverse or OpenUSD integration claimed. |
| https://blogs.nvidia.com/blog/factory-operations-fox-blueprint-ai-brain/ | FOX connects signals, records, specialist agents and work instructions. Available, dated 2026-05-31. | Separate evidence types and local specialist endpoints. Architectural reference only; FOX is not installed. |
| https://docs.nvidia.com/vss/ | Current documentation identifies VSS 3.3.0 and modular real time, downstream and offline workflows. Available. | Preserve existing local segmentation and retrieval pipeline. No blueprint migration or installed VSS claim. |
| https://docs.nvidia.com/vss/getting-started/quickstart | Current quickstart covers profiles, local or remote model endpoints and SBSA details. Available. | Preserve known local endpoints; do not copy a default cloud endpoint or change serving flags. |
| https://developer.nvidia.com/blog/?p=123017 | Resolves to VSS 3.3 technical article dated 2026-09-29. Available. | Modular adoption and bounded investigation. Published VSS efficiency figures are not our measurements. |
| https://threejs.org/docs/ | Browser WebGL scene, object hierarchy and camera APIs. Available. | Locally bundle pinned Three.js 0.180.0. Original code generated geometry. |
| https://www.hp.com/ar-es/workstations/ai-stations.html | Official HP page lists ZGX Fury with GB300 and coherent CPU/GPU memory. Available. | Why HP describes the actual local workload and measured endpoint/device state. Published maxima are not measured application bandwidth or a comparison against other platforms. |

The attempted HP URL https://www.hp.com/us-en/workstations/ai-station.html was unavailable to the research tool; the official regional page above was used instead.

## Current VSS requirements checked before deciding against migration

The 3.3 quickstart specifies Docker Engine `28.3.3 <= version < 29.5.0`, managed service profiles, access-controlled model artifacts, model configuration choices and a trusted isolated deployment. For GB300 and other ARM SBSA hosts, it specifies exporting `VSS_CONTAINER_TAG_SUFFIX=-sbsa` before Compose derives image names. It supports local and remote model configurations; some edge shared layouts are explicitly unmeasured in the documentation. The default skill path may use an external agent harness and does not imply a local LLM container. Those are requirements for that blueprint, not evidence this machine satisfies them.

This project already has pinned functioning loopback APIs and network-none model containers. Installing the whole blueprint would introduce additional services, model access requirements and migration risk without repairing the current vision authorization blocker. We did not install it, switch model families, acquire cloud services or alter Docker/OS/network configuration.

## Build tooling

Scoped Node 22.14.0 Linux ARM64 was downloaded from https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-arm64.tar.xz and verified against the official https://nodejs.org/dist/v22.14.0/SHASUMS256.txt before extraction under `.tools/`. It is build tooling, not a runtime network dependency. Locked npm dependencies and licenses are recorded in package-lock.json and ASSET_PROVENANCE.md. Models and serving configuration remain as inspected in BASELINE.md and config/models.json.
