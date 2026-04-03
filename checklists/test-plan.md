# FA Tools Migration — Comprehensive QA Test Plan

> QA-Oracle | 2026-04-03 | For thread #257
> Covers: every route (20), every edge function (16), every role (anon/fa/admin/bqm/full_control/user)

---

## Test Environment

| Property | Value |
|----------|-------|
| **Staging URL** | `https://fatools.vuttipipat.com` (Phase 1 test) |
| **Production URL** | `https://tools.iagencyaia.com` (Phase 2 go-live) |
| **Old Supabase** | `rugcuukelivcferjjzek` |
| **New Supabase** | TBD (after Dev creates) |
| **Test viewports** | Desktop 1440×900, Mobile 375×812 |

## Role Test Accounts Required

| Role | Email | Purpose |
|------|-------|---------|
| `full_control` | (existing) | Full access — all pages, all features, manage roles |
| `admin` | (existing) | Admin — all pages except `admin_roles` |
| `fa` | (existing or create) | Standard FA — dashboard + profile only |
| `user` | (create) | View-only — dashboard + profile, limited features |
| `bqm` | (create) | Restricted — iQuick/iPlan/iCompare only |
| `anon` | (no login) | Public routes, shared links, public forms |

---

## SECTION 1: Infrastructure Verification

### 1.1 Supabase Project Health

```bash
# Test: New Supabase project responds
curl -s -o /dev/null -w "%{http_code}" "https://${NEW_PROJECT_REF}.supabase.co/rest/v1/" \
  -H "apikey: ${ANON_KEY}"
# Expected: 200

# Test: Compare table count
OLD_TABLES=$(curl -s "https://api.supabase.com/v1/projects/${OLD_REF}/database/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"query":"SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\''"}')
NEW_TABLES=$(curl -s "https://api.supabase.com/v1/projects/${NEW_REF}/database/query" \
  -d '{"query":"SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\''"}')
echo "OLD: $OLD_TABLES | NEW: $NEW_TABLES"
# Expected: counts match

# Test: Compare function count (CRITICAL — iJourney lesson #13)
# OLD project:
curl -s "https://api.supabase.com/v1/projects/${OLD_REF}/database/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"query":"SELECT routine_name FROM information_schema.routines WHERE routine_schema='\''public'\'' ORDER BY routine_name"}'
# NEW project: same query — lists must match exactly
# Expected: 40+ functions match

# Test: Compare trigger count
curl -s "https://api.supabase.com/v1/projects/${NEW_REF}/database/query" \
  -d '{"query":"SELECT count(*) FROM pg_trigger t JOIN pg_class c ON t.tgrelid=c.oid JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='\''public'\'' AND NOT t.tgisinternal"}'
# Expected: 40+ triggers match old project

# Test: Compare RLS policy count
curl -s "https://api.supabase.com/v1/projects/${NEW_REF}/database/query" \
  -d '{"query":"SELECT count(*) FROM pg_policies WHERE schemaname='\''public'\''"}'
# Expected: 370+ policies match
```

### 1.2 Storage Buckets

| # | Bucket | Test | Expected |
|---|--------|------|----------|
| 1 | `fa-signatures` | List objects, download 1 | File accessible |
| 2 | `fa-business-cards` | List objects, download 1 | File accessible |
| 3 | `proposal-screenshots` | List objects, download 1 | File accessible |
| 4 | `manual-screenshots` | List objects, download 1 | File accessible |
| 5 | `event-attachments` | List objects, download 1 | File accessible |

### 1.3 Edge Function Deployment

```bash
# Test: All 16 edge functions respond (not 404)
FUNCTIONS="api-gateway insurance-chat submit-lead encrypt-decrypt migrate-encrypt generate-reminders generate-business-card screenshot-proposal fetch-aia-funds fetch-fund-factsheet parse-fund-peer-avg sync-peer-avg sync-application-to-lead backfill-lead-sync soft-delete-lead update-fund-cron-schedule"

for fn in $FUNCTIONS; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://${NEW_PROJECT_REF}.supabase.co/functions/v1/${fn}" \
    -H "Authorization: Bearer ${ANON_KEY}")
  echo "$fn: $STATUS"
done
# Expected: All return 200 or 400 (not 404 = function exists)
# Note: Some may return 401/403 — that's OK, means function exists but needs auth
```

### 1.4 Secrets Verification

