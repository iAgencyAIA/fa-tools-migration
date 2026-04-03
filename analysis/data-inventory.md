# FA Tools Data Inventory

> Compiled by Data-Oracle, 2026-04-03
> Source: 184 migration files from `BankCurfew/iagencyaiafatools`

## Summary

| Category | Count |
|----------|-------|
| **Tables** | 67 |
| **Storage Buckets** | 7 |
| **RLS Policies** | 303 |
| **Database Functions** | 40+ (SECURITY DEFINER) |
| **Triggers** | 40+ |
| **Edge Functions** | 17 (16 deployable + _shared) |
| **Encrypted Tables** | 3 (leads, insurance_applications, iagency_customers) |
| **History/Audit Tables** | 4 |
| **Seed Data Migrations** | 30 |

## Tables (67 Total)

### Tier 1: No Foreign Keys (migrate FIRST)

These tables have no FK dependencies — safe to import in any order:

| # | Table | Category | Encrypted | Has Seed Data |
|---|-------|----------|-----------|---------------|
| 1 | `app_settings` | Config | No | Yes |
| 2 | `app_roles` | Config | No | Yes |
| 3 | `insurance_products` | Product | No | Yes |
| 4 | `event_categories` | Reference | No | Yes |
| 5 | `tax_deduction_settings` | Reference | No | Yes |
| 6 | `vitality_discounts` | Reference | No | Yes |
| 7 | `vitality_products` | Reference | No | Yes |
| 8 | `unique_rider_udr` | Reference | No | Yes |
| 9 | `rider_category_mappings` | Reference | No | Yes |
| 10 | `premium_calc_type_settings` | Reference | No | Yes |
| 11 | `product_links` | Reference | No | Yes |
| 12 | `family_upgrade_paths` | Reference | No | No |
| 13 | `sa_adjustments` | Reference | No | No |
| 14 | `cv_per_1000` | Reference | No | No |
| 15 | `special_discounts` | Reference | No | No |
| 16 | `manual_content` | Content | No | Yes |
| 17 | `share_message_templates` | Config | No | Yes |
| 18 | `aia_funds` | Fund Data | No | No |
| 19 | `api_keys` | Config | No | Yes |
| 20 | `admin_broadcasts` | Communication | No | No |

### Tier 2: FK to auth.users (migrate AFTER auth users created)

These reference `auth.users(id)` — must drop FKs, import data, recreate auth users, re-add FKs.

| # | Table | Category | Encrypted | Notes |
|---|-------|----------|-----------|-------|
| 21 | `fa_profiles` | Core | No | FK → auth.users |
| 22 | `user_roles` | Auth | No | FK → auth.users, seed data |
| 23 | `role_permissions` | Auth | No | FK → app_roles, seed data |
| 24 | `notifications` | Communication | No | FK → auth.users |
| 25 | `broadcast_reads` | Communication | No | FK → auth.users |
| 26 | `calendar_events` | Events | No | FK → auth.users |
| 27 | `event_responses` | Events | No | FK → auth.users |
| 28 | `chat_conversations` | Communication | No | FK → auth.users |
| 29 | `admin_audit_log` | Audit | No | FK → auth.users |

### Tier 3: FK to other public tables (migrate in order)

