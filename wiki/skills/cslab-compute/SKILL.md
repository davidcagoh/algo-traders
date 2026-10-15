---
name: cslab-compute
description: Use the U of T MScAC CSLab Slurm cluster for compute-heavy work while keeping all files and activity inside David's home and workspace directories.
---

# U of T MScAC CSLab compute

Use this guide when planning or running jobs on the CSLab cluster. It is also
the working reference for assessing whether a local workload should move to a
CSLab GPU. Remote access is currently unverified until the user enables VPN.

## Scope and safe paths

- Use only David's own home and workspace directories on the cluster. The
  resource note currently identifies the workspace root as
  `/w/20251/daveed`; confirm the current allocation path after connecting.
- Keep source, manifests, bounded datasets, logs, checkpoints, and final results
  under a David-owned workspace/project directory. Keep model and framework
  caches under `/w/20251/daveed` or David's home directory.
- Do not inspect, read, write, or run files from another user's home or project.
- The home filesystem has a sharp 10 GB limit and is intended for documents,
  small files, and email. Put environments, package/build caches, datasets, and
  model weights in David's `/w/20251/daveed` workspace instead.
- The `/w/20251` and `/w/20252` work filesystems are shared among students and
  will be deleted shortly after graduation. Keep only needed files; remove
  large files after confirming they are no longer needed, and retain important
  results in an approved durable location before workspace expiry.
- Do not use shared `/scratch/scratch-space` for authoritative data or results;
  it is temporary and expires. Avoid it entirely when the task requires all
  activity to stay in David-owned directories.
- Work directories are world-readable by default. Start new runs with a
  restrictive umask and private project permissions (for example `umask 077`,
  `mkdir -m 700 -p /w/20251/daveed/algo-traders`, and files mode 600). Check
  permissions before placing snapshots, logs, checkpoints, or credentials
  there. Do not change permissions on a shared parent directory.
- Never put private data in `public_html`: everything there is published, and
  guessed or old-looking URLs are not a privacy control.
- Do not copy credentials into scripts, job output, manifests, or repository
  files. Use protected environment variables or an approved cluster secret
  mechanism. Do not print secrets for debugging.
- Do not connect until the user has enabled the required VPN. No cluster
  connectivity or current queue status has been verified in this session.

## Accounts, hosts, and discover resources

CSLab research computing and the instructional teaching labs are separate
facilities and accounts. Use David's CSLab account for research compute; do
not assume a similarly named teach.cs account is the same account. The CS
research login `cs.toronto.edu` is an alias for `apps0.cs.toronto.edu`.

`apps0` and `apps1` are for interactive, lightweight activity such as editing,
email, and small checks. Move heavy or long-running CPU/GPU work to compute
servers or Slurm. The linked resource note for this repo says the reliable
direct-compute route is two SSH hops:

```bash
ssh uoft
ssh comps0
```