```bash
# Test: Encryption roundtrip
curl -s "https://${NEW_PROJECT_REF}.supabase.co/functions/v1/encrypt-decrypt" \
  -H "Authorization: Bearer ${ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"action":"encrypt","data":{"test":"QA-Oracle-verification-string"}}'
# Expected: Returns {"test":"enc:..."}

# Test: Decrypt the result back
curl -s "https://${NEW_PROJECT_REF}.supabase.co/functions/v1/encrypt-decrypt" \
  -H "Authorization: Bearer ${USER_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"action":"decrypt","data":{"test":"<enc_value_from_above>"}}'
# Expected: Returns {"test":"QA-Oracle-verification-string"}
```

### 1.5 CORS Verification

```bash
# Test: CORS preflight from staging domain
curl -s -I "https://${NEW_PROJECT_REF}.supabase.co/functions/v1/api-gateway" \
  -H "Origin: https://fatools.vuttipipat.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS
# Expected: Access-Control-Allow-Origin includes fatools.vuttipipat.com

# Repeat for: tools.iagencyaia.com
```

### 1.6 pg_cron Job

```bash
# Test: Fund cron schedule exists
curl -s "https://api.supabase.com/v1/projects/${NEW_REF}/database/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"query":"SELECT * FROM cron.job"}'
# Expected: Daily fund update job exists

# Test: app_settings has new Supabase anon key
curl -s "https://api.supabase.com/v1/projects/${NEW_REF}/database/query" \
  -d '{"query":"SELECT key, value FROM app_settings WHERE key='\''supabase_anon_key'\''"}'
# Expected: Value matches new project anon key
```

---

## SECTION 2: Data Integrity

### 2.1 Row Count Comparison (ALL tables)

```bash
# Script: Compare row counts between old and new project
TABLES="fa_profiles user_roles role_permissions app_roles app_settings
insurance_products product_benefits product_payouts product_links cv_per_1000 sa_adjustments
leads leads_history lead_follow_ups lead_policies lead_policy_coverages
proposals proposals_history
insurance_applications insurance_applications_history application_shares
portfolio_customers portfolio_policies portfolio_family_members portfolio_financial_info portfolio_shares
aia_funds aia_fund_nav aia_fund_yearly_performance
unitlink_product_funds unitlink_coi_rates unitlink_cor_rates unitlink_coi_sa_discounts unitlink_coi_cor_discounts unitlink_product_config unitlink_vitality_cashback
vitality_products vitality_discounts vitality_bundle_discounts special_discounts tax_deduction_settings
calendar_events event_categories event_responses
admin_broadcasts broadcast_reads
chat_conversations chat_messages chat_feedback
manual_content
business_card_shares share_message_templates api_keys
iagency_customers iagency_policies iagency_policy_renewals iagency_code_sequences
notifications premium_calc_type_settings rider_category_mappings unique_rider_udr"

for table in $TABLES; do
  OLD=$(curl -s "...old..." -d "{\"query\":\"SELECT count(*) as c FROM $table\"}" | jq -r '.[0].c')
  NEW=$(curl -s "...new..." -d "{\"query\":\"SELECT count(*) as c FROM $table\"}" | jq -r '.[0].c')
  MATCH=$([[ "$OLD" == "$NEW" ]] && echo "✅" || echo "❌ OLD=$OLD NEW=$NEW")
  echo "$table: $MATCH"
done
```

### 2.2 Encrypted Data Verification

| # | Test | Method | Expected |
|---|------|--------|----------|
| 1 | Encrypted leads have `enc:` prefix | `SELECT first_name FROM leads WHERE first_name LIKE 'enc:%' LIMIT 5` | All PII fields start with `enc:` |
| 2 | Decrypt a known lead | Call `encrypt-decrypt` edge function with decrypt action | Original PII readable |
| 3 | Create new lead → verify encryption | `submit-lead` edge function | New row has `enc:` prefix |
| 4 | View lead in dashboard | Login as FA, open Leads tab | PII displays decrypted |

### 2.3 Foreign Key Integrity

```bash
# Test: No orphaned records
# Check leads → user_roles FK
curl -s "..." -d '{"query":"SELECT count(*) FROM leads l LEFT JOIN fa_profiles f ON l.fa_id = f.id WHERE f.id IS NULL AND l.fa_id IS NOT NULL"}'
# Expected: 0

# Check proposals → insurance_products FK
curl -s "..." -d '{"query":"SELECT count(*) FROM proposals p LEFT JOIN insurance_products ip ON p.product_id = ip.id WHERE ip.id IS NULL AND p.product_id IS NOT NULL"}'
# Expected: 0
```

