# FA Tools — Edge Functions Analysis (16 functions)

## Function Inventory

| # | Function | JWT Required | External APIs | Risk Level |
|---|----------|-------------|---------------|------------|
| 1 | **api-gateway** | No (X-API-Key or Bearer) | None | HIGH — main API, complex routing |
| 2 | **insurance-chat** | No | Lovable AI (Gemini) | MEDIUM — AI chat with tool calling |
| 3 | **submit-lead** | No | None | MEDIUM — public form, encrypts PII |
| 4 | **encrypt-decrypt** | Partial (decrypt=Yes) | None | HIGH — handles encryption key |
| 5 | **migrate-encrypt** | Yes | None | LOW — one-time migration |
| 6 | **generate-reminders** | No | None | LOW — calendar notifications |
| 7 | **generate-business-card** | No | Lovable AI (Gemini Flash) | MEDIUM — image generation |
| 8 | **screenshot-proposal** | No | APIFlash | MEDIUM — URL screenshot |
| 9 | **fetch-aia-funds** | No | Firecrawl → aiaim.co.th | HIGH — scrapes AIA fund data |
| 10 | **fetch-fund-factsheet** | No | aiaim.co.th (proxy) | LOW — PDF proxy |
| 11 | **parse-fund-peer-avg** | No | Firecrawl → PDFs | MEDIUM — PDF parsing |
| 12 | **sync-peer-avg** | No | Calls parse-fund-peer-avg | MEDIUM — batch operation |
| 13 | **sync-application-to-lead** | No | None | MEDIUM — data sync + encrypt |
| 14 | **backfill-lead-sync** | No | None | LOW — one-time migration |
| 15 | **soft-delete-lead** | No | None | LOW — simple CRUD |
| 16 | **update-fund-cron-schedule** | Yes | pg_cron | MEDIUM — cron management |

## Secrets Required

| Secret | Used By | Notes |
|--------|---------|-------|
| `ENCRYPTION_KEY` | encrypt-decrypt, submit-lead, sync-application-to-lead, migrate-encrypt | **CRITICAL** — 32-byte hex key for AES-256-GCM. All encrypted PII is unreadable without it |
| `FIRECRAWL_API_KEY` | fetch-aia-funds, parse-fund-peer-avg | Web scraping API |
| `LOVABLE_API_KEY` | insurance-chat, generate-business-card | AI gateway (Gemini) |
| `APIFLASH_ACCESS_KEY` | screenshot-proposal | Screenshot service |

## Auto-Provided by Supabase (no action needed)

| Variable | Used By |
|----------|---------|
| `SUPABASE_URL` | All functions |
| `SUPABASE_ANON_KEY` | All functions |
| `SUPABASE_SERVICE_ROLE_KEY` | All functions (admin operations) |

## Migration Considerations

### Each function must be:
1. Reviewed for hardcoded project references
2. Tested locally against new Supabase project
3. Deployed with `supabase functions deploy <name>`
4. Secrets set via `supabase secrets set KEY=value`

### Shared code
- `supabase/functions/_shared/` contains shared utilities
- All functions import from `_shared/` — must deploy together

### CORS
- Functions have CORS headers for specific origins
- Must update allowed origins after migration

### Rate Limiting
- `insurance-chat`: 20 requests/min
- `submit-lead`: 10 requests/min
- Rate limits are per-function, will reset on new project

### SSRF Protection
- `screenshot-proposal` has domain whitelist — must verify allowed domains post-migration
