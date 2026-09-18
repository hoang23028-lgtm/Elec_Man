# Backup and restore

Back up PostgreSQL, original/derived image storage, and model bundles as separate artifacts. Backups are written below `backups/<UTC timestamp>/` with SHA-256 checksums.

Windows development:

```powershell
.\scripts\backup.ps1 -EnvFile .env.example
```

Ubuntu production:

```bash
ENV_FILE=.env ./scripts/backup.sh
```

Copy completed backup directories to separate storage or a NAS. A backup remaining only on the application server is not sufficient.

Restore is destructive and intentionally requires an explicit switch. Stop user traffic first, verify the selected timestamp, and run:

```powershell
.\scripts\restore.ps1 -BackupDirectory .\backups\20260918T120000Z -EnvFile .env -ConfirmRestore
```

The restore script verifies checksums, stops application services, replaces the database schema and storage/model volumes, then starts the stack. Test restores regularly on a non-production server. Never use a live PostgreSQL data-directory copy as the primary database backup.

To install a candidate model into the protected model volume, run `install-model.ps1`, record its returned SHA-256, then register the relative path and checksum in the administration UI. Registration does not activate or hot-load a model.