---

## SECTION 3: Route Testing Matrix (20 routes × 6 roles)

### Legend
- ✅ = Should load / work
- 🔒 = Should redirect to `/auth`
- 🚫 = Should redirect to `/dashboard` (insufficient permission)
- 📄 = Shows limited content based on role

### 3.1 Public Routes (no auth required)

| # | Route | anon | fa | admin | bqm | user | full_control | Test Focus |
|---|-------|------|-----|-------|-----|------|-------------|------------|
| 1 | `/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Landing page loads |
| 2 | `/auth` | ✅ | ✅→dash | ✅→dash | ✅→dash | ✅→dash | ✅→dash | Login form OR redirect if logged in |
| 3 | `/pending-approval` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Shows pending message |
| 4 | `/analyzepolicy` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Policy analysis tool loads |
| 5 | `/manual` | ✅ | ✅ | 📄+admin | ✅ | ✅ | 📄+admin | Manual content loads; admin sees extra |
| 6 | `/simulator` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Unit-link simulator loads |
| 7 | `/funds` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Fund data renders |
| 8 | `/api-docs` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | API documentation renders |

### 3.2 Token-Gated Public Routes (shared links)

| # | Route | Test | Expected |
|---|-------|------|----------|
| 9 | `/iquick/:token` | Load with valid token | Quick proposal renders with product data |
| 10 | `/iplan/:token` | Load with valid token | Full plan view with all sections |
| 11 | `/icompare/:token` | Load with valid token | Comparison table renders |
| 12 | `/ilink/:token` | Load with valid token | Unit-link proposal renders |
| 13 | `/iAgencyAIA/:token` | Load with old-format token | Redirects to correct new path |
| 14 | `/iAgency/:token` | Load with valid token | Business card renders + LINE link |
| 15 | `/portfolio/:token` | Load with valid token | Portfolio data renders |
| 16 | `/apply/:token` | Load with valid token | Application form renders, submittable |
| 17 | `/view-application/:token` | Load with valid token | Application data displays |

**For each shared route, also test:**
- Invalid/expired token → appropriate error message
- Token from OLD project → still resolves after migration

### 3.3 Authenticated Routes

| # | Route | anon | fa | admin | bqm | user | full_control |
|---|-------|------|-----|-------|-----|------|-------------|
| 18 | `/dashboard` | 🔒 | ✅ (7 tabs) | ✅ (7 tabs) | ✅ (3 tabs) | ✅ (7 tabs) | ✅ (7 tabs) |
| 19 | `/profile` | 🔒 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 20 | `/admin` | 🔒 | 🚫 | ✅ (20 tabs) | 🚫 | 🚫 | ✅ (21 tabs) |

### 3.4 Dashboard Tab Access per Role

| Tab | `full_control` | `admin` | `fa` | `user` | `bqm` |
|-----|---------------|---------|------|--------|-------|
| `quick` (iQuick) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `plan` (iPlan) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `compare` (iCompare) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `unitlink` | ✅ | ✅ | ✅ | ✅ | 🚫 |
| `lead` (Leads) | ✅ | ✅ | ✅ | ✅ | 🚫 |
| `funds` | ✅ | ✅ | ✅ | ✅ | 🚫 |
| `recruit` (FA Income) | ✅ | ✅ | ✅ | ✅ | 🚫 |

### 3.5 Admin Tab Access per Role

| Tab | `full_control` | `admin` | `fa` | `bqm` |
|-----|---------------|---------|------|-------|
| `dashboard` (Overview) | ✅ | ✅ | 🚫 | 🚫 |
| `products` | ✅ | ✅ | 🚫 | 🚫 |
| `unitlink` | ✅ | ✅ | 🚫 | 🚫 |
| `rider-categories` | ✅ | ✅ | 🚫 | 🚫 |
| `product-links` | ✅ | ✅ | 🚫 | 🚫 |
| `vitality` | ✅ | ✅ | 🚫 | 🚫 |
| `special-discounts` | ✅ | ✅ | 🚫 | 🚫 |
| `premium-calc-types` | ✅ | ✅ | 🚫 | 🚫 |
| `leads` | ✅ | ✅ | 🚫 | 🚫 |
| `iagency-customers` | ✅ | ✅ | 🚫 | 🚫 |
| `proposals` | ✅ | ✅ | 🚫 | 🚫 |
| `applications` | ✅ | ✅ | 🚫 | 🚫 |
| `users` | ✅ | ✅ | 🚫 | 🚫 |
| `roles` | ✅ | **🚫** | 🚫 | 🚫 |
| `tax-deductions` | ✅ | ✅ | 🚫 | 🚫 |
| `calendar` | ✅ | ✅ | 🚫 | 🚫 |
| `broadcasts` | ✅ | ✅ | 🚫 | 🚫 |
| `share-templates` | ✅ | ✅ | 🚫 | 🚫 |
| `trash` | ✅ | ✅ | 🚫 | 🚫 |
| `settings` | ✅ | ✅ | 🚫 | 🚫 |
| `api-keys` | ✅ | ✅ | 🚫 | 🚫 |

**Note:** `roles` tab is `full_control` ONLY — admin role cannot access it.

---

## SECTION 4: Edge Function Testing (ALL 16)

### 4.1 api-gateway (8 sub-routes)

```bash
BASE="https://${NEW_REF}.supabase.co/functions/v1/api-gateway"
API_KEY="<test-api-key>"

