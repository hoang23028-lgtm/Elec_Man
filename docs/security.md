# Security and authentication

Phase 2 uses one administrator account, Argon2id password hashes, opaque server-side sessions, and HttpOnly cookies. The database stores only SHA-256 session and CSRF-token hashes. Cookies are `Secure` in production and use `SameSite=Strict`.

All authenticated state-changing endpoints require the `X-CSRF-Token` returned on login. The frontend should keep that non-credential CSRF token only in memory, never in localStorage. Login attempts are limited in memory to five attempts per IP/username combination per 15 minutes, suitable for this one-server scope.

Create the administrator after migrations:

```powershell
$env:ADMIN_INITIAL_PASSWORD = "a-long-unique-password"
docker compose exec backend python -m app.scripts.init_admin --username admin_operator
Remove-Item Env:ADMIN_INITIAL_PASSWORD
```

For production, set `SESSION_SECRET` to a unique random value of at least 32 characters. Startup rejects the example placeholder in production. Never commit `.env`.
