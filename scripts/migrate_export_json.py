"""
Merges a localStorage export from the CRM prototype (the "Exportar" button
in Plantillas/Analytics — a JSON file shaped like
{"_meta": {...}, "pcrm_prospects": "[...stringified array...]", ...})
into the deployed CRM API via POST /prospects/bulk (upsert by id).

Unlike scripts/migrate_seed_data.py (one-time, reads the original 296
hardcoded rows out of index.html), this is for ongoing merges: whenever
someone doing outreach in a standalone/local copy of the tool exports their
browser's state and it needs to land in the shared Postgres-backed app.

Usage:
    python scripts/migrate_export_json.py --file export.json \\
      --api https://<crm-api>.up.railway.app --token <jwt>
"""
import argparse
import json
import sys
import urllib.request


def load_prospects(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("pcrm_prospects")
    if raw is None:
        raise RuntimeError("No 'pcrm_prospects' key in export file")
    prospects = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(prospects, list):
        raise RuntimeError("'pcrm_prospects' did not decode to a list")
    return prospects


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
    parser.add_argument("--file", required=True, help="Path to the exported JSON")
    parser.add_argument("--api", required=True, help="CRM API base URL")
    parser.add_argument("--token", required=True, help="JWT from pooly-core /login (admin user)")
    parser.add_argument("--dry-run", action="store_true", help="Only parse and print count, don't push")
    args = parser.parse_args()

    prospects = load_prospects(args.file)
    print(f"Loaded {len(prospects)} prospects from {args.file}")

    if args.dry_run:
        print("Dry run — not pushing. Sample:", prospects[0]["empresa"], "...", prospects[-1]["empresa"])
        return

    total = post_bulk(args.api, args.token, prospects)
    print(f"Done: {total} prospects upserted into {args.api}")


if __name__ == "__main__":
    sys.exit(main())
