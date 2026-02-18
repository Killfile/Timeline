-- Migration 005: Add admin authentication and category management tables

-- Create update_updated_at_column function (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_users_updated_at'
        AND tgrelid = 'users'::regclass
    ) THEN
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- Seed roles
INSERT INTO roles (name, description) VALUES
    ('admin', 'Administrator with full access to user and category management'),
    ('user', 'Regular user with standard timeline access (reserved for future features)')
ON CONFLICT (name) DO NOTHING;

-- User-Role junction table
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    assigned_by INTEGER REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- Timeline Categories table
CREATE TABLE IF NOT EXISTS timeline_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    strategy_name VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_timeline_categories_name ON timeline_categories(name);
CREATE INDEX IF NOT EXISTS idx_timeline_categories_strategy ON timeline_categories(strategy_name);
CREATE INDEX IF NOT EXISTS idx_timeline_categories_metadata ON timeline_categories USING gin(metadata);

-- Create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_timeline_categories_updated_at'
        AND tgrelid = 'timeline_categories'::regclass
    ) THEN
        CREATE TRIGGER update_timeline_categories_updated_at
            BEFORE UPDATE ON timeline_categories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Add category_id to historical_events (new foreign key)
ALTER TABLE historical_events
ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_historical_events_category_id ON historical_events(category_id);

-- Ingestion Uploads table
CREATE TABLE IF NOT EXISTS ingestion_uploads (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES timeline_categories(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    events_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    uploaded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingestion_uploads_category_id ON ingestion_uploads(category_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_uploads_uploaded_by ON ingestion_uploads(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_ingestion_uploads_status ON ingestion_uploads(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_uploads_uploaded_at ON ingestion_uploads(uploaded_at DESC);

-- Create default admin user
-- Default credentials: admin@example.com / admin123
-- **IMPORTANT**: Change this password immediately after first login!
DO $$
DECLARE
    admin_user_id INTEGER;
    admin_role_id INTEGER;
BEGIN
    -- Check if default admin already exists
    IF NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@example.com') THEN
        -- Insert default admin user
        INSERT INTO users (email, password_hash, is_active)
        VALUES (
            'admin@example.com',
            '$argon2id$v=19$m=65536,t=3,p=4$hz3IC5+nY87BwiLc5v0DRg$xWVwpdUGWwluYFN3JsdmSeeALTniub6vhIcFb3gyeVM',
            TRUE
        )
        RETURNING id INTO admin_user_id;

        -- Get admin role ID
        SELECT id INTO admin_role_id FROM roles WHERE name = 'admin';

        -- Assign admin role to default user
        INSERT INTO user_roles (user_id, role_id)
        VALUES (admin_user_id, admin_role_id);

        RAISE NOTICE 'Default admin user created: admin@example.com / admin123';
        RAISE NOTICE 'SECURITY WARNING: Change the default password immediately!';
    END IF;
END $$;