Run the second command from the first remote login. Do not assume a one-command
ProxyJump alias exists. Host specifications and Slurm rules can change; check
the official [Linux compute host guide](https://support.cs.toronto.edu/systems/linuxcompute.html)
and [Slurm resource guide](https://support.cs.toronto.edu/systems/slurmresource.html)
after access is available. Once connected, inspect only your own account and
available scheduler information:

```bash
slurm_report -g
sinfo -p gpunodes -o "%20N %10m %25f %20G"
squeue -u "$USER"
```

The local resource note lists example `gpunodes` hardware: RTX 4090 (~24.5 GB),
A4500 (~20.5 GB), A4000 (~16.1 GB), A2000 (~12.3 GB), A6000 (~49.1 GB), and
RTX 2070/2080 (~8 GB). Treat this as a dated inventory, not a promise of
availability. Query the scheduler before choosing a GPU and confirm the
allocated node with `nvidia-smi` inside the job.

## Set up an isolated run

Use a project-specific environment and caches in your workspace. Do not reuse
another project's virtual environment. For the repo's TimesFM work, a suitable
layout after confirming the workspace path is:

```text
/w/20251/daveed/algo-traders/       source and run artifacts
/w/20251/daveed/algo-traders/.venv  project environment
/w/20251/daveed/hf_cache/           Hugging Face model cache
/w/20251/daveed/torch_cache/        PyTorch cache
```

Home directories are private by default; workspace directories are readable by
others by default. Keep new research artifacts private unless sharing is an
explicit goal. Avoid `public_html` for project output. Check your own disk use
without inspecting other students' files or shared usage reports.

Before an expensive run, verify the interpreter, package imports, accelerator,
available memory, free space, and model cache location on the allocated node.
Record package/model revisions and a fresh run ID in the workspace. Probe one
small representative input first; capture wall time and peak host/device
memory. Scale only after that probe succeeds.

## Slurm jobs

Adapt every resource request to the selected model and live node. The local
resource note says
the maximum job duration is five days and that GPU time and allocated memory
affect fair-share priority. Request only what the measured job needs. Keep
stdout/stderr in a logs directory inside your project workspace.

```bash
#!/bin/bash
#SBATCH --job-name=timesfm-eval
#SBATCH --partition=gpunodes
#SBATCH -c 4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH -t 1-00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail
umask 077
cd /w/20251/daveed/algo-traders
source .venv/bin/activate
export HF_HOME=/w/20251/daveed/hf_cache
export TORCH_HOME=/w/20251/daveed/torch_cache
mkdir -p logs
nvidia-smi
forecast-evaluation/.venv/bin/timesfm-eval evaluate
```

Create the workspace log directory before submission if required by Slurm.
Submit and monitor only your jobs:

```bash
sbatch job.slurm
squeue -u "$USER"
tail -f logs/timesfm-eval_<jobid>.out
sacct --format JobID,Partition,ExitCode,NodeList,JobName,State,Elapsed
```

Cancel only a job ID you own and intend to stop: `scancel <jobid>`.

## TimesFM 3.0 resource assessment

The repository's pinned model is TimesFM 3.0.2 with a 330M-parameter
checkpoint. The local preflight currently reports 16 GB total RAM, about
4.6 GB available, 13.1 GB free in the Hugging Face cache volume, CPU mode, and
no installed `timesfm` package. The local guide recommends 8 GB available RAM
for this model; it warns below that level. A local run may still work with a
small batch, but is not a dependable choice for the full rolling-origin job.

The listed CSLab GPUs all have more VRAM than the local available-memory
headroom, but this alone does not establish fit or speed. Package compatibility,
CUDA/PyTorch versions, host memory, checkpoint download access, and real peak
memory must be verified on an allocated node. Start with one origin and batch
size 1, record peak memory and time, then decide whether to run the full pinned
evaluation. Do not run a large batch on an unmeasured assumption.

## Account help and workstation boundaries

The [MScAC Tech Tips directory](https://mscac.cs.toronto.edu/techtips/) is
authenticated. Its visible notice says to use the CSLab account name without
an `@` suffix and the CSLab password; if password authentication is unclear,
try that password with SSH, and contact the assigned POC if it is forgotten.

The Tech Tips also describe desktop computers in the MScAC room. Their home
directories are local and unbacked-up, they are not CSLab compute nodes, and
users should leave them on, avoid administrative operations/reboots, and ask
the POC for software installation. They are not suitable for durable project
data or heavy runs.

## Verified Tech Tips summary

The following seven tips were read from the authenticated browser on
2026-10-14. These are concise summaries; verify time-sensitive paths and
policies against the linked official pages before relying on them.

1. **Accounts and host roles (Tip 1).** CSLab is research computing; teaching
   labs are a separate facility/account. `cs.toronto.edu` is an alias for
   `apps0`. Apps hosts are for low-CPU interactive work; substantial or
   long-running work belongs on compute hosts or Slurm. Teach.cs account names
   may resemble UTORids but are separate. SGS mail may go to the U of T mailbox.
2. **Room equipment (Tip 2).** Monitors/keyboards/mice requested for the MScAC
   room stay there unless permission is granted. Printer-adjacent desktops
   (`gyre` and `gimble`) are locally managed, have local unbacked-up home
   directories, and are for quick tasks. Leave them on; do not perform admin
   operations, reboot unnecessarily, or install software yourself.
3. **Storage (Tip 3).** Home has a 10 GB limit and is intended for documents,
   small files, and email. Large installs, caches, datasets, and model weights
   belong in the user's `/w/<term>/daveed` directory. `/w` capacity is finite
   and shared; work filesystems are deleted shortly after graduation. The tip
   exposes a shared usage report, but this workflow must not inspect it because
   work is restricted to David's home and workspace paths.
4. **Heavy compute (Tip 4).** Use compute hosts or Slurm for expensive work;
   apps hosts are not compute nodes. Some compute hosts allow SSH and Slurm
   nodes provide exclusive allocations, including GPUs. Slurm jobs cannot use
   X-Windows. Put large files (including pip installs and build outputs) on a
   `/w` filesystem, not home.
5. **Publishing (Tip 5).** Files under `public_html` are public static content.
   Do not put private datasets, forecasts, model artifacts, or logs there.
   Guessable URL suffixes do not provide access control.
6. **Command line and sessions (Tip 6).** `screen` can detach and resume an
   interactive session, but reattachment must happen on the same host. Use it
   for interactive continuity only; it does not allocate compute resources or
   replace Slurm for heavy jobs. The tip links introductory shell material.
7. **File sharing and permissions (Tip 7).** Home is private by default;
   `/w` is world-readable by default. File names are not secrets. Keep this
   workflow's directories and files private unless sharing is explicitly
   intended; do not loosen home-directory permissions or alter shared-parent
   permissions to make a project work.

## Source notes

- [Local CSLab resource note](../../../compute-resources/using-uoft-cslab-compute.md)
- [Archived Tech Tips text copies](../../../compute-resources/techtips/README.md)
- [MScAC Tech Tips directory](https://mscac.cs.toronto.edu/techtips/)
- [Tech Tip 1: accounts and computers](https://mscac.cs.toronto.edu/techtips/techtip01.txt)
- [Tech Tip 2: MScAC space equipment](https://mscac.cs.toronto.edu/techtips/techtip02.txt)
- [Tech Tip 3: disk space](https://mscac.cs.toronto.edu/techtips/techtip03.txt)
- [Tech Tip 4: heavy computation and GPUs](https://mscac.cs.toronto.edu/techtips/techtip04.txt)
- [Tech Tip 5: publishing web pages](https://mscac.cs.toronto.edu/techtips/techtip05.txt)
- [Tech Tip 6: command line and screen](https://mscac.cs.toronto.edu/techtips/techtip06.txt)
- [Tech Tip 7: file sharing and permissions](https://mscac.cs.toronto.edu/techtips/techtip07.txt)
- [TimesFM 3.0 repo notes](../timesfm-forecasting/references/timesfm3.md)
- [TimesFM resource preflight](../timesfm-forecasting/references/system_requirements.md)
