# FA Tools Migration — Risk Matrix

## Severity Legend
- **P0 CRITICAL** — Migration fails, data loss, or security breach
- **P1 HIGH** — Major feature broken, must fix before go-live
- **P2 MEDIUM** — Feature degraded, can fix post-migration
- **P3 LOW** — Minor issue, cosmetic

---

## P0 — CRITICAL RISKS

### R1: Encryption Key Loss
**Risk**: ENCRYPTION_KEY not migrated → all PII (leads, applications) permanently unreadable
**Impact**: 100% of lead data unusable, PDPA violation
**Mitigation**: Get key from แบงค์ BEFORE migration starts. Verify decrypt works on test data.
**Owner**: Security + แบงค์

### R2: 184 Migrations Fail to Replay
**Risk**: Migrations contain project-specific data, hardcoded UUIDs, or depend on auth state
**Impact**: Schema incomplete → app crashes
**Mitigation**: Dev reviews ALL 184 migrations for hardcoded refs. Test replay on a branch/staging project first.
**Owner**: Dev

### R3: Edge Function Secrets Missing
**Risk**: 4 external API keys not configured on new project → functions return 500
**Impact**: AI chat broken, fund data broken, screenshot broken, encryption broken
**Mitigation**: Document all 4 secrets. Set via `supabase secrets set` before go-live. Test each function.
**Owner**: BotDev + Admin

### R4: Data Migration Corrupts Encrypted Fields
**Risk**: Encrypted `enc:` values get mangled during JSON export/import
**Impact**: Existing leads/applications can't be decrypted
**Mitigation**: Export as raw text, verify `enc:` prefix preserved. Test decrypt after import.
**Owner**: Data + Security

---

## P1 — HIGH RISKS

### R5: Lovable Deployment Broken
**Risk**: Lovable platform tied to old Supabase project. Can't deploy updates after migration.
**Impact**: No new features or bug fixes deployable
**Mitigation**: Update Lovable project settings to new Supabase URL. Test a deploy before DNS cutover.
**Owner**: BotDev

### R6: Storage Buckets Not Migrated
**Risk**: 6 storage buckets (product images, business cards, signatures, screenshots, etc.) not created/populated
**Impact**: Images missing throughout the app
**Mitigation**: Script to list all objects, download, re-upload. Verify public URL patterns match.
**Owner**: Data + Admin

### R7: pg_cron Job References Old Project
**Risk**: Daily fund update cron calls old Supabase URL (recently fixed to use app_settings, but must verify)
**Impact**: Fund NAV data stops updating
**Mitigation**: Verify `app_settings.supabase_anon_key` set on new project. Test cron manually.
**Owner**: BotDev

### R8: Auth Users + Role Permissions
**Risk**: auth.users don't transfer. Existing FAs can't login. Role assignments lost.
**Impact**: All users locked out
**Mitigation**: Recreate auth users with same UUIDs (Admin API). Verify role_permissions table intact.
**Owner**: Dev + Admin

### R9: RLS Policies Block Queries
**Risk**: 370+ RLS policies may reference functions that don't exist yet on new project
**Impact**: Queries return empty or error
**Mitigation**: Apply functions BEFORE RLS policies. Test each role's access (anon, fa, admin, bqm).
**Owner**: Dev + QA

### R10: CORS Origins Not Updated
**Risk**: Edge functions and Supabase have hardcoded CORS origins. New domain not added.
**Impact**: API calls blocked by browser CORS policy
**Mitigation**: Update all CORS configs in edge functions + Supabase dashboard.
**Owner**: BotDev

---

## P2 — MEDIUM RISKS

### R11: PWA Cache Stale
**Risk**: Users with old Service Worker cached get mixed old/new API calls
**Impact**: Intermittent errors for existing users
**Mitigation**: Increment version in app. Service Worker will force update. Clear IndexedDB cache.
**Owner**: BotDev

### R12: Share Links Break During Transition
**Risk**: Existing share tokens (proposals, applications, portfolios) point to old project
**Impact**: Previously shared links stop working
**Mitigation**: Both old and new projects live during transition. DNS cutover is atomic. Old share links work until DNS switches.
**Owner**: QA

### R13: Fund Scraper Rate Limits
**Risk**: Firecrawl API has rate limits. New project key may have fresh limits but migration triggers batch operations.
**Impact**: Fund data sync fails
**Mitigation**: Rate limit the initial fund sync. Don't trigger batch operations during migration.
**Owner**: BotDev

### R14: Missing Triggers
**Risk**: Triggers (updated_at, validation) not migrated — same issue found in iJourney
**Impact**: Data integrity issues — timestamps don't update, financial validation skipped
**Mitigation**: Export triggers from `pg_trigger` on old project. Apply after functions. Verify all fire.
**Owner**: Dev

### R15: Hardcoded Project IDs in Code
**Risk**: `dlkdjowvljdgwcrcowot` or old project ref hardcoded in codebase
**Impact**: API calls go to wrong project
**Mitigation**: grep entire codebase for old project refs. Replace with env vars or new refs.
**Owner**: BotDev

---

## P3 — LOW RISKS

### R16: Admin Audit Log Gap
**Risk**: `admin_audit_log` entries during migration window lost or mixed
**Impact**: Incomplete audit trail
**Mitigation**: Note migration timestamp. Audit log gap is expected and documented.
**Owner**: Security

### R17: Calendar Event Reminders
**Risk**: `generate-reminders` function not running during migration → missed reminders
**Impact**: FAs miss calendar events
**Mitigation**: Run catch-up after migration. Notify FAs of potential missed reminders.
**Owner**: Admin

### R18: One-Time Migration Functions Still Deployed
**Risk**: `migrate-encrypt`, `backfill-lead-sync`, `migrate-proposals-to-policies` deployed but unnecessary
**Impact**: Dead code, potential security surface
**Mitigation**: Don't deploy one-time migration functions on new project. Clean up later.
**Owner**: BotDev

---

## Risk Summary

| Severity | Count | Must Resolve Before Go-Live |
|----------|-------|-----------------------------|
| P0 CRITICAL | 4 | YES — all must be resolved |
| P1 HIGH | 6 | YES — all must be resolved |
| P2 MEDIUM | 5 | Preferred, can fix post-migration |
| P3 LOW | 3 | No — fix when convenient |
| **Total** | **18** | |