| # | Table | Category | Encrypted | FK Dependencies |
|---|-------|----------|-----------|----------------|
| 30 | `leads` | Core | **YES** | FK → fa_profiles |
| 31 | `proposals` | Core | No | FK → leads |
| 32 | `insurance_applications` | Core | **YES** | FK → leads |
| 33 | `lead_policies` | Core | No | FK → leads |
| 34 | `lead_policy_coverages` | Core | No | FK → lead_policies |
| 35 | `lead_follow_ups` | Core | No | FK → leads |
| 36 | `product_benefits` | Product | No | FK → insurance_products |
| 37 | `product_payouts` | Product | No | FK → insurance_products |
| 38 | `portfolio_customers` | Portfolio | No | FK → fa_profiles |
| 39 | `portfolio_family_members` | Portfolio | No | FK → portfolio_customers |
| 40 | `portfolio_financial_info` | Portfolio | No | FK → portfolio_customers |
| 41 | `portfolio_policies` | Portfolio | No | FK → portfolio_customers |
| 42 | `portfolio_coverages` | Portfolio | No | FK → portfolio_policies |
| 43 | `chat_messages` | Communication | No | FK → chat_conversations |
| 44 | `chat_feedback` | Communication | No | FK → chat_conversations |
| 45 | `aia_fund_nav` | Fund Data | No | FK → aia_funds |
| 46 | `aia_fund_yearly_performance` | Fund Data | No | FK → aia_funds |
| 47 | `unitlink_product_config` | Unitlink | No | Seed data |
| 48 | `unitlink_product_funds` | Unitlink | No | FK → unitlink_product_config |
| 49 | `unitlink_coi_rates` | Unitlink | No | FK → unitlink_product_config |
| 50 | `unitlink_cor_rates` | Unitlink | No | FK → unitlink_product_config |
| 51 | `unitlink_vitality_cashback` | Unitlink | No | FK → unitlink_product_config |
| 52 | `unitlink_coi_cor_discounts` | Unitlink | No | Seed data |
| 53 | `unitlink_coi_sa_discounts` | Unitlink | No | No |
| 54 | `vitality_bundle_discounts` | Unitlink | No | No |
| 55 | `iagency_customers` | iAgency | **YES** | No |
| 56 | `iagency_policies` | iAgency | No | FK → iagency_customers |
| 57 | `iagency_code_sequences` | iAgency | No | Seed data |
| 58 | `iagency_policy_renewals` | iAgency | No | FK → iagency_policies |

### Tier 4: Sharing/View Tracking (migrate last)

| # | Table | Category | Encrypted | FK Dependencies |
|---|-------|----------|-----------|----------------|
| 59 | `portfolio_shares` | Sharing | No | FK → portfolio_customers |
| 60 | `portfolio_share_views` | Analytics | No | FK → portfolio_shares |
| 61 | `application_shares` | Sharing | No | FK → insurance_applications |
| 62 | `application_share_views` | Analytics | No | FK → application_shares |
| 63 | `business_card_shares` | Sharing | No | FK → fa_profiles |

### Tier 5: History/Audit Tables (migrate last — service_role only)

| # | Table | Category | Encrypted | Notes |
|---|-------|----------|-----------|-------|
| 64 | `leads_history` | Audit | No | Service role only RLS |
| 65 | `proposals_history` | Audit | No | Service role only RLS |
| 66 | `insurance_applications_history` | Audit | No | Service role only RLS |
| 67 | `lead_policies_history` | Audit | No | Service role only RLS |

## Encrypted Fields (AES-256-GCM)

**Algorithm**: AES-256-GCM via Web Crypto API (SubtleCrypto)
**Key**: 32-byte hex string stored as Edge Function secret (`ENCRYPTION_KEY`)
**Format**: `enc:` prefix + base64(IV + ciphertext + auth tag)
**IV**: Random 12-byte per encryption

### Fields with `enc:` prefix data:

**`leads` table:**
- `first_name` (TEXT)
- `last_name` (TEXT)
- `phone` (TEXT)
- `email` (TEXT)
- `line_id` (TEXT)
- `notes` (TEXT)
- Flag: `is_encrypted` (BOOLEAN, DEFAULT false)

**`insurance_applications` table:**
- PII fields in multi-step application form
- Flag: `is_encrypted` (BOOLEAN, DEFAULT false)

**`iagency_customers` table:**
- Customer PII fields
- Flag: `is_encrypted` (BOOLEAN, DEFAULT false)

### CRITICAL Migration Rules for Encrypted Data:
1. **SAME ENCRYPTION_KEY** must be used on new project — changing it = permanent data loss
2. Export/import must preserve `enc:` prefix values as raw TEXT — no JSON transformation
3. Verify roundtrip: export → import → decrypt → matches original plaintext
4. `is_encrypted` flag must match actual field state

## Storage Buckets (7 Total)

All configured with `public = true`:

| # | Bucket Name | Purpose | RLS Policies |
|---|-------------|---------|-------------|
| 1 | `fa-business-cards` | FA business card images | Yes |
| 2 | `fa-signatures` | FA signature images | Yes |
| 3 | `broadcast-attachments` | Admin broadcast files | Yes |
| 4 | `event-attachments` | Calendar event files | Yes |
| 5 | `manual-screenshots` | Help doc screenshots | Yes |
| 6 | `product-images` | Product marketing images | Yes |
| 7 | `proposal-screenshots` | Proposal/comparison screenshots | Yes |

