# Admin Setup Guide

## Default Admin Credentials

After running migration `005_add_admin_tables.sql`, a default admin account is automatically created:

```
Email: admin@example.com
Password: admin123
```

## ⚠️ SECURITY WARNING

**Change the default password immediately after first login!**

The default credentials are public knowledge and should never be used in production.

## First Login

1. Navigate to the admin page: `http://localhost:3000/admin.html`
2. Log in with the default credentials above
3. Immediately change your password (feature coming in User Story 2)

## Creating Additional Admin Users

Additional admin users can be created via the admin API (User Story 2 feature):

```bash
POST /admin/users
Content-Type: application/json

{
  "email": "newadmin@example.com",
  "password": "secure-password-here",
  "roles": ["admin"]
}
```

## Password Requirements

- Minimum 8 characters
- Hashed with Argon2id (64 MiB memory, 3 iterations)
- Passwords never stored in plain text

## Roles

- **admin**: Full access to user management, category management, and timeline uploads
- **user**: (Reserved for future features) Standard timeline access only

## Authentication Model

### Two-Tier Authentication

1. **Anonymous Tokens** (`POST /token`)
   - No credentials required
   - Grants `"public"` scope for read-only timeline access
   - Discourages automated scrapers (requires cookie/JS support)

2. **Admin Tokens** (`POST /admin/login`)
   - Requires email/password
   - Grants `["public", "admin"]` scopes
   - Full access to privileged operations

### Scopes

| Scope | Access Level |
|-------|-------------|
| `public` | Read-only access to `/events`, `/categories`, `/search`, `/stats` |
| `admin` | Write access to `/admin/*` endpoints |

## Troubleshooting

### Can't log in

1. Verify the database migration was applied:
   ```bash
   docker exec -it timeline-db psql -U timeline_user -d timeline_history -c "SELECT email FROM users;"
   ```

2. Check API logs:
   ```bash
   docker logs timeline-api --tail 50
   ```

3. Verify CORS is configured correctly for your frontend origin

### Reset admin password

If you forget the admin password, you can reset it directly in the database:

```bash
# Generate a new hash (replace 'newpassword' with your desired password)
cd api && python -c "from auth.password_service import hash_password; print(hash_password('newpassword'))"

# Update the database (replace the hash with the one generated above)
docker exec -it timeline-db psql -U timeline_user -d timeline_history -c \
  "UPDATE users SET password_hash = '\$argon2id\$v=19\$m=65536,t=3,p=4\$...' WHERE email = 'admin@example.com';"
```

## Security Best Practices

1. Change default credentials immediately
2. Use strong, unique passwords (12+ characters recommended)
3. Limit admin access to trusted users only
4. Regularly review user accounts and remove inactive accounts
5. Monitor admin activity logs
6. Use HTTPS in production (configured in reverse proxy)