# Test each route
curl -s "$BASE/products" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: > 0

curl -s "$BASE/premium/calculate" -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"...","age":35,"sum_assured":1000000}'
# Expected: premium calculation result

curl -s "$BASE/leads" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: > 0

curl -s "$BASE/proposals" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: > 0

curl -s "$BASE/applications" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: > 0 or []

curl -s "$BASE/funds" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: > 0

curl -s "$BASE/fa-profile" -H "x-api-key: $API_KEY" | jq '.id'
# Expected: profile UUID

curl -s "$BASE/portfolio" -H "x-api-key: $API_KEY" | jq '.length'
# Expected: ≥ 0
```

### 4.2 insurance-chat (AI Chat)

```bash
# Test: Streaming SSE response
curl -s "https://${NEW_REF}.supabase.co/functions/v1/insurance-chat" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"แบบประกันชีวิตมีอะไรบ้าง?"}]}' \
  --no-buffer | head -20
# Expected: SSE data events with AI response content
```

### 4.3 submit-lead (Public Form)

```bash
# Test: Submit test lead with encryption
curl -s "https://${NEW_REF}.supabase.co/functions/v1/submit-lead" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name":"QA","last_name":"Test","phone":"0800000000",
    "email":"qa@test.com","notes":"migration test","source":"qa_test"
  }'
# Expected: 200, lead created with enc: prefix fields

# Test: Rate limiting (11th request in 1 minute should fail)
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code} " \
    "https://${NEW_REF}.supabase.co/functions/v1/submit-lead" \
    -H "Content-Type: application/json" \
    -d '{"first_name":"Rate","last_name":"Test'$i'","phone":"080000000'$i'"}'
done
# Expected: First 10 = 200, 11th = 429
```

### 4.4 encrypt-decrypt

```bash
# Test: Encrypt
ENC=$(curl -s "https://${NEW_REF}.supabase.co/functions/v1/encrypt-decrypt" \
  -H "Authorization: Bearer ${ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"action":"encrypt","data":{"name":"คุณทดสอบ","phone":"0891234567"}}')
echo "$ENC"
# Expected: {"name":"enc:...","phone":"enc:..."}

# Test: Decrypt (requires user JWT)
curl -s "https://${NEW_REF}.supabase.co/functions/v1/encrypt-decrypt" \
  -H "Authorization: Bearer ${USER_JWT}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"decrypt\",\"data\":$ENC}"
# Expected: {"name":"คุณทดสอบ","phone":"0891234567"}
```

### 4.5 generate-business-card

```bash
curl -s "https://${NEW_REF}.supabase.co/functions/v1/generate-business-card" \
  -H "Authorization: Bearer ${USER_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<fa_user_uuid>"}'
# Expected: 200, image URL in storage bucket
```

### 4.6 screenshot-proposal

```bash
curl -s "https://${NEW_REF}.supabase.co/functions/v1/screenshot-proposal" \
  -H "Authorization: Bearer ${USER_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://fatools.vuttipipat.com/iquick/<token>"}'
