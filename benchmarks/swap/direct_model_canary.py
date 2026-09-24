# What: import argument parsing; why: private run inputs must be explicit and validated.
import argparse

# What: import dynamic module support; why: the exact reviewed router canary should be reused.
import importlib.util

# What: import path handling; why: source and artifact locations need safe joins.
from pathlib import Path

# What: create the parser; why: malformed operator input must fail before inference.
parser = argparse.ArgumentParser()
# What: require exact source; why: no installed copy may shadow the detached revision.
parser.add_argument("--source", required=True)
# What: require numeric loopback port; why: the canary must target the owned engine.
parser.add_argument("--port", required=True, type=int)
# What: require public model alias; why: requests must not leak private paths.
parser.add_argument("--model", required=True)
# What: require private artifact directory; why: raw responses stay local.
parser.add_argument("--artifacts", required=True)
# What: parse inputs; why: validated values drive all later operations.
args = parser.parse_args()
# What: resolve the reviewed qualifier; why: protocol parsing must match the router campaign.
module_path = Path(args.source) / "benchmarks/swap/qualify_native_router.py"
# What: create an import specification; why: exact source can be loaded without package ambiguity.
spec = importlib.util.spec_from_file_location("lan215_direct_qualifier", module_path)
# What: create an isolated module; why: global qualifier state must not leak between runs.
module = importlib.util.module_from_spec(spec)
# What: execute the module; why: its reviewed canary must be callable below.
spec.loader.exec_module(module)
# What: construct loopback origin; why: requests must never leave the host.
base = f"http://127.0.0.1:{args.port}"
# What: resolve private evidence storage; why: outputs need safe path operations.
artifacts = Path(args.artifacts)
# What: repeat twice; why: qualification requires one cold-post-load and one warm completion.
for index in range(2):
    # What: execute the reviewed direct canary; why: malformed streaming or wrong arithmetic fails closed.
    raw, row = module.canary(base, args.model, direct=True)
    # What: save raw SSE privately; why: review must distinguish protocol evidence from summaries.
    (artifacts / f"completion-{index + 1}.sse").write_bytes(raw)
    # What: save parsed evidence privately; why: the deterministic result must remain auditable.
    (artifacts / f"completion-{index + 1}.txt").write_text(repr(row), encoding="utf-8")
# What: report success; why: the shell gate needs an explicit two-completion marker.
print("TWO_COMPLETIONS_OK")
