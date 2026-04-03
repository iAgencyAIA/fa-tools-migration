#!/usr/bin/env python3
"""
FA Tools Data Import — FK-ordered import with encrypted field verification.

Imports table data from JSON files to target Supabase via Management API.
Follows FK dependency order, handles auth.users constraints, verifies enc: prefix.

Usage:
  python fa-tools-import.py --project <ref> --token <sbp_token> --datadir /tmp/fa-tools-export
  python fa-tools-import.py --project <ref> --token <sbp_token> --datadir /tmp/fa-tools-export --dry-run
  python fa-tools-import.py --project <ref> --token <sbp_token> --datadir /tmp/fa-tools-export --phase 1
  python fa-tools-import.py --project <ref> --token <sbp_token> --datadir /tmp/fa-tools-export --tables leads proposals

Requires: curl, jq
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

# Tables grouped by phase for FK-safe import
PHASES = {
    1: {
        "name": "Reference/Config (no FKs)",
        "tables": [
            "app_settings", "app_roles", "insurance_products", "event_categories",
            "tax_deduction_settings", "vitality_discounts", "vitality_products",
            "unique_rider_udr", "rider_category_mappings", "premium_calc_type_settings",
            "product_links", "family_upgrade_paths", "sa_adjustments", "cv_per_1000",
            "special_discounts", "manual_content", "share_message_templates",
            "aia_funds", "api_keys", "admin_broadcasts", "unitlink_product_config",
            "unitlink_coi_cor_discounts", "unitlink_coi_sa_discounts",
            "vitality_bundle_discounts", "iagency_code_sequences",
        ],
    },
    2: {
        "name": "User-dependent (drop auth FKs first)",
        "pre_sql": """
-- Drop FK constraints to auth.users before importing user-dependent data
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN (
    SELECT conname, conrelid::regclass AS tbl
    FROM pg_constraint
    WHERE confrelid = 'auth.users'::regclass AND contype = 'f'
  ) LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', r.tbl, r.conname);
    RAISE NOTICE 'Dropped FK % on %', r.conname, r.tbl;
  END LOOP;
