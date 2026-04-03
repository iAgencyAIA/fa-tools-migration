# FA Tools Migration Project

> Migrating FA Tools from BankCurfew org to iAgencyAIA org — full analysis, risk assessment, and execution plan.

**Source**: `BankCurfew/iagencyaiafatools` + Supabase `tekvqbbjsfncwbdsvrfw`
**Target**: `iAgencyAIA/fa-tools` + New Supabase project (TBD)
**Reference**: [migration-playbook](https://github.com/iAgencyAIA/migration-playbook) (lessons from iJourney)

## Status: PLANNING

## Scale

| Dimension | iJourney (done) | FA Tools |
|-----------|-----------------|----------|
| Tables | 20 | 50+ |
| Rows | ~1,500 | 10,000+ |
| Migrations | 1 | **184** |
| Database Functions | 18 | **40+** |
| Edge Functions | 0 | **16** |
| Storage Buckets | 0 | **6** |
| RLS Policies | 65 | **370+** |
| Triggers | 16 | **40+** |
| Cron Jobs | 0 | **1** (daily fund update) |
| Auth Users | 2 | Many |
| External APIs | 1 (LINE LIFF) | **5** (Firecrawl, Lovable AI, APIFlash, AIA Fund, Supabase) |
| Encryption | None | **AES-256-GCM** (PII data) |
| Deploy | CF Pages | **Lovable** |

## Documents

### Analysis
- [Full Codebase Analysis](analysis/codebase-analysis.md) — Tech stack, structure, every component
- [Database Inventory](analysis/database-inventory.md) — All tables, functions, triggers, RLS, types
- [Edge Functions](analysis/edge-functions.md) — All 16 functions, APIs, secrets
- [External Integrations](analysis/external-integrations.md) — Every external service dependency
- [Encryption Audit](analysis/encryption-audit.md) — PII encryption, key management

### Risk Assessment
- [Risk Matrix](risks/risk-matrix.md) — All identified risks ranked by severity
- [Rollback Plan](risks/rollback-plan.md) — How to roll back if migration fails

### Plans
- [Migration Plan](plans/migration-plan.md) — Step-by-step execution plan
- [Team Assignment](plans/team-assignment.md) — Who does what

### Checklists
- [Pre-Migration](checklists/pre-migration.md)
- [Execution](checklists/execution.md)
- [Post-Migration](checklists/post-migration.md)

## Team

| Oracle | Role in Migration |
|--------|------------------|
| **BoB** | Orchestrator — overall coordination |
| **BotDev** | Lead — code analysis, env vars, edge functions |
| **Dev** | Schema migration, database functions, triggers |
| **Admin** | Infrastructure — CF Pages, DNS, deploy pipeline |
| **QA** | Verification — test every endpoint post-migration |
| **Data** | Data migration — export/import, encryption key |
| **Security** | Encryption audit, secrets rotation, PDPA compliance |