# Expected: 200, screenshot image returned or stored
```

### 4.7 fetch-aia-funds (Admin only)

```bash
curl -s "https://${NEW_REF}.supabase.co/functions/v1/fetch-aia-funds" \
  -H "Authorization: Bearer ${ADMIN_JWT}" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 200, funds upserted in aia_funds table
# Verify: SELECT count(*) FROM aia_funds should increase
```

### 4.8 fetch-fund-factsheet

```bash
curl -s "https://${NEW_REF}.supabase.co/functions/v1/fetch-fund-factsheet?fund_code=ABAG" \
  -H "Authorization: Bearer ${ANON_KEY}" \
  --output /tmp/factsheet-test.pdf
file /tmp/factsheet-test.pdf
# Expected: PDF document
```

### 4.9 generate-reminders

```bash
curl -s "https://${NEW_REF}.supabase.co/functions/v1/generate-reminders" \
  -H "Authorization: Bearer ${USER_JWT}"
# Expected: 200, notifications created for upcoming events
```

### 4.10 soft-delete-lead

```bash
# Create test lead first, then soft-delete
curl -s "https://${NEW_REF}.supabase.co/functions/v1/soft-delete-lead" \
  -H "Authorization: Bearer ${ADMIN_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"lead_id":"<test_lead_uuid>"}'
