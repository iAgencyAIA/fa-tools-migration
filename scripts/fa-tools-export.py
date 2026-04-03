#!/usr/bin/env python3
"""
FA Tools Data Export — Enhanced for encrypted fields, storage, and verification.

Exports all 67 tables from source Supabase via Management API.
Handles enc: prefix preservation, FK ordering, and row count verification.

Usage:
  python fa-tools-export.py --project <ref> --token <sbp_token>
  python fa-tools-export.py --project <ref> --token <sbp_token> --tables leads proposals
  python fa-tools-export.py --project <ref> --token <sbp_token> --storage-only
  python fa-tools-export.py --project <ref> --token <sbp_token> --counts-only

Requires: curl, jq
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

# FK-safe import order (67 tables in 5 phases)
TABLE_ORDER = [
    # Phase 1: Reference/Config (no FKs)
    "app_settings", "app_roles", "insurance_products", "event_categories",
    "tax_deduction_settings", "vitality_discounts", "vitality_products",
    "unique_rider_udr", "rider_category_mappings", "premium_calc_type_settings",
    "product_links", "family_upgrade_paths", "sa_adjustments", "cv_per_1000",
    "special_discounts", "manual_content", "share_message_templates",
    "aia_funds", "api_keys", "admin_broadcasts", "unitlink_product_config",
    "unitlink_coi_cor_discounts", "unitlink_coi_sa_discounts",
    "vitality_bundle_discounts", "iagency_code_sequences",
    # Phase 2: User-dependent tables
    "fa_profiles", "user_roles", "role_permissions", "notifications",
    "broadcast_reads", "calendar_events", "event_responses",
    "chat_conversations", "admin_audit_log",
    # Phase 3: Core business data (FK order)
    "leads", "proposals", "insurance_applications",
    "lead_policies", "lead_policy_coverages", "lead_follow_ups",
    "product_benefits", "product_payouts",
    "portfolio_customers", "portfolio_family_members",
    "portfolio_financial_info", "portfolio_policies", "portfolio_coverages",
    "chat_messages", "chat_feedback",
    "aia_fund_nav", "aia_fund_yearly_performance",
    "unitlink_product_funds", "unitlink_coi_rates", "unitlink_cor_rates",
    "unitlink_vitality_cashback",
    "iagency_customers", "iagency_policies", "iagency_policy_renewals",
    # Phase 4: Sharing/Analytics
    "portfolio_shares", "portfolio_share_views",
    "application_shares", "application_share_views",
    "business_card_shares",
    # Phase 5: History tables
    "leads_history", "proposals_history",
    "insurance_applications_history", "lead_policies_history",
]

ENCRYPTED_TABLES = {"leads", "insurance_applications", "iagency_customers"}
ENCRYPTED_FIELDS = {
    "leads": ["first_name", "last_name", "phone", "email", "line_id", "notes"],
    "insurance_applications": [],  # PII fields vary
    "iagency_customers": [],       # PII fields vary
}

STORAGE_BUCKETS = [
    "fa-business-cards", "fa-signatures", "broadcast-attachments",
    "event-attachments", "manual-screenshots", "product-images",
    "proposal-screenshots",
]


def execute_sql(project_id, token, sql, timeout=60):
    """Execute SQL via Supabase Management API (curl only — urllib gets 1010'd)."""
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
        print(f"  CURL ERROR: {result.stderr[:200]}", file=sys.stderr)
        return None
    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "error" in data:
            print(f"  SQL ERROR: {data['error']}", file=sys.stderr)
            return None
        return data
    except Exception:
        print(f"  PARSE ERROR: {result.stdout[:300]}", file=sys.stderr)
        return None


def get_all_tables(project_id, token):
    """Get actual table list from information_schema (not hardcoded)."""
    result = execute_sql(project_id, token,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name;")
    if not result:
        return []
    return [r["table_name"] for r in result]


def get_row_counts(project_id, token, tables):
    """Get row counts for all tables in a single query."""
    unions = " UNION ALL ".join(
        f"SELECT '{t}' as tbl, count(*)::int as cnt FROM public.\"{t}\""
        for t in tables
    )
    result = execute_sql(project_id, token, unions, timeout=120)
    if not result:
        return {}
    return {r["tbl"]: r["cnt"] for r in result}


def export_table(project_id, token, table, outdir, batch_size=500):
    """Export a single table, preserving enc: prefix values as raw text."""
    all_rows = []
    offset = 0

    while True:
        result = execute_sql(project_id, token,
            f"SELECT json_agg(t) FROM ("
            f"SELECT * FROM public.\"{table}\" ORDER BY ctid "
            f"LIMIT {batch_size} OFFSET {offset}) t;",
            timeout=120)

        if not result or not result[0].get("json_agg"):
            break

        rows = result[0]["json_agg"]
        all_rows.extend(rows)

        if len(rows) < batch_size:
            break
        offset += batch_size

    filepath = os.path.join(outdir, f"{table}.json")
    with open(filepath, "w") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=None)

    # Verify encrypted fields preserved
    enc_warnings = []
    if table in ENCRYPTED_TABLES and all_rows:
        for field in ENCRYPTED_FIELDS.get(table, []):
            for row in all_rows:
                val = row.get(field)
                if val and isinstance(val, str) and row.get("is_encrypted"):
                    if not val.startswith("enc:"):
                        enc_warnings.append(f"  WARNING: {table}.{field} row has is_encrypted=true but no enc: prefix")
                        break

    return len(all_rows), filepath, enc_warnings


def export_storage_inventory(project_id, token, outdir):
    """Export storage bucket inventory (object list, not file contents)."""
    print("\n=== Storage Bucket Inventory ===\n")

    for bucket in STORAGE_BUCKETS:
        result = execute_sql(project_id, token,
            f"SELECT name, bucket_id, metadata, created_at "
            f"FROM storage.objects WHERE bucket_id = '{bucket}' "
            f"ORDER BY created_at;")

        if not result:
            print(f"  {bucket}: ERROR or empty")
            continue

        count = len(result) if isinstance(result, list) and result and "name" in result[0] else 0
        print(f"  {bucket}: {count} objects")

        filepath = os.path.join(outdir, f"_storage_{bucket}.json")
        with open(filepath, "w") as f:
            json.dump(result if count > 0 else [], f, ensure_ascii=False, indent=2)

    print()


def export_functions(project_id, token, outdir):
    """Export all database functions for migration."""
    result = execute_sql(project_id, token,
        "SELECT routine_name, routine_definition IS NOT NULL as has_def, "
        "external_language as lang "
        "FROM information_schema.routines "
        "WHERE routine_schema = 'public' "
        "ORDER BY routine_name;")

    if not result:
        print("  Could not list functions")
        return

    print(f"\n=== Database Functions: {len(result)} found ===\n")

    # Export full function definitions
    func_result = execute_sql(project_id, token,
        "SELECT pg_get_functiondef(p.oid) as funcdef, p.proname as name "
        "FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
        "WHERE n.nspname = 'public' ORDER BY p.proname;",
        timeout=120)

    if func_result:
        filepath = os.path.join(outdir, "_functions.json")
        with open(filepath, "w") as f:
            json.dump(func_result, f, ensure_ascii=False, indent=2)
        print(f"  Exported {len(func_result)} function definitions to {filepath}")


def export_triggers(project_id, token, outdir):
    """Export all triggers."""
    result = execute_sql(project_id, token,
        "SELECT trigger_name, event_object_table, action_timing, "
        "event_manipulation, action_statement "
        "FROM information_schema.triggers "
        "WHERE trigger_schema = 'public' "
        "ORDER BY event_object_table, trigger_name;")

    if result:
        filepath = os.path.join(outdir, "_triggers.json")
        with open(filepath, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Exported {len(result)} triggers to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="FA Tools Data Export")
    parser.add_argument("--project", required=True, help="Source Supabase project ref")
    parser.add_argument("--token", required=True, help="Supabase personal access token (sbp_...)")
    parser.add_argument("--outdir", default="/tmp/fa-tools-export", help="Output directory")
    parser.add_argument("--tables", nargs="*", help="Specific tables (default: all)")
    parser.add_argument("--counts-only", action="store_true", help="Only show row counts")
    parser.add_argument("--storage-only", action="store_true", help="Only export storage inventory")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per batch")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"{'=' * 60}")
    print(f"FA Tools Data Export — {timestamp}")
    print(f"Source: {args.project}")
    print(f"Output: {args.outdir}")
    print(f"{'=' * 60}")

    if args.storage_only:
        export_storage_inventory(args.project, args.token, args.outdir)
        return 0

    # Get actual tables from DB
    db_tables = get_all_tables(args.project, args.token)
    if not db_tables:
        print("ERROR: Could not retrieve table list from database")
        return 1

    # Use specified tables or ordered list, filtering to what actually exists
    if args.tables:
        tables = [t for t in args.tables if t in db_tables]
    else:
        # Use FK-safe order, then append any tables not in our list
        ordered = [t for t in TABLE_ORDER if t in db_tables]
        extras = [t for t in db_tables if t not in TABLE_ORDER]
        tables = ordered + sorted(extras)

    print(f"\nFound {len(db_tables)} tables in DB, exporting {len(tables)}")
    if extras := [t for t in db_tables if t not in TABLE_ORDER]:
        print(f"  NEW tables not in inventory: {extras}")

    # Get row counts
    print(f"\n=== Row Counts ===\n")
    counts = get_row_counts(args.project, args.token, tables)

    manifest = {"timestamp": timestamp, "project": args.project, "tables": {}}
    total_rows = 0
    for t in tables:
        c = counts.get(t, "?")
        enc = " [ENCRYPTED]" if t in ENCRYPTED_TABLES else ""
        print(f"  {t}: {c} rows{enc}")
        manifest["tables"][t] = {"count": c, "encrypted": t in ENCRYPTED_TABLES}
        if isinstance(c, int):
            total_rows += c

    print(f"\n  TOTAL: {total_rows} rows across {len(tables)} tables")

    if args.counts_only:
        # Save manifest
        with open(os.path.join(args.outdir, "_manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        return 0

    # Export each table
    print(f"\n=== Exporting Data ===\n")
    all_warnings = []

    for table in tables:
        expected = counts.get(table, 0)
        if expected == 0:
            filepath = os.path.join(args.outdir, f"{table}.json")
            with open(filepath, "w") as f:
                json.dump([], f)
            print(f"  {table}: 0 rows (empty)")
            manifest["tables"][table]["exported"] = 0
            continue

        actual, filepath, warnings = export_table(
            args.project, args.token, table, args.outdir, args.batch_size)

        match = "OK" if actual == expected else f"MISMATCH (expected {expected})"
        enc = " [ENC]" if table in ENCRYPTED_TABLES else ""
        print(f"  {table}: {actual} rows — {match}{enc}")
        manifest["tables"][table]["exported"] = actual

        all_warnings.extend(warnings)

    # Export functions + triggers
    export_functions(args.project, args.token, args.outdir)
    export_triggers(args.project, args.token, args.outdir)

    # Export storage inventory
    export_storage_inventory(args.project, args.token, args.outdir)

    # Save manifest
    manifest["total_rows"] = total_rows
    manifest["warnings"] = all_warnings
    with open(os.path.join(args.outdir, "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Export complete: {total_rows} rows, {len(tables)} tables")
    print(f"Manifest: {args.outdir}/_manifest.json")
    if all_warnings:
        print(f"\n  WARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"    {w}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
