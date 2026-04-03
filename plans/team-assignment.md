# FA Tools Migration — Team Assignment

## Phase 1: Deep Analysis (Current)

Every oracle studies the migration-playbook + FA Tools repo before execution.

| Oracle | Assignment | Deliverable |
|--------|-----------|-------------|
| **BotDev** | Deep-learn FA Tools codebase — every component, hook, context, route. Map all env vars, CORS, Lovable config. Review all 16 edge functions for hardcoded refs. | `analysis/codebase-deep-dive.md` + list of all hardcoded values to update |
| **Dev** | Review all 184 migrations in order. Identify project-specific inserts, hardcoded UUIDs, auth dependencies. Test replay on a scratch Supabase project. | `analysis/migration-replay-report.md` + confirmed replay success/failures |
| **Data** | Inventory all data: table counts, storage objects, encrypted fields. Write export scripts. Test data roundtrip (export→import→verify). | `analysis/data-inventory.md` + working export/import scripts |
| **Security** | Audit encryption implementation. Map all secrets. Verify PDPA compliance of migration plan. Assess exposure risk during transition. | `analysis/security-audit.md` + secrets checklist |
| **Admin** | Plan infrastructure: new CF Pages project, DNS cutover, Lovable reconfiguration, pm2 services. | `plans/infrastructure-plan.md` |
| **QA** | Write comprehensive test plan: every route, every edge function, every role. Prepare test scripts. | `checklists/test-plan.md` |

## Phase 2: Execution

| Step | Oracle | Description |
|------|--------|-------------|
| 1 | **Dev** | Create new Supabase project. Replay 184 migrations. |
| 2 | **Dev** | Export + apply all functions, triggers, types from old project |
| 3 | **Data** | Export all table data. Handle encrypted fields with care. |
| 4 | **Data** | Import data to new project. Verify row counts. |
| 5 | **Data** | Migrate Storage buckets — download all objects, re-upload |
| 6 | **BotDev** | Deploy all 16 edge functions to new project |
| 7 | **BotDev** | Set all secrets (ENCRYPTION_KEY, FIRECRAWL, LOVABLE, APIFLASH) |
| 8 | **Admin** | Create auth users with matching UUIDs |
| 9 | **Admin** | Set up CF Pages / DNS / deploy pipeline |
| 10 | **BotDev** | Update Lovable project settings |
| 11 | **BotDev** | Update CORS origins in edge functions |
| 12 | **Security** | Verify encryption works end-to-end on new project |
| 13 | **QA** | Full test: every route, every function, every role |
| 14 | **Admin** | DNS cutover (atomic switch) |
| 15 | **QA** | Post-cutover verification |
| 16 | **BoB** | Report to แบงค์ |

## Phase 3: Verification

| Oracle | Verification |
|--------|-------------|
| **QA** | All routes load, all features work, all roles tested |
| **Security** | Encryption roundtrip verified, no exposed secrets |
| **BotDev** | All edge functions respond, AI chat works, fund sync works |
| **Data** | Row counts match, encrypted fields decrypt correctly |
| **Admin** | DNS resolves, SSL works, deploy pipeline functional |

## Communication

- All updates via `/talk-to bob` (BoB coordinates)
- Meeting thread for questions and blockers
- Board tracking via `maw project`
