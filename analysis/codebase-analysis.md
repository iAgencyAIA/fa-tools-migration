# FA Tools — Codebase Analysis

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite 5 + SWC |
| Styling | Tailwind CSS 3 + shadcn/ui (Radix) |
| State | TanStack React Query v5 |
| Routing | react-router-dom v6 |
| Auth | Supabase Auth (email/password only, no social) |
| Backend | Supabase (Postgres + Edge Functions + Storage + Auth) |
| Forms | react-hook-form + zod |
| Charts | Recharts |
| PDF | jspdf + jspdf-autotable + html2canvas |
| Excel | xlsx |
| QR | qrcode + qrcode.react |
| PWA | vite-plugin-pwa (Workbox, autoUpdate) |
| Caching | IndexedDB (idb) + session cache + Service Worker |
| Deploy | Lovable platform |
| Package Manager | Bun |

## Project Structure

```
src/
  pages/              # 17 pages (Dashboard, Auth, Profile, Admin, etc.)
  components/         # Large — many subdirectories
  contexts/           # 4 contexts (AppLanguage, ApplicationLanguage, Chat, SharedLanguage)
  hooks/              # 18 hooks (auth, caching, permissions, products, PWA)
  lib/                # 45+ files (utils, PDF gen, tax calc, encryption)
  integrations/       # Supabase client + types
  data/               # translations, nationalities, address, banks
  workers/            # pdf.worker.ts (Web Worker for PDF generation)
  assets/

supabase/
  config.toml         # Project config
  migrations/         # 184 migration files (Nov 2025 - Apr 2026)
  functions/          # 16 edge functions + _shared/

public/
  data/               # thailand-address-raw.json (~2MB)
  fonts/              # LINESeedSansTH + Inter (~2.2MB)
  app-icon.png, og-image.png, favicon
```

## Routes (20 routes)

| Route | Page | Auth Required |
|-------|------|--------------|
| `/` | Landing | No |
| `/auth` | Login/Signup | No |
| `/dashboard` | Main workspace (6 modes) | Yes |
| `/profile` | FA profile editor | Yes |
| `/admin` | Admin panel | Yes (admin role) |
| `/pending-approval` | Approval waiting | No |
| `/analyzepolicy` | Policy analysis tool | No |
| `/manual` | Documentation | No |
| `/simulator` | Unit-linked fund simulator | No |
| `/funds` | Fund viewer | No |
| `/api-docs` | API documentation | No |
| `/iquick/:token` | Shared quick proposal | No |
| `/iplan/:token` | Shared plan proposal | No |
| `/icompare/:token` | Shared comparison | No |
| `/ilink/:token` | Shared unit-link proposal | No |
| `/iAgencyAIA/:token` | Legacy redirect | No |
| `/iAgency/:token` | Shared business card | No |
| `/portfolio/:token` | Shared portfolio | No |
| `/apply/:token` | Public application form | No |
| `/view-application/:token` | View submitted application | No |

## Auth Flow

1. User signs up with email/password
2. `handle_new_fa_user()` trigger auto-creates `fa_profiles` + assigns `fa` role
3. User sees `/pending-approval` until admin approves (`fa_profiles.is_approved`)
4. Role system: `user_roles` table with enum `app_role` (admin, fa, user, full_control, bqm)
5. Page access controlled by `role_permissions` table

## PWA / Caching

- Service Worker with Workbox autoUpdate strategy
- IndexedDB for offline product data caching
- Session cache for frequently accessed queries
- Bundle splitting: 8 manual chunks (vendor-react, supabase, ui, charts, pdf, excel, utils, qr)
- Version checking on mount — forces cache clear on version mismatch

## CORS Origins

```
iagencyaiafatools.lovable.app
tools.iagencyaia.com
fatools.vuttipipat.com
localhost:5173
localhost:5174
```

## Lovable Deployment

FA Tools deploys through Lovable platform — NOT standard CI/CD:
- `lovable-tagger` dev dependency
- `.lovable/plan.md` directory
- No wrangler.toml, vercel.json, or Dockerfile
- Changes go through Lovable chat UI
- **Migration impact**: Need to update Lovable project settings for new Supabase URL
