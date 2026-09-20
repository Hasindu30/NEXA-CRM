# Architecture

## Stack
- Next.js frontend (App Router)
- FastAPI backend
- PostgreSQL database
- Redis (future for caching/workers)

## Modular Monolith
The backend is a single deployed unit structured internally by feature domains (`app/modules/<module_name>/`).

## Layering
- **Routers**: HTTP concerns only.
- **Services**: Business logic and Unit of Work (transactions).
- **Repositories**: Database access (no commits here).

## Multi-Tenancy
The tenant concept is a `Workspace`. 
Future implementation will use `workspace_id` for scoping and PostgreSQL Row Level Security (RLS) as defense-in-depth.