END $$;
""",
        "tables": [
            "fa_profiles", "user_roles", "role_permissions", "notifications",
            "broadcast_reads", "calendar_events", "event_responses",
            "chat_conversations", "admin_audit_log",
        ],
    },
    3: {
        "name": "Core business data (FK order)",
        "tables": [
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
        ],
    },
    4: {
        "name": "Sharing/Analytics",
        "tables": [
            "portfolio_shares", "portfolio_share_views",
            "application_shares", "application_share_views",
            "business_card_shares",
        ],
    },
    5: {
        "name": "History/Audit tables",
        "tables": [
            "leads_history", "proposals_history",
            "insurance_applications_history", "lead_policies_history",
        ],
    },
}

ENCRYPTED_TABLES = {"leads", "insurance_applications", "iagency_customers"}


def execute_sql(project_id, token, sql, timeout=120):
    """Execute SQL via Supabase Management API."""
    api_url = f"https://api.supabase.com/v1/projects/{project_id}/database/query"
    # Write SQL to temp file and use jq for safe escaping
    tmpfile = "/tmp/_fa_import_sql.sql"
    with open(tmpfile, "w") as f:
        f.write(sql)
    result = subprocess.run(
        ["bash", "-c",
         f'jq -n --rawfile sql "{tmpfile}" \'{{query: $sql}}\' | '
         f'curl -s -X POST '
         f'-H "Authorization: Bearer {token}" '
         f'-H "Content-Type: application/json" '
         f'-d @- "{api_url}"'],
        capture_output=True, text=True, timeout=timeout
    )
    try:
        os.remove(tmpfile)
    except OSError:
        pass
    if result.returncode != 0:
        return {"error": result.stderr[:300]}
    try:
        data = json.loads(result.stdout)
        return data
    except Exception:
        return {"error": f"Parse error: {result.stdout[:300]}"}


def sql_value(v):
    """Convert Python value to SQL literal, preserving enc: prefix."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, dict)):
        j = json.dumps(v, ensure_ascii=False).replace("'", "''")
        return f"'{j}'::jsonb"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def get_primary_key(project_id, token, table):
    """Get primary key column(s) for conflict resolution."""
    result = execute_sql(project_id, token,
        f"SELECT a.attname FROM pg_index i "
        f"JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        f"WHERE i.indrelid = 'public.\"{table}\"'::regclass AND i.indisprimary;")
    if result and isinstance(result, list) and result[0].get("attname"):
        return [r["attname"] for r in result]
    return ["id"]  # fallback


def generate_insert_sql(table, rows, pk_cols, batch_size=50):
    """Generate INSERT SQL batches with ON CONFLICT DO NOTHING."""
    if not rows:
        return []

    cols = list(rows[0].keys())
    col_list = ", ".join(f'"{c}"' for c in cols)
    pk_list = ", ".join(f'"{c}"' for c in pk_cols)

    batches = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        values = []
        for row in batch:
            vals = [sql_value(row.get(c)) for c in cols]
            values.append(f"({', '.join(vals)})")

        sql = (f"INSERT INTO public.\"{table}\" ({col_list}) VALUES\n"
               + ",\n".join(values)
               + f"\nON CONFLICT ({pk_list}) DO NOTHING;")
        batches.append(sql)

    return batches


def load_json(filepath):
    """Load JSON data, handling json_agg wrapper from export."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict) and "json_agg" in data[0]:
        return data[0]["json_agg"] or []
    return data if isinstance(data, list) else []


def verify_encrypted_fields(table, rows):
    """Check that enc: prefix is preserved in encrypted table data."""
    if table not in ENCRYPTED_TABLES:
        return []

    warnings = []
    for row in rows[:10]:  # spot check first 10
        if row.get("is_encrypted"):
            for key, val in row.items():
                if key in ("is_encrypted", "id", "created_at", "updated_at"):
                    continue
                if isinstance(val, str) and len(val) > 20 and not val.startswith("enc:"):
                    warnings.append(
                        f"  {table}.{key}: has is_encrypted=true but value doesn't start with enc:")
    return warnings


def main():
    parser = argparse.ArgumentParser(description="FA Tools Data Import")
    parser.add_argument("--project", required=True, help="Target Supabase project ref")
    parser.add_argument("--token", required=True, help="Supabase personal access token")
    parser.add_argument("--datadir", required=True, help="Directory with exported JSON files")
    parser.add_argument("--tables", nargs="*", help="Specific tables to import")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Import specific phase only")
    parser.add_argument("--batch-size", type=int, default=50, help="Rows per INSERT batch")
    parser.add_argument("--dry-run", action="store_true", help="Generate SQL without executing")
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"{'=' * 60}")
    print(f"FA Tools Data Import — {timestamp}")
    print(f"Target: {args.project}")
    print(f"Source: {args.datadir}")
    if args.dry_run:
        print("MODE: DRY RUN (no SQL executed)")
    print(f"{'=' * 60}")

    # Determine which tables to import
    if args.tables:
        phases_to_run = {0: {"name": "Custom selection", "tables": args.tables}}
    elif args.phase:
        phases_to_run = {args.phase: PHASES[args.phase]}
    else:
        phases_to_run = PHASES

    total_imported = 0
    all_warnings = []

    for phase_num, phase in sorted(phases_to_run.items()):
        print(f"\n{'─' * 60}")
        print(f"Phase {phase_num}: {phase['name']}")
        print(f"{'─' * 60}")

        # Run pre-SQL if defined
        if "pre_sql" in phase and not args.dry_run:
            print(f"  Running pre-phase SQL...")
            result = execute_sql(args.project, args.token, phase["pre_sql"])
            if isinstance(result, dict) and "error" in result:
                print(f"  PRE-SQL ERROR: {result['error']}")
                print("  Continuing anyway (FKs may not exist yet)...")

        for table in phase["tables"]:
            filepath = os.path.join(args.datadir, f"{table}.json")
            if not os.path.exists(filepath):
                print(f"\n  {table}: SKIP (no file)")
                continue

            rows = load_json(filepath)
            if not rows:
                print(f"\n  {table}: 0 rows (empty)")
                continue

            # Verify encrypted data integrity
            enc_warnings = verify_encrypted_fields(table, rows)
            all_warnings.extend(enc_warnings)
            if enc_warnings:
                for w in enc_warnings:
                    print(f"  WARNING: {w}")

            # Get primary key for ON CONFLICT
            if not args.dry_run:
                pk_cols = get_primary_key(args.project, args.token, table)
            else:
                pk_cols = ["id"]

            batches = generate_insert_sql(table, rows, pk_cols, args.batch_size)

            enc_tag = " [ENCRYPTED]" if table in ENCRYPTED_TABLES else ""
            print(f"\n  {table}: {len(rows)} rows, {len(batches)} batches{enc_tag}")

            imported = 0
            for j, sql in enumerate(batches):
                batch_count = min(args.batch_size, len(rows) - j * args.batch_size)

                if args.dry_run:
                    print(f"    batch {j+1}/{len(batches)}: DRY RUN ({len(sql)} chars)")
                    imported += batch_count
                else:
                    result = execute_sql(args.project, args.token, sql)
                    if isinstance(result, dict) and ("error" in result or "message" in result):
                        msg = str(result.get("message", result.get("error", "?")))[:120]
                        print(f"    batch {j+1}/{len(batches)}: ERROR — {msg}")
                    else:
                        imported += batch_count
                        print(f"    batch {j+1}/{len(batches)}: OK ({batch_count} rows)")

            total_imported += imported
            print(f"    Total: {imported}/{len(rows)}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Import complete: {total_imported} rows")
    if all_warnings:
        print(f"\nWARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  {w}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
