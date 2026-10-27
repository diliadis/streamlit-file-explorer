# Running on a SLURM cluster

The explorer reads paths on the machine running Streamlit. On a cluster, start the app in an allocation and configure roots that are mounted on that compute node. A local app cannot browse an arbitrary cluster path unless that path is mounted locally or the app itself runs remotely.

This guide supplies a deployment pattern, not a tested configuration for your particular cluster. Partition names, SSH access to compute nodes, authentication, and interactive-app policies vary by site.

## Prepare the environment

Build the wheel on a development machine, including its frontend assets (see the main README). Copy the wheel and your app to shared storage on the cluster using your usual transfer method. Install the wheel in a cluster Python environment:

```bash
python3 -m venv /shared/path/explorer-env
/shared/path/explorer-env/bin/python -m pip install /shared/path/streamlit_file_explorer-0.1.0-py3-none-any.whl
```

For an offline cluster, prepare the dependencies in an approved wheelhouse for the cluster's Python version and platform, and install using `--no-index --find-links /path/to/wheelhouse`. Compiled dependencies must match the target platform. Node.js is only needed where you build the component assets.

The demo can be copied with `streamlit_app.py`, `.streamlit/config.toml`, and `examples/data/`. With `FILE_EXPLORER_ROOTS` set, the demo uses those configured roots instead of sample data.

## Submit an allocation

Set the following variables in the submission shell, using real cluster paths:

```bash
export EXPLORER_APP_DIR=/shared/path/streamlit-file-explorer
export EXPLORER_PYTHON=/shared/path/explorer-env/bin/python
export FILE_EXPLORER_ROOTS='{"Project":"/shared/project/data","Scratch":"/scratch/my-user"}'
export EXPLORER_PORT=8517
sbatch --partition=YOUR_PARTITION examples/launch_slurm.sbatch
```

Add your site's required account or QoS arguments. The supplied script requests one task, one CPU, 2 GiB memory, and two hours. Adapt these to the surrounding app. The log `file-explorer-JOBID.out` reports the hostname and port. The job may queue before the server starts. SLURM does not transfer app files for you; they must be available on the allocated node. See the [official sbatch documentation](https://slurm.schedmd.com/sbatch.html).

The script binds to `127.0.0.1`. On a shared compute node, loopback is reachable by other processes/users on that node: it is **not user authentication**. For sensitive data, use your site's authenticated interactive-app service or an authenticated deployment approved by your administrator. Configure only roots you intend that app's users to see. A dedicated allocation alone is not a substitute for application access policy.

## Connect from your laptop

If your site permits SSH to allocated compute nodes through a login node, open a tunnel from your laptop, replacing all placeholders:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -J YOUR_USER@LOGIN_HOST \
  -L 8517:127.0.0.1:8517 \
  YOUR_USER@COMPUTE_HOST
```

Then visit `http://127.0.0.1:8517`. This command terminates SSH on the compute node; a tunnel ending only on the login node will not reach the compute node's loopback listener. Keep the tunnel and allocation running while using the app.

If compute-node SSH is prohibited, use the site's supported portal (for example Open OnDemand) or ask its administrators for the approved proxy configuration. Do not disable Streamlit's CORS/XSRF protections or expose an unauthenticated listener to work around connectivity. A portal may require an administrator-defined base URL path and websocket proxy configuration.

Stop the allocation when finished with `scancel JOBID`. Do not run a persistent web app on a login node unless your site's policy explicitly permits it.

## Storage and permissions

- Shared project storage, home directories, and scratch must actually be mounted on the allocated host. Node-local scratch may disappear when the job ends.
- Filesystem access uses the job's OS account. A shared service running for several browser users sees the service account's permissions.
- Child symlinks are deliberately unavailable. Configure their destination as a separate root if it should be browsable.
- Large directories produce bounded, possibly partial scans. Tune `max_entries`, `page_size`, and `cache_ttl` for your storage metadata performance.
- The listing cache is per session. No file listing or file content is placed in a process-global Streamlit cache.
- Refresh observes new jobs' output; there is no background filesystem polling.
- A slow or disconnected network filesystem may block a synchronous read. Monitor the cluster's storage health if the UI stays in its loading state.