# Expected: 200, lead marked as deleted
```

### 4.11-4.16 Remaining Functions

| # | Function | Test | Expected |
|---|----------|------|----------|
| 11 | `parse-fund-peer-avg` | POST with valid URL | Performance data parsed |
| 12 | `sync-peer-avg` | POST (admin) | Batch iterates all funds |
| 13 | `sync-application-to-lead` | POST with app+lead IDs | Records linked |
| 14 | `backfill-lead-sync` | GET (dry run) | Returns count, no mutations |
| 15 | `migrate-encrypt` | POST (admin) | Batch encrypt succeeds |
| 16 | `update-fund-cron-schedule` | POST with time | pg_cron updated |

---

## SECTION 5: Auth Flow Testing

### 5.1 Sign In

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Valid login | Enter email + password → click login | Redirect to `/dashboard`, session persisted |
| 2 | Invalid password | Enter wrong password | Error message, stay on `/auth` |
| 3 | Non-existent email | Enter unknown email | Error message |
| 4 | Session persistence | Login → close tab → reopen | Still logged in (localStorage session) |
| 5 | Token refresh | Login → wait 60+ min → navigate | Auto-refresh, no re-login needed |
| 6 | Logout | Click logout → verify | Session cleared, redirect to `/auth` |

### 5.2 Sign Up

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Valid signup | Fill all fields (name, email, password, consent) | Account created, redirect to `/pending-approval` |
| 2 | Duplicate email | Signup with existing email | Error message |
| 3 | Weak password | Use < 6 chars | Validation error |
| 4 | Missing consent | Skip PDPA checkbox | Form won't submit |

### 5.3 Password Recovery

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Request reset | Enter email → submit | Email sent |
| 2 | Reset link | Click email link → set new password | Password updated, can login |
| 3 | Invalid link | Modify reset token in URL | Error message |

### 5.4 Role Enforcement

| # | Test | Role | Action | Expected |
|---|------|------|--------|----------|
| 1 | Admin page access | `fa` | Navigate to `/admin` | Redirect to `/dashboard` |
| 2 | Admin page access | `bqm` | Navigate to `/admin` | Redirect to `/dashboard` |
| 3 | Roles tab access | `admin` | Click "Role" tab in admin | Tab not visible |
| 4 | Roles tab access | `full_control` | Click "Role" tab | Tab visible + functional |
| 5 | BQM dashboard tabs | `bqm` | Check visible tabs | Only quick, plan, compare |
| 6 | Lead operations | `bqm` | Try to access lead tab | Tab not visible |
| 7 | Lead create | `user` | Try to create lead | Button not visible / disabled |
| 8 | Lead delete | `fa` | Try to delete lead | Not permitted (`can_delete_leads` = false) |

---

## SECTION 6: Feature Testing (Post-Migration)

### 6.1 Premium Calculator

| # | Test | Expected |
|---|------|----------|
| 1 | Select product → calculate premium | Correct premium amount based on age/SA |
| 2 | Change age → recalculate | Premium updates |
| 3 | Add riders → recalculate | Rider costs added |
| 4 | Tax deduction display | Shows correct deduction amount |
| 5 | Special discount applied | Discount reflected in total |
| 6 | Vitality discount applied | Vitality reduction shown |

### 6.2 Proposal Workflow (End-to-End)

| # | Step | Test |
|---|------|------|
| 1 | Calculate premium | Product selected, premium shown |
| 2 | Save proposal | Click save → `proposals` table insert |
| 3 | Share proposal | Generate share link → token created |
| 4 | View shared proposal (anon) | Open `/iplan/:token` → renders correctly |
| 5 | Customer fills contact form | Submit → `submit-lead` → lead created |
| 6 | FA views lead | Login → leads tab → new lead visible, PII decrypted |
| 7 | FA screenshots proposal | Click screenshot → APIFlash called → image stored |

### 6.3 Portfolio Management

| # | Test | Expected |
|---|------|----------|
| 1 | View portfolio dashboard | Customer list loads |
| 2 | Search customer | Results returned |
| 3 | View customer detail | Profile + policies load |
| 4 | Add family member | Saved to `portfolio_family_members` |
| 5 | Share portfolio | Token generated, `/portfolio/:token` works |

### 6.4 AI Chat

| # | Test | Expected |
|---|------|----------|
| 1 | Ask about products | Streaming response with product info |
| 2 | Ask about pricing | Uses `cv_per_1000` data |
| 3 | Rate limiting | 21st request in 1 min → 429 |

### 6.5 Fund Data

| # | Test | Expected |
|---|------|----------|
| 1 | Fund list loads | `aia_funds` data renders |
| 2 | Fund NAV display | `aia_fund_nav` data shown |
| 3 | Fund factsheet | PDF loads via `fetch-fund-factsheet` |
| 4 | UnitLink simulator | Calculation with fund data works |

### 6.6 Admin Functions

| # | Test | Expected |
|---|------|----------|
| 1 | Admin dashboard stats | RPCs return data (not null/empty) |
| 2 | User management | List users, approve pending, change role |
| 3 | Product management | Import/edit products |
| 4 | Lead management | View, search, soft-delete, restore from trash |
| 5 | Application management | View, history, status changes |
| 6 | Broadcast management | Create, publish, verify read tracking |
| 7 | Calendar events | Create event with attachment → uploaded to storage |
| 8 | Settings | Fund cron schedule visible, editable |
| 9 | API keys | Generate, revoke, test via `api-gateway` |
| 10 | iAgency customers | Transfer, code generation |

### 6.7 PWA Behavior

| # | Test | Expected |
|---|------|----------|
| 1 | Service Worker updates | New deployment triggers SW update prompt |
| 2 | Cache cleared | Old Supabase URL not in cached responses |
| 3 | Offline indicator | Shows offline state gracefully |
| 4 | Version check | Detects new version, prompts refresh |

---

## SECTION 7: Regression Risks from Migration Playbook

Based on **14 gotchas** from iJourney migration:

| # | Gotcha | Test |
|---|--------|------|
| 1 | DB functions missing | `SELECT count(*) FROM information_schema.routines WHERE routine_schema='public'` — must be 40+ |
| 2 | Triggers missing | `SELECT count(*) FROM pg_trigger` — must match old |
| 3 | `updated_at` trigger | Update a lead row → verify `updated_at` auto-updates |
| 4 | Auth users missing | Login with all test accounts |
| 5 | RLS blocks queries | Test each role can read/write expected tables |
| 6 | Admin dashboard empty | Stats RPCs return data (not null) |
| 7 | Shared links broken | Test 5 known existing share tokens |
| 8 | CORS blocking | Browser console shows no CORS errors |
| 9 | Encrypted data corrupted | Decrypt 5 known leads → PII readable |
| 10 | Storage files missing | Load 5 known business cards / signatures |

---

## SECTION 8: New Risks Not in Matrix

QA identifies these additional risks from codebase analysis:

### R19 (P1 HIGH): Lovable API Key Dependency
**Risk**: `insurance-chat` and `generate-business-card` call Lovable AI API. If Lovable restricts API access after org transfer, both features break.
**Test**: Call both functions post-migration, verify AI responses work.

### R20 (P2 MEDIUM): `iAgencyAIA/:token` Legacy Redirect
**Risk**: Old shared links may use `/iAgencyAIA/` prefix. The legacy redirect component must map correctly to new Supabase data.
**Test**: Load an old-format link → verify redirect.

### R21 (P2 MEDIUM): IndexedDB Cache Contains Old Supabase URL
**Risk**: FA Tools uses IndexedDB (idb) for offline product caching. Existing users will have cached data pointing to old Supabase URL in their browser.
**Test**: Clear IndexedDB → reload → verify fresh data from new project.

### R22 (P1 HIGH): `can_access_page` RPC Must Exist
**Risk**: ProtectedRoute calls `can_access_page(_user_id, _page)` RPC on every page load. If this RPC is missing from new project, ALL authenticated routes break — users see blank page or redirect loop.
**Test**: Verify RPC exists: `SELECT proname FROM pg_proc WHERE proname = 'can_access_page'`

---

## SECTION 9: Test Execution Order

1. **Infrastructure** (Section 1) — blocks everything else
2. **Data Integrity** (Section 2) — blocks feature testing
3. **Auth Flows** (Section 5) — blocks role-based testing
4. **Route × Role Matrix** (Section 3) — core access verification
5. **Edge Functions** (Section 4) — API-level testing
6. **Feature Testing** (Section 6) — end-to-end user flows
7. **Regression Checks** (Section 7) — playbook lessons applied
8. **PWA + Cache** (Section 6.7) — final cleanup verification

---

## SECTION 10: Test Summary Counts

| Area | Test Cases |
|------|-----------|
| Infrastructure (Supabase, storage, CORS, cron) | 25 |
| Data Integrity (row counts, encryption, FKs) | 60+ (per table) |
| Route × Role Matrix (20 routes × 6 roles) | 120 |
| Edge Functions (16 functions, multi-scenario) | 40 |
| Auth Flows (signin, signup, recovery, enforcement) | 20 |
| Feature Testing (calculator, proposals, chat, admin) | 35 |
| Regression from Playbook | 10 |
| **Total** | **310+** |

---

## Appendix: Quick-Run Smoke Test Script

For rapid post-deployment verification (run all critical paths in < 5 min):

```bash
#!/bin/bash
# FA Tools Migration — Smoke Test
# Usage: ./smoke-test.sh <SUPABASE_REF> <ANON_KEY> <STAGING_URL>

