# Security Principles

*(Note: These are future principles to be implemented)*

- Password hashing: Argon2id
- Tokens: Short-lived access tokens with rotating refresh sessions
- Cookies: HttpOnly Secure for session/tokens
- CSRF Protection
- CORS: Strict allow-origins
- Authorization: RBAC and Workspace isolation
- Database: PostgreSQL RLS
- Infrastructure: Rate limiting, Audit logging, Secrets management
