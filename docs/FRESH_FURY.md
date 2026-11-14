# Plant 7 · Fresh Fury installation and launch

Version 1.1.0 · 14 November 2026 · Private owner-authorized handoff

This guide starts from a freshly provisioned HP ZGX Fury running Ubuntu 24.04 ARM64. The recorded walkthrough works without models or Docker. Live inference needs the compatible SM 10.3 GPU with at least 240000 MiB reported GPU memory, an operational OEM NVIDIA driver, Docker and the NVIDIA Container Toolkit. Other configurations are not certified by this release.

Repository: https://github.com/Navigatedhustle/plant7-inside-the-line
Release: https://github.com/Navigatedhustle/plant7-inside-the-line/releases/tag/v1.1.0

## 1. What to download

Download these release assets while signed in to GitHub as Navigatedhustle or another account granted repository access:

- `plant7-inside-the-line.tar.gz` — application, compiled browser scene, all synthetic data, original authored clips, captured run, source, tests, installer and notices.
- `plant7-python312-linux-arm64.tar.gz` — every pinned Python dependency wheel for Linux ARM64 / Python 3.12. This avoids package-index downloads during installation.
- `Plant7-Fresh-Fury-Guide.pdf` — this guide, printable with clickable links.
- `SHA256SUMS` — integrity hashes for all release downloads.
- `RELEASE_CONTENTS.json` — machine-readable asset inventory and pinned live model/image sources.

All application/media/data assets and offline Python wheels are supplied. Live model weights (~157 GB) and the serving image are acquired by the live installer from their pinned upstream sources. They are not email attachments or mirrored weights. Vision is unavailable and excluded. Driver/OS packages remain the target machine's prerequisites. An air-gapped live installation additionally needs transferred weights, verification records and a saved serving image; see section 8.

The private repository has no public download URL. The email includes the small application bundle and PDF; larger dependency assets are linked from the GitHub release. Keep the release files together in a folder such as `~/Plant7`.

## 2. Prepare the fresh operating system

Use the OEM-supported Ubuntu image and NVIDIA driver for this Fury. Do not replace a working OEM driver to run this demo. First, open Terminal and check:

```bash
uname -m
python3 --version
nvidia-smi
nvidia-smi --query-gpu=compute_cap,memory.total --format=csv,noheader,nounits
```

For the pinned live stack, expect `aarch64`, Python `3.12.x`, compute capability `10.3`, and GPU memory at least `240000` MiB. If `nvidia-smi` fails, restore the OEM-supported driver stack before live setup; the recording is still usable without it. The source host used Ubuntu 24.04.5; no specific driver version is installed or changed by the demo.

For a fresh Ubuntu 24.04 installation, install the ordinary utilities used below. Run these commands on the receiving Fury, not on a machine presenting another demo:

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv ca-certificates curl gnupg git gh xdg-utils
mkdir -p "$HOME/Plant7"
cd "$HOME/Plant7"
```

## 3. Get and verify the release

In a browser, sign in to GitHub, open the release link and download the assets in section 1. Alternatively, the GitHub CLI supports private release downloads:

```bash
gh auth login --hostname github.com --web --git-protocol https
gh release download v1.1.0 --repo Navigatedhustle/plant7-inside-the-line --dir "$HOME/Plant7"
cd "$HOME/Plant7"
sha256sum -c SHA256SUMS
tar -xzf plant7-inside-the-line.tar.gz
tar -xzf plant7-python312-linux-arm64.tar.gz
cd plant7-inside-the-line
```

Every checksum should say `OK`. If a file was not downloaded, its check will say missing; download it before continuing. The dependency archive expands to `plant7-wheelhouse/` beside the application folder. Never copy `.venv`, `.env`, `runtime`, browser credentials or machine-specific GPU bindings from the source machine. This installation creates its own state and credentials.

## 4. Fastest successful launch: recorded walkthrough

From the extracted application folder:

```bash
./scripts/install.sh --wheelhouse ../plant7-wheelhouse
./scripts/open_desktop.sh
./scripts/healthcheck.sh
```

The installation is local to the project directory and does not need sudo. A generated application-menu entry and `Plant 7.desktop` point to the actual folder. If the desktop asks you to trust a new launcher, use the terminal launch command instead. Open `http://127.0.0.1:8097/` on that Fury if the browser does not open automatically.

Expected result: a clearly labelled recorded walkthrough, a working health check and five steps controlled by one blue button. No model request or Docker operation is made in recorded mode. The recorded token counts and timings describe the saved source run, not live work on the receiving Fury.

