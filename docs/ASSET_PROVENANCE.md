# Asset and dependency provenance

Accessed and recorded 2026-11-14. No automaker assets, CAD, logos, footage, textures, external fonts or remotely hosted runtime assets were acquired. All new geometry is original procedural code. The HP name is plain text, not an invented logo; color tokens are proposed presentation tokens and not verified HP brand compliance.

| Item | Source URL | License / attribution | Modification | Local path |
| --- | --- | --- | --- | --- |
| Factory, generic SUV, fixture, bracket, fasteners, robots | Original project authoring, no external source | Original demo code; no third party visual attribution | Procedural scene hierarchy, replaceable independent geometry module | frontend/geometry.ts |
| 2D fallback | Original inline SVG code | Original demo code | Generic functional fastener illustration | frontend/main.ts |
| Three.js 0.180.0 and examples OrbitControls/RoundedBoxGeometry | https://www.npmjs.com/package/three/v/0.180.0 and https://github.com/mrdoob/three.js/tree/r180 | MIT, Three.js authors; full notice retained | Bundled locally with esbuild; geometry not downloaded | node_modules/three; static/inside/scene-*.js; static/inside/licenses/three.txt |
| uPlot 1.6.32 | https://www.npmjs.com/package/uplot/v/1.6.32 and https://github.com/leeoniya/uPlot | MIT, Leon Sorokin; full notice retained | Local bundle and copied CSS | static/inside/app.js, uplot.css, licenses/uplot.txt |
| System typography | Browser/OS system Arial or Helvetica fallback | Existing system installation; no redistributed font file | No font requests or runtime dependency | static/inside/app.css |
| Synthetic assembly MP4, 960 by 700, 10 fps, 10 seconds | Actual browser rendering of original geometry | Original synthetic demonstration; no camera footage, people or external recordings | Labeled author animation and clock; no model detections | static/inside/assembly.mp4; data/video/inside-line.mp4; scripts/make_assembly_clip.py |
| Deliberately occluded synthetic MP4 | Original assembly MP4 above | Original synthetic demonstration | Authored occlusion for inconclusive-source dataset, no model annotation | static/inside/assembly-occluded.mp4; scripts/make_occluded_clip.py |
| Clip metadata | Authored source clock and synthetic MES | Original synthetic fixture | Explicit manual labels; excluded from VLM answer inputs | static/inside/assembly.json; data/video/inside-line.json |
| Existing procedural placeholder clips | Original scripts/generate_data.py | Original development fixtures | Preserved; not described as recordings | data/video/l3_s40_*.mp4 |
| Screenshot and short walkthrough captures | Actual local Playwright browser | Original application capture | Captured at documented viewports; no compositing into evidence | docs/captures/*.png and walkthrough.webm |
| Node 22.14.0 Linux ARM64 | https://nodejs.org/dist/v22.14.0/ | Node.js MIT plus bundled third party notices in distribution LICENSE | Official SHA256 verified, scoped build tool only | .tools/node-v22.14.0-linux-arm64/LICENSE |
| TypeScript 5.9.3 | https://www.npmjs.com/package/typescript/v/5.9.3 | Apache 2.0 | Build tooling only | node_modules/typescript/LICENSE.txt; package-lock.json |
| esbuild 0.25.11 | https://www.npmjs.com/package/esbuild/v/0.25.11 | MIT | Build tooling only | node_modules/esbuild/LICENSE.md; package-lock.json |
| @types/three 0.180.0 and transitive build types | https://www.npmjs.com/package/@types/three/v/0.180.0 | MIT; individual package notices | Type checking only, no new visual assets | node_modules/@types/three/LICENSE; package-lock.json |

Model weights, Python packages and the existing vLLM image were not upgraded or redownloaded. Their prior inventories remain in MODELS.md, LICENSES_FOR_IP_REVIEW.md and the checked in Python/container license inventories. This record is provenance, not external publication approval. Prior HP IP Marketing Review remains pending; nothing was pushed or published.

## Guided handoff additions

The one-button flow and token economics are code-rendered UI. No new imagery, footage, weights or model configurations were generated or substituted. The bootstrap pip 26.3 wheel is copied from the project’s existing downloaded bootstrap cache; its license files remain inside the wheel. Release packages exclude development-machine GPU bindings, environment credentials, runtime sessions and model weights. Python dependencies are pinned in requirements.lock and subject to the existing inventory/review. A local source bundle is not publication or endorsement approval.