**Total storage policies**: 23 RLS policies across storage.objects
**Migration note**: Files must be downloaded → re-uploaded. Public URLs change (new project ID in URL). Any DB columns storing full storage URLs need UPDATE.

## Seed/Reference Data Tables

30 migrations contain INSERT statements. These are reference data that MUST exist for the app to function:

| Table | Type | Critical |
|-------|------|----------|
| `app_settings` | Config KV pairs | YES — includes cron URLs |
| `app_roles` | Role definitions | YES — admin, fa, user, bqm |
| `role_permissions` | Permission matrix | YES — page access control |
| `insurance_products` | Product catalog | YES — core feature |
| `premium_calc_type_settings` | Calculation rules | YES — premium engine |
| `tax_deduction_settings` | Tax limits | YES — tax calculations |
| `unique_rider_udr` | Rider age/SA limits | YES — product validation |
| `vitality_discounts` | Discount schedules | YES — pricing |
| `vitality_products` | Vitality plans | YES — product catalog |
| `rider_category_mappings` | Rider categories | YES — product mapping |
| `product_links` | External references | NO — cosmetic |
| `share_message_templates` | Share messages | NO — cosmetic |
| `manual_content` | Help docs | NO — cosmetic |
| `event_categories` | Event types | NO — calendar feature |
| `api_keys` | API key records | YES — Jarvis bot, BQM |
| `unitlink_product_config` | Unitlink products | YES — investment feature |
| `unitlink_coi_cor_discounts` | Discount tables | YES — pricing |
| `iagency_code_sequences` | Code sequences | YES — customer codes |

## Import Order (FK-safe)

```
Phase 1: Reference/Config (no FKs)
  app_settings → app_roles → insurance_products → event_categories →
  tax_deduction_settings → vitality_discounts → vitality_products →
  unique_rider_udr → rider_category_mappings → premium_calc_type_settings →
  product_links → family_upgrade_paths → sa_adjustments → cv_per_1000 →
  special_discounts → manual_content → share_message_templates →
  aia_funds → api_keys → admin_broadcasts → unitlink_product_config →
  unitlink_coi_cor_discounts → unitlink_coi_sa_discounts →
  vitality_bundle_discounts → iagency_code_sequences

Phase 2: Drop auth.users FKs, then import user-dependent tables
  [DROP FK CONSTRAINTS to auth.users]
  fa_profiles → user_roles → role_permissions → notifications →
  broadcast_reads → calendar_events → event_responses →
  chat_conversations → admin_audit_log

Phase 3: Core business data (FK order)
  leads (ENCRYPTED) → proposals → insurance_applications (ENCRYPTED) →
  lead_policies → lead_policy_coverages → lead_follow_ups →
  product_benefits → product_payouts →
  portfolio_customers → portfolio_family_members →
  portfolio_financial_info → portfolio_policies → portfolio_coverages →
  chat_messages → chat_feedback →
  aia_fund_nav → aia_fund_yearly_performance →
  unitlink_product_funds → unitlink_coi_rates → unitlink_cor_rates →
  unitlink_vitality_cashback →
  iagency_customers (ENCRYPTED) → iagency_policies → iagency_policy_renewals

Phase 4: Sharing/Analytics
  portfolio_shares → portfolio_share_views →
  application_shares → application_share_views →
  business_card_shares

Phase 5: History tables
  leads_history → proposals_history →
  insurance_applications_history → lead_policies_history

Phase 6: Recreate auth users + re-add FKs
  [CREATE auth users via Admin API with matching UUIDs]
  [RE-ADD FK CONSTRAINTS to auth.users]
```

## Risk Notes

1. **R4 (P0)**: Encrypted field roundtrip — `enc:` prefix must survive JSON serialization
2. **R6 (P1)**: 7 storage buckets need manual file migration — no automated Supabase transfer
3. **R8 (P1)**: auth.users don't transfer — UUIDs must be recreated via Admin API
4. **R14 (P2)**: Triggers must be exported separately via `pg_get_triggerdef()`
5. **Live row counts**: Cannot access old Supabase via MCP (Lovable-managed) — need SBP token or direct access
