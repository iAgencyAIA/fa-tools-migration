# FA Tools — Encryption Audit

## Overview

FA Tools uses **AES-256-GCM** encryption for Personally Identifiable Information (PII) in compliance with PDPA.

## Encryption Details

| Property | Value |
|----------|-------|
| Algorithm | AES-256-GCM |
| Key | 32-byte hex string stored as Supabase Edge Function secret (`ENCRYPTION_KEY`) |
| IV | Random 12-byte IV per encryption (stored with ciphertext) |
| Format | `enc:` prefix + base64(IV + ciphertext + auth tag) |
| Implementation | Web Crypto API (SubtleCrypto) |

## Encrypted Fields

### `leads` table
- `first_name`
- `last_name`
- `phone`
- `email`
- `line_id`
- `notes`

### `insurance_applications` table
- PII fields in the multi-step application form

## Migration Risk: CRITICAL

**The ENCRYPTION_KEY is the single most critical secret in this migration.**

If the key is:
- **Lost** → All encrypted PII is permanently unreadable
- **Changed** → Existing encrypted data can't be decrypted
- **Exposed** → All customer PII is compromised (PDPA violation)

## Migration Steps

1. **Get the current ENCRYPTION_KEY** from old Supabase Edge Function secrets
   - Cannot be read via API — must be known or retrieved from secure storage
   - แบงค์ has this key
2. **Set the SAME key** on the new project: `supabase secrets set ENCRYPTION_KEY=<same-key>`
3. **Verify** by decrypting a known record on the new project
4. **Never** store the key in git, .env files, or any unencrypted location

## Where the Key is Used

| Function | Operation |
|----------|-----------|
| `encrypt-decrypt` | Main encrypt/decrypt endpoint |
| `submit-lead` | Encrypts PII on lead submission |
| `sync-application-to-lead` | Encrypts PII when syncing app→lead |
| `migrate-encrypt` | Batch encrypts existing unencrypted records |

## Test Plan

After migration:
1. Create a new lead via the app → verify `enc:` prefix in DB
2. View the lead in the dashboard → verify PII decrypts correctly
3. Submit a public application form → verify encryption works end-to-end
