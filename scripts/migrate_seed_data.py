"""
One-time migration: extracts the 296 hardcoded REAL_PROSPECTS records from
the original prototype (../index.html, untouched) and pushes them into the
deployed CRM API via POST /prospects/bulk.

Usage:
    python scripts/migrate_seed_data.py --api https://<crm-api>.up.railway.app --token <jwt>

Get a token by logging into pooly-core first, e.g.:
    curl -X POST https://pooly-core-development.up.railway.app/login \\
      -H "Content-Type: application/json" \\
      -d '{"email": "you@pooly.mx", "password": "..."}'
"""
import argparse
import json
import os
import sys
import urllib.request

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html")


def extract_real_prospects(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")

    marker = "REAL_PROSPECTS=["
    i = text.find(marker)
    if i == -1:
        raise RuntimeError("REAL_PROSPECTS not found in source file")

    start = i + len("REAL_PROSPECTS=")
    depth = 0
    in_str = False
    esc = False
    end = None
    for k in range(start, len(text)):
        c = text[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if end is None:
        raise RuntimeError("Could not find matching closing bracket for REAL_PROSPECTS")

    return json.loads(text[start:end])


def post_bulk(api_base, token, prospects, batch_size=50):
    total = 0
    for i in range(0, len(prospects), batch_size):
        batch = prospects[i:i + batch_size]
        body = json.dumps({"prospects": batch}).encode("utf-8")
        req = urllib.request.Request(
            f"{api_base.rstrip('/')}/prospects/bulk",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            total += result.get("upserted", 0)
        print(f"  batch {i // batch_size + 1}: {len(batch)} rows upserted")
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True, help="CRM API base URL")
    parser.add_argument("--token", required=True, help="JWT from pooly-core /login")
    parser.add_argument("--dry-run", action="store_true", help="Only parse and print count, don't push")
    args = parser.parse_args()

    prospects = extract_real_prospects(SRC)
    print(f"Extracted {len(prospects)} prospects from {SRC}")

    if args.dry_run:
        print("Dry run — not pushing. Sample:", prospects[0]["empresa"], "...", prospects[-1]["empresa"])
        return

    total = post_bulk(args.api, args.token, prospects)
    print(f"Done: {total} prospects upserted into {args.api}")


if __name__ == "__main__":
    sys.exit(main())
