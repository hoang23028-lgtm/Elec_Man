# Architecture

This is a simple single-server deployment. Nginx routes same-origin browser traffic to Next.js and FastAPI. FastAPI communicates with PostgreSQL and local volume-backed storage. A separate worker will claim PostgreSQL jobs in Phase 4. PostgreSQL is private to the Docker network; Nginx is the only published service.

AI dependencies and model loading are intentionally absent from Phase 1, preserving a narrow future worker/pipeline boundary.
