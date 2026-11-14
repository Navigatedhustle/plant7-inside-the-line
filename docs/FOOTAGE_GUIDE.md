# Synthetic footage and later mock station ingest

The new bundled clip is **synthetic demonstration footage**, rendered from the actual original browser bracket geometry. It is not a real camera recording and does not validate factory vision accuracy. Four contact motions and fastener labels are manually authored, not detections. Their sidecar is never supplied as the answer to the VLM. The occluded variant intentionally obscures the joint and cannot establish a complete sequence.

The UI explicitly separates WI requirement 1,3,2,4; the authored demonstration motion; stored torque/angle measurements; and any future model observation. Vision is currently unavailable. A real local endpoint attempt was recorded with no caption or invented sequence. Pixel based sequence discrimination remains blocked until that endpoint can run. The telemetry and document investigation remains usable with this limit.

## Recreate the synthetic clip

Run the app and use:

```bash
cd /home/gb300/plant7-investigator
.venv/bin/python scripts/make_assembly_clip.py
.venv/bin/python scripts/make_occluded_clip.py
```

The authoring script hides presentation overlays before capturing the actual geometry. It emits the MP4 and explicit author metadata under data/video. Original render assets are also preserved under static/inside for offline startup. Source clock is 2026-11-10T14:42:38Z; telemetry source events for the example unit are seconds 41 through 44. This is authored alignment, not measured camera accuracy.

## Mock station filming checklist

1. Use the fictional unbranded Bracket B7 fixture or a safe physical mock. Obtain approval from participants and the location. Exclude real plant, supplier and personal data.
2. Mount the camera above and slightly to the side. Keep every fastener and socket contact visible throughout the complete cycle. Avoid hands, cables or fixture hardware occluding the socket.
3. Use at least 1080p and a stable 25 or 30 fps recording. Lock focus and exposure. Include enough pre and post cycle footage to establish all four visits.
4. Record a correct 1,3,2,4 sequence and a deliberate 1,2,3,4 counterexample on the safe mock. Record a separate occluded/incomplete example. The requirement is specific to this fictional component.
5. Record actual camera start UTC, unit ID and tool timestamps with a shared visible time reference. Document clock offset, uncertainty, dropped frames and any discontinuities. Never align by guessing.
6. Use synthetic or explicitly approved tool telemetry. Video cannot establish torque, calibration, preload or operator intent. Do not infer personnel blame from an ambiguous clip.
7. Preserve an original local MP4 and camera metadata. Keep human annotations separate from pixel evaluation prompts and results.

## Tested ingest path

Copy the approved mock MP4 into this project's `data/video` folder. The tool resolves symlinks, rejects paths outside that root, requires an MP4 no larger than 2 GiB, decodes actual pixels and validates line/station/timestamp metadata.

```bash
.venv/bin/python scripts/ingest_video.py mock_station.mp4 \
  --line 3 --station 40 --started-at 2026-11-10T14:42:38Z --validate-only
```

Validation was run on the bundled MP4: 960 by 700, 10 fps, 10.0 seconds. Actual existing segmentation was also run, producing local independently encoded chunks. No model output was substituted when vision was unavailable. After authorized local vision access is restored, remove `--validate-only` to run the preserved segment, pixel VLM, embedding and index workflow:

```bash
.venv/bin/python scripts/ingest_video.py mock_station.mp4 \
  --line 3 --station 40 --started-at 2026-11-10T14:42:38Z
```

Inspect the resulting observations against held out correct, incorrect and occluded pixels. Report successes, failures and uncertainty before accepting any automatic sequence finding. Do not use sidecar contact order, file names or generator captions as the answer key supplied to the VLM. Partial captions or a matching clip title do not pass sequence evaluation.

Before a customer demonstration that implies camera based sequence understanding, replace the old l3_s40 development placeholders with an approved filmed mock and complete this evaluation. The new synthetic clip may be used only with its persistent synthetic label and an explanation that it proves workflow presentation rather than real factory vision accuracy.

## Optional physical offline demonstration

Only an onsite presenter using a locally connected keyboard and display may rehearse cable removal. Warm the local models, open loopback URLs and verify the labeled source limits first. Remove the external network cable only from that onsite console, then run the local investigation and inspect/export evidence. Reconnect afterward. Do not perform this from SSH or Tailscale, do not change host networking, and do not describe remote tailnet viewing as evidence remaining inside the building. The implemented automated offline checks already preserve remote access and need no cable removal.