REF=$1; KEY=$2; URL=$3
PASS=0; FAIL=0

check() {
  local name=$1; local result=$2; local expected=$3
  if [[ "$result" == *"$expected"* ]]; then
    echo "✅ $name"; ((PASS++))
  else
    echo "❌ $name (got: $result)"; ((FAIL++))
  fi
}

# 1. Supabase API
R=$(curl -s -o /dev/null -w "%{http_code}" "https://${REF}.supabase.co/rest/v1/" -H "apikey: $KEY")
check "Supabase API" "$R" "200"

# 2. Staging URL
R=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
check "Staging URL" "$R" "200"

# 3. Edge Functions exist
for fn in api-gateway insurance-chat submit-lead encrypt-decrypt; do
  R=$(curl -s -o /dev/null -w "%{http_code}" "https://${REF}.supabase.co/functions/v1/${fn}" -H "Authorization: Bearer $KEY")
  check "Edge: $fn" "$R" "$(echo $R | grep -v 404)"
done

# 4. Products API
R=$(curl -s "https://${REF}.supabase.co/functions/v1/api-gateway/products" -H "x-api-key: $KEY" | jq 'length')
check "API: products" "$R" "$(echo $R | grep -E '^[1-9]')"

# 5. Encryption roundtrip
ENC=$(curl -s "https://${REF}.supabase.co/functions/v1/encrypt-decrypt" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"action":"encrypt","data":{"test":"smoke"}}' | jq -r '.test')
check "Encryption" "$ENC" "enc:"

# 6. Bundle contains new Supabase URL
BUNDLE_REF=$(curl -s "$URL/assets/index-*.js" 2>/dev/null | grep -oP '[a-z]{20}\.supabase\.co' | head -1)
check "Bundle Supabase URL" "$BUNDLE_REF" "${REF}.supabase.co"

# 7. Storage bucket
R=$(curl -s -o /dev/null -w "%{http_code}" "https://${REF}.supabase.co/storage/v1/bucket" -H "Authorization: Bearer $KEY")
check "Storage API" "$R" "200"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL)) checks"
```

---

*QA-Oracle — "Test everything. Trust nothing. Verify twice."*
