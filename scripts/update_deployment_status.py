#!/usr/bin/env python3
import argparse, os, re
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone


DEPLOYMENT_FILE = "deployment-status.md"

# component_id, DEPLOY_* env, VEDA_*_GIT_REF env, display name in MD, repo URL
COMPONENTS = [
    ("auth", "DEPLOY_AUTH", "VEDA_AUTH_GIT_REF", "AUTH", "https://github.com/ieee-grss-veda/grss-veda-keycloak"),
    ("backend", "DEPLOY_BACKEND", "VEDA_BACKEND_GIT_REF", "BACKEND", "https://github.com/NASA-IMPACT/veda-backend"),
    ("features_api", "DEPLOY_FEATURES_API", "VEDA_FEATURES_API_GIT_REF", "FEATURES_API", "https://github.com/NASA-IMPACT/veda-features-api-cdk"),
    ("routes", "DEPLOY_ROUTES", "VEDA_ROUTES_GIT_REF", "ROUTES", "https://github.com/NASA-IMPACT/veda-routes"),
    ("sm2a", "DEPLOY_SM2A", "VEDA_SM2A_DATA_AIRFLOW_GIT_REF", "SM2A", "https://github.com/NASA-IMPACT/veda-sm2a"),
    ("monitoring", "DEPLOY_MONITORING", "VEDA_MONITORING_GIT_REF", "MONITORING", "https://github.com/NASA-IMPACT/veda-monitoring"),
    ("titiler_multidim", "DEPLOY_TITILER_MULTIDIM", "VEDA_TITILER_MULTIDIM_GIT_REF", "TITILER_MULTIDIM", "https://github.com/developmentseed/titiler-multidim"),
    ("s3_dr", "DEPLOY_S3_DISASTER_RECOVERY", "VEDA_S3_DISASTER_RECOVERY_GIT_REF", "S3_DR", "https://github.com/NASA-IMPACT/s3-disaster-recovery"),
    ("titiler_cmr", "DEPLOY_TITILER_CMR", "VEDA_TITILER_CMR_GIT_REF", "TITILER_CMR", "https://github.com/developmentseed/titiler-cmr"),
]

ROW_RE = re.compile(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$')
ENV_RE = re.compile(r'^##\s+(.+)\s*$')

def load_state(path: str) -> dict:
    """Parse existing markdown into { env: { DISPLAY_NAME: ref } }."""
    state = defaultdict(dict)
    if not os.path.exists(path):
        return state

    current_env = None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            m_env = ENV_RE.match(line)
            if m_env:
                current_env = m_env.group(1).strip()
                continue

            if not current_env or not line.startswith("|"):
                continue

            m_row = ROW_RE.match(line)
            if not m_row:
                continue

            c1 = m_row.group(1).strip()
            c2 = m_row.group(2).strip()
            c3 = m_row.group(3).strip()

            if c1.lower() == "component":
                continue
            if set(c1) == {"-"} and set(c2) == {"-"}:
                continue

            state[current_env][c1] = (c2, c3)
    return state

def make_ref_link(repo_url: str, ref: str) -> str:
    if not ref:
        return ""
    return f"[{ref}]({repo_url}/tree/{ref})"

def write_state(path: str, state: dict):
    ordered_envs = sorted(state.keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Deployment Status\n\nIf a component or environment is not listed, it has not yet been deployed through veda-deploy.\n\n")
        for env in ordered_envs:
            f.write(f"## {env}\n")
            f.write("| Component | Git Ref | Updated (UTC) |\n")
            f.write("|-----------|---------|---------------|\n")
            for _, _, _, disp, repo_url in COMPONENTS:
                entry = state[env].get(disp, ("",""))
                print(f"Processing {disp} for {env}: {entry}")
                ref, upd = entry
                ref_link = ref if ref.startswith("[") else make_ref_link(repo_url, ref)
                f.write(f"| {disp} | {ref_link} | {upd} |\n")
            f.write("\n")

def collect_updates_from_env() -> dict:
    """Return { DISPLAY_NAME: ref } for components that should be updated."""
    updates = {}
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    for _, deploy_env, ref_env, display, _ in COMPONENTS:
        print(f"Checking {display} for environment variables: {deploy_env}, {ref_env}")
        deploy_flag = os.getenv(deploy_env, "")
        ref_val = os.getenv(ref_env, "")
        print(f"  {deploy_env} = {deploy_flag}, {ref_env} = {ref_val}")
        if deploy_flag == "true" and ref_val.strip(): # this is weird but GHA won't let the flag be cast as a boolean
            updates[display] = (ref_val.strip(), ts)
    return updates

def main():
    print("Updating deployment status...")
    ap = argparse.ArgumentParser(description="Update deployment-status.md with current refs.")
    ap.add_argument("--env", required=True, help="Target environment name (must match your GH environment)")
    ap.add_argument("--file", default=DEPLOYMENT_FILE, help="Path to deployment status markdown")
    args = ap.parse_args()

    state = load_state(args.file)
    print(f"Loaded existing state for {args.env}: {state.get(args.env, {})}")
    # Ensure env exists in state even if empty
    _ = state[args.env]

    updates = collect_updates_from_env()
    print(f"Collected updates: {updates}")
    if not updates:
        # Nothing to do; write existing state back unchanged (no-op)
        write_state(args.file, state)
        return

    # Apply updates for selected components only
    for display, ref in updates.items():
        state[args.env][display] = ref

    write_state(args.file, state)

if __name__ == "__main__":
    print("Starting deployment status update script...")
    main()