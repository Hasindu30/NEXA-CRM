# Database Conventions

- Engine: PostgreSQL
- Primary Keys: UUIDs
- Isolation: `workspace_id` tenant isolation
- ORM: SQLAlchemy 2 async
- Migrations: Alembic
- Rules: Repositories handle queries, Services handle transactions
- Strategy: Indexes on foreign keys and tenant lookups, soft delete where appropriate.
