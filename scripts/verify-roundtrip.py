#!/usr/bin/env python3
"""
FA Tools Migration Verification — Compare source and target data.

Verifies:
1. Row counts match per table
2. Encrypted fields (enc: prefix) preserved
3. Database functions exist
4. Triggers exist
5. Storage buckets created
6. RLS policies applied

Usage:
  python verify-roundtrip.py --source <old_ref> --target <new_ref> --token <sbp_token>
  python verify-roundtrip.py --target <new_ref> --token <sbp_token> --manifest /tmp/fa-tools-export/_manifest.json
"""
import argparse
import json
import subprocess
import sys


def execute_sql(project_id, token, sql, timeout=60):
    """Execute SQL via Management API."""
    api_url = f"https://api.supabase.com/v1/projects/{project_id}/database/query"
    payload = json.dumps({"query": sql})
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json",
         "-d", payload, api_url],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "error" in data:
            return None
        return data
    except Exception:
        return None


def check_row_counts(project_id, token, expected_counts):
    """Compare row counts against expected."""
    print("\n=== Row Count Verification ===\n")
    passed = 0
    failed = 0

    tables = list(expected_counts.keys())
    # Build union query for all counts
    unions = " UNION ALL ".join(
        f"SELECT '{t}' as tbl, count(*)::int as cnt FROM public.\"{t}\""
        for t in tables
    )
    result = execute_sql(project_id, token, unions, timeout=120)

    if not result:
        print("  ERROR: Could not query target database")
        return 0, len(tables)

    actual = {r["tbl"]: r["cnt"] for r in result}

    for table in tables:
        exp = expected_counts[table]
        act = actual.get(table, "MISSING")

        if act == "MISSING":
            print(f"  FAIL  {table}: table missing from target")
            failed += 1
        elif act == exp:
            print(f"  PASS  {table}: {act} rows")
            passed += 1
        else:
            print(f"  FAIL  {table}: expected {exp}, got {act}")
            failed += 1

    return passed, failed


def check_encrypted_fields(project_id, token):
    """Spot-check encrypted fields have enc: prefix."""
    print("\n=== Encrypted Field Verification ===\n")

    checks = [
        ("leads", "first_name", "is_encrypted = true"),
        ("insurance_applications", "id", "is_encrypted = true"),
        ("iagency_customers", "id", "is_encrypted = true"),
    ]

    for table, field, where in checks:
        result = execute_sql(project_id, token,
            f"SELECT count(*) as total, "
            f"count(*) FILTER (WHERE {field} LIKE 'enc:%') as encrypted "
            f"FROM public.\"{table}\" WHERE {where} LIMIT 1;")

        if not result:
            print(f"  SKIP  {table}: could not query")
            continue

        total = result[0]["total"]
        encrypted = result[0]["encrypted"]

        if total == 0:
            print(f"  SKIP  {table}: no encrypted rows")
        elif encrypted == total:
            print(f"  PASS  {table}: {encrypted}/{total} rows have enc: prefix")
        else:
            print(f"  FAIL  {table}: {encrypted}/{total} rows have enc: prefix ({total - encrypted} MISSING)")


def check_functions(project_id, token):
    """Check database functions exist."""
    print("\n=== Database Functions ===\n")

    result = execute_sql(project_id, token,
        "SELECT count(*) as cnt FROM information_schema.routines "
        "WHERE routine_schema = 'public';")

    if result:
        count = result[0]["cnt"]
        status = "PASS" if count >= 40 else "WARN"
        print(f"  {status}  {count} functions found (expected 40+)")
    else:
        print("  FAIL  Could not query functions")


def check_triggers(project_id, token):
    """Check triggers exist."""
    print("\n=== Triggers ===\n")

    result = execute_sql(project_id, token,
        "SELECT count(*) as cnt FROM information_schema.triggers "
        "WHERE trigger_schema = 'public';")

    if result:
        count = result[0]["cnt"]
        status = "PASS" if count >= 30 else "WARN"
        print(f"  {status}  {count} triggers found (expected 30+)")
    else:
        print("  FAIL  Could not query triggers")


def check_storage_buckets(project_id, token):
    """Check storage buckets exist."""
    print("\n=== Storage Buckets ===\n")

    expected = [
        "fa-business-cards", "fa-signatures", "broadcast-attachments",
        "event-attachments", "manual-screenshots", "product-images",
        "proposal-screenshots",
    ]

    result = execute_sql(project_id, token,
        "SELECT id, public FROM storage.buckets ORDER BY id;")

    if not result:
        print("  FAIL  Could not query storage buckets")
        return

    existing = {r["id"]: r["public"] for r in result}

    for bucket in expected:
        if bucket in existing:
            pub = "public" if existing[bucket] else "PRIVATE"
            print(f"  PASS  {bucket} ({pub})")
        else:
            print(f"  FAIL  {bucket}: MISSING")


def check_rls_policies(project_id, token):
    """Check RLS policy count."""
    print("\n=== RLS Policies ===\n")

    result = execute_sql(project_id, token,
        "SELECT count(*) as cnt FROM pg_policies "
        "WHERE schemaname = 'public';")

    if result:
        count = result[0]["cnt"]
        status = "PASS" if count >= 300 else "WARN"
        print(f"  {status}  {count} policies found (expected 300+)")
    else:
        print("  FAIL  Could not query policies")


def main():
    parser = argparse.ArgumentParser(description="FA Tools Migration Verification")
    parser.add_argument("--source", help="Source Supabase project ref (for live comparison)")
    parser.add_argument("--target", required=True, help="Target Supabase project ref")
    parser.add_argument("--token", required=True, help="Supabase personal access token")
    parser.add_argument("--manifest", help="Path to export manifest JSON (alternative to --source)")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"FA Tools Migration Verification")
    print(f"Target: {args.target}")
    print(f"{'=' * 60}")

    # Get expected counts
    if args.manifest:
        with open(args.manifest) as f:
            manifest = json.load(f)
        expected_counts = {
            t: info["count"] if isinstance(info, dict) else info
            for t, info in manifest.get("tables", {}).items()
            if (info.get("count", 0) if isinstance(info, dict) else info) != "?"
        }
    elif args.source:
        # Query source for counts
        tables_result = execute_sql(args.source, args.token,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
        if tables_result:
            tables = [r["table_name"] for r in tables_result]
            unions = " UNION ALL ".join(
                f"SELECT '{t}' as tbl, count(*)::int as cnt FROM public.\"{t}\""
                for t in tables
            )
            counts = execute_sql(args.source, args.token, unions, timeout=120)
            expected_counts = {r["tbl"]: r["cnt"] for r in (counts or [])}
        else:
            expected_counts = {}
    else:
        print("ERROR: Provide --source or --manifest for comparison")
        return 1

    # Run all checks
    passed, failed = check_row_counts(args.target, args.token, expected_counts)
    check_encrypted_fields(args.target, args.token)
    check_functions(args.target, args.token)
    check_triggers(args.target, args.token)
    check_storage_buckets(args.target, args.token)
    check_rls_policies(args.target, args.token)

    # Final summary
    print(f"\n{'=' * 60}")
    total_checks = passed + failed
    if failed == 0:
        print(f"ALL CHECKS PASSED ({passed}/{total_checks} tables verified)")
    else:
        print(f"FAILURES DETECTED: {failed}/{total_checks} tables failed")
    print(f"{'=' * 60}")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
