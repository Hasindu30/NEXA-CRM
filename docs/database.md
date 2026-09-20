# Database Conventions

- Engine: PostgreSQL (Source of Truth)
- Primary Keys: UUIDs
- Isolation: `workspace_id` tenant isolation
- ORM: SQLAlchemy 2 async (Data-access foundation)
- Driver: asyncpg
- Migrations: Alembic (Owns all schema migrations)
- Rules: 
  - Repositories handle queries but do NOT own commits.
  - Services / Unit of Work boundary owns transaction commits and rollbacks.
- Strategy: Indexes on foreign keys and tenant lookups, soft delete where appropriate.
