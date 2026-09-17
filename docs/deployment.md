# Deployment foundation

Copy `.env.example` to `.env`; set a strong PostgreSQL password and update the password in `DATABASE_URL` to match. Start with `docker compose up --build`. Confirm the liveness and readiness endpoints through Nginx.

For production, terminate HTTPS with a trusted internal certificate and configure HSTS only after all access is HTTPS. Do not publish PostgreSQL ports. Persistent volumes retain database, storage, model, and log data.