The installation and full browser journey were exercised in a separate folder with spaces on the source Fury. This is a clean installation test, not certification of a second physical machine.

## 5a. Prepare Docker for live inference

Skip this section when `docker info` succeeds as your normal user and `docker info --format '{{json .Runtimes}}'` already includes `nvidia`. Otherwise, install Docker using its official Ubuntu instructions [1], and NVIDIA Container Toolkit using its official apt instructions [2]. These are receiving-machine administrator steps; the application installer does not perform them.

For a pristine Ubuntu host with no Docker engine, the Docker repository can be configured as follows. Do not remove an existing engine or restart workloads merely to follow this guide; ask that machine's administrator if Docker is already managed.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
P7_ARCH=$(dpkg --print-architecture)
. /etc/os-release
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: ${P7_ARCH}
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo groupadd --force docker
sudo usermod -aG docker "$USER"
```

Sign out of the desktop completely and sign back in before continuing. Docker group membership gives privileged access to the machine [3]. Keep the demo installer running as the normal desktop user, not under sudo.

## 5b. Enable NVIDIA GPU container access

For an absent NVIDIA Container Toolkit, configure its signed package source and install the documented pinned toolkit version:

```bash
P7_NVIDIA_KEY=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
P7_NVIDIA_LIST=/etc/apt/sources.list.d/nvidia-container-toolkit.list
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o "$P7_NVIDIA_KEY"
curl -fsSL \
  https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed "s#deb https://#deb [signed-by=${P7_NVIDIA_KEY}] https://#g" | \
  sudo tee "$P7_NVIDIA_LIST"
sudo apt-get update
P7_TOOLKIT_VERSION=1.20.1-1
sudo apt-get install -y \
  nvidia-container-toolkit="${P7_TOOLKIT_VERSION}" \
  nvidia-container-toolkit-base="${P7_TOOLKIT_VERSION}" \
  libnvidia-container-tools="${P7_TOOLKIT_VERSION}" \
  libnvidia-container1="${P7_TOOLKIT_VERSION}"
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker info --format '{{json .Runtimes}}'
```

NVIDIA runtime configuration edits Docker's daemon configuration, and restarting Docker can interrupt containers. Perform this once on the fresh receiving system before starting demo workloads. If this host uses rootless Docker, use NVIDIA's separate rootless procedure [2] instead of the rootful configuration commands above. If the pinned toolkit packages are no longer available, follow the current official installation guide; do not change the application's pinned model or serving-image versions as a workaround.

## 6. Install the live stack

First stop a recorded app if it is running, then run the preflight from this application folder:

```bash
./scripts/stop_all.sh
python3 scripts/doctor.py --pre-install
```

All preflight checks must be READY. Have a stable network connection and at least 300 GB free as a practical starting allowance for ~157 GB of weights, the serving image, dependencies and compilation caches. Actual image/cache space varies; model downloads enforce a 20 GiB remaining-disk reserve. Confirm the working GPU is otherwise available to this demo before loading its resident models.

The Python wheelhouse avoids dependency downloads; upstream live assets still require internet:

```bash
./scripts/install.sh --mode live --download-models --wheelhouse ../plant7-wheelhouse
./scripts/start_all.sh
./scripts/healthcheck.sh
./scripts/open_desktop.sh
```

This downloads only the four accessible pinned roles: brain, SQL worker, embedding and reranking. Exact repositories, revisions, weight byte totals and the serving image digest are in `config/models.json` and the release inventory. Preserve upstream terms and model notices. If an upstream source requires credentials or acceptance, complete that provider's process locally and rerun; do not send credentials by email.

First live startup can take several minutes while weights load and kernels compile. Wait for `Ready: http://127.0.0.1:8097/`. Progress is visible in the terminal and `logs/launch.log`; never close the window because startup appears quiet. A required live role that fails is reported, not replaced by a successful-looking recording.

Expected health: application and working slice READY; brain/worker/embed/rerank READY. Vision remains UNAVAILABLE and the full multimodal gate remains unaccepted. That known vision limitation does not fail the working telemetry/document slice.

## 7. Present and verify

Use the blue button or right arrow/Space through: line signal, joint, evidence playback, exact unit scope, then decision and token economics. There is no presenter sign-in or control panel. Optional source, passport, explicit simulation and export clicks add depth. Refresh resumes the current browser session. The final button resets the walkthrough.

