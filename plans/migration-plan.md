# FA Tools Migration — Execution Plan

## Pre-Requisites (Before Day 1)

- [ ] ENCRYPTION_KEY obtained from แบงค์
- [ ] All 4 edge function secrets documented
- [ ] 184 migrations tested on scratch project
- [ ] Export/import scripts tested
- [ ] Test plan written and reviewed
- [ ] Rollback plan confirmed
- [ ] แบงค์ approves go-live date

## Day 1: Schema + Data

### Morning: Schema
1. Create new Supabase project in iAgencyAIA org
2. Replay all 184 migrations in order
3. Export and apply all functions from old project (`pg_get_functiondef`)
4. Export and apply all triggers from old project (`pg_get_triggerdef`)
5. Verify: compare `information_schema.routines`, `pg_trigger`, `pg_policies` between old and new

### Afternoon: Data
6. Drop auth.users FK constraints on new project
7. Export all table data from old project (batched JSON)
8. Import all data to new project (INSERT with ON CONFLICT DO NOTHING)
9. Verify row counts match
10. Export and import Storage bucket objects (6 buckets)

## Day 2: Functions + Auth

### Morning: Edge Functions
11. Deploy all 16 edge functions to new project
12. Set all secrets (ENCRYPTION_KEY, FIRECRAWL_API_KEY, LOVABLE_API_KEY, APIFLASH_ACCESS_KEY)
13. Test each edge function individually
14. Set up pg_cron job for daily fund update
15. Update `app_settings` with new project URL and keys

### Afternoon: Auth + Config
16. Create auth users with matching UUIDs via Admin API
17. Re-add FK constraints
18. Update CORS origins in edge functions
19. Update Lovable project settings (Supabase URL + keys)
20. Build and deploy to CF Pages (staging domain first)

## Day 3: QA + Go-Live

### Morning: Full QA
21. Test every route with every role (anon, fa, admin, bqm)
22. Test encryption roundtrip (create lead → view lead)
23. Test AI chat (insurance-chat)
24. Test fund sync (fetch-aia-funds)
25. Test share links (proposal, application, portfolio, business card)
26. Test public forms (submit-lead, application form)
27. Test PWA behavior (install, cache, offline)

### Afternoon: Go-Live
28. Final data delta sync (rows added since Day 1 export)
29. DNS cutover — atomic switch to new project
30. Verify production URL works
31. Monitor for errors (30 min watch)
32. Report to แบงค์

## Rollback Plan

If critical issues found after DNS cutover:
1. Switch DNS back to old project (< 5 min)
2. Old project stays active throughout — zero data loss
3. Investigate and fix on new project
4. Try again

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| Analysis + Planning | 2-3 days |
| Execution (Day 1-2) | 2 days |
| QA + Go-Live (Day 3) | 1 day |
| **Total** | **5-6 days** |
