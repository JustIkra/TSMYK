#!/usr/bin/env sh
set -eu

echo "=== Bootstrapping API service ==="

vpn_flag="$(printf '%s' "${VPN_ENABLED:-0}" | tr '[:upper:]' '[:lower:]')"
if [ "$vpn_flag" = "1" ] || [ "$vpn_flag" = "true" ] || [ "$vpn_flag" = "yes" ] || [ "$vpn_flag" = "on" ]; then
    echo "Ensuring WireGuard/AWG interface before starting the app..."
    if ! python -m app.core.vpn_bootstrap; then
        echo "ERROR: VPN bootstrap failed! Application will not start without VPN." >&2
        exit 1
    fi
    echo "VPN interface is up and running."
fi

echo "Checking database state..."
# Detect broken state: alembic_version exists but core tables don't
# This can happen if migrations were interrupted or volume was corrupted
if python -c "
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

dsn = str(settings.POSTGRES_DSN).replace('+asyncpg', '')
engine = create_engine(dsn)
with engine.connect() as conn:
    # Check if alembic_version table exists and has records
    result = conn.execute(text(\"\"\"
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'alembic_version'
        )
    \"\"\"))
    has_alembic = result.scalar()

    if has_alembic:
        result = conn.execute(text('SELECT COUNT(*) FROM alembic_version'))
        version_count = result.scalar()

        # Check if 'user' table exists (core table created in first migration)
        result = conn.execute(text(\"\"\"
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'user'
            )
        \"\"\"))
        has_user_table = result.scalar()

        if version_count > 0 and not has_user_table:
            print('BROKEN_STATE')
            sys.exit(0)

    print('OK')
" 2>/dev/null | grep -q "BROKEN_STATE"; then
    echo "WARNING: Detected broken database state (alembic_version exists but tables missing)"
    echo "Resetting alembic_version to allow fresh migration..."
    python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
dsn = str(settings.POSTGRES_DSN).replace('+asyncpg', '')
engine = create_engine(dsn)
with engine.connect() as conn:
    conn.execute(text('DELETE FROM alembic_version'))
    conn.commit()
print('alembic_version reset successfully')
"
fi

echo "Applying database migrations..."
# Use 'heads' to handle multiple head revisions (merge migrations)
if ! alembic upgrade heads; then
    echo "ERROR: Failed to apply database migrations!" >&2
    exit 1
fi
echo "Database migrations applied successfully."

echo "Creating default admin user..."
if ! python create_admin.py admin@test.com admin123; then
    echo "WARNING: Failed to create default admin user (may already exist)" >&2
fi

echo "Starting application..."
exec python main.py