Before the audience arrives, run a live investigation and verify the result reaches Evidence ready. Confirm the live/recorded badge, synthetic-footage notice, 539-unit example scope and visible vision limitation. At the last step, confirm token counts are numeric and that changing volume/rates updates the illustrative token charge. Hardware, electricity, operations, embedding/reranking charges and model equivalence are excluded; this is not validated savings or a provider quote.

Use the actual viewing laptop/projector for a rehearsal. All five desktop screens fit tested viewports from 1280x720 to 1920x1080. Physical second-Fury and projector performance remain to be checked onsite. The browser renders the 3D scene; if WebGL fails, functional 2D source inspection remains available.

For a read-only wall or mobile link, open What runs on Fury. Remote LAN/tailnet access uses the receiving machine's existing authorized network address. No public tunnel, firewall rule or source machine Tailscale identity is created or copied. Remote viewers receive evidence.

## 8. Air-gapped live transfer

The release's application and wheelhouse supply offline software installation. An entirely offline live Fury additionally needs a separate model/image transfer from an authorized source: only `models/brain`, `models/worker`, `models/embed`, `models/rerank` and the matching `logs/download-ROLE.json` records. Exclude the unused challenger and absent vision role. Do not copy source runtime state or credentials.

On the source, save the exact configured image to transfer media:

```bash
P7_IMAGE=$(python3 -c 'import json; print(json.load(open("config/models.json"))["image"])')
docker save "$P7_IMAGE" -o plant7-serving-image.tar
```

Copy that image archive and the required checkpoint folders/records on suitable storage. Check transfer hashes, retain the upstream notices and comply with the applicable redistribution terms. On the receiving machine, load the image first and point the installer at the transferred project folder:

```bash
docker load -i /path/to/plant7-serving-image.tar
./scripts/install.sh --mode live --model-source /path/to/transferred-plant7 --wheelhouse ../plant7-wheelhouse
./scripts/start_all.sh
```

The installer copies the required weights into this installation and checks revision records and byte totals. This is not a full cryptographic weight audit. The ~157 GB checkpoints and serving image are not part of the GitHub/email distribution in this release; the download installer is the standard fresh-machine route.

## 9. Recover without disturbing other projects

`./scripts/healthcheck.sh` checks the working installed slice. `.venv/bin/python scripts/doctor.py --live` checks GPU, Docker, image and weights. `.venv/bin/python scripts/restart_app.py` restarts only the app. `./scripts/stop_all.sh` stops this installation's verified processes/containers, preserving weights and source records. Never delete global caches, kill unrelated listeners or replace the driver to resolve an app error.

If 8097 is occupied, stop the conflicting app yourself or launch a recorded copy on another port: `P7_PORT=18097 ./scripts/start_all.sh --mode replay --open`; use the same environment variable with its health check. Live model API ports remain pinned to 8001-8005 and 8013, so run one live Plant 7 stack per host.

An incomplete investigation retains its failure. Retry or explicitly select the labelled recording. Repeated launches are serialized. Retried submissions reuse an idempotency ID, and recorded recovery does not consume a full live queue slot. Reinstalling preserves generated credentials and sessions. If moving the folder, rerun installation to recreate the virtual environment and launcher paths.

For escalation, share the failing check and relevant log excerpt, the release tag, Ubuntu/architecture/GPU information and whether the badge says LIVE or RECORDED. Exclude `.env`, `runtime/inside/presenter.key`, browser session keys and other credentials.

## 10. Validation, notices and sources

The source build passed 49 behavioral tests, a real local and Tailscale browser journey, four desktop sizes, source/passport/simulation/export checks, explicit failure/replay recovery, no-external-browser-request checks, clean offline-wheel installation, repeated/concurrent launch, stop/restart and headless launch. Recorded lifecycle checks made no Docker/group command calls. Live readiness on the source Fury is verified; a second physical Fury's hardware/OS provisioning is not certified by these results.

This is synthetic operational evidence and authored footage with real local inference in live mode. No production MES/PLC/shipment action is performed. Vision, physical cause confirmation and full multimodal acceptance remain open. The owner's requested private GitHub/email delivery does not assert completion of the existing HP IP Marketing Review or grant a new open-source licence. Original notices are retained in `docs/LICENSES_FOR_IP_REVIEW.md`, `docs/ASSET_PROVENANCE.md` and `static/inside/licenses/`.

Official prerequisite references, checked 14 November 2026:

[1] Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/

[2] NVIDIA Container Toolkit installation and Docker configuration: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

[3] Docker post-install user access: https://docs.docker.com/engine/install/linux-postinstall/
