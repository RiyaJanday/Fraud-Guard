"""
One-off terminal script: (1) list which account(s) are Admin, and
(2) optionally set a new password for one of them — using the EXACT same
bcrypt hashing the app itself uses (passlib CryptContext(schemes=["bcrypt"])
from app/core/security.py), so the new password actually works with the
real /auth/login endpoint afterward. Manually writing some other hash
format here would silently break login instead.

Usage:
    cd fraudguard-backend

    # Just list admin accounts (read-only, safe to run anytime):
    python manage_admin.py --database-url "postgresql+psycopg2://user:pass@host/db" --list

    # Set a new password for a specific admin account:
    python manage_admin.py --database-url "postgresql+psycopg2://user:pass@host/db" --email admin@example.com --set-password "NewStrongPass123"

Getting --database-url: same one you already used for
register_production_model.py — Render dashboard -> your Postgres service ->
Connect -> External Database URL, with postgresql:// changed to
postgresql+psycopg2://.

This directly edits the users table; it does not go through the API, so it
also bypasses the app's own password-strength Pydantic validation (see
UserRegister/ChangePasswordRequest schemas) — pick a password that would
pass those rules anyway (8+ chars, at least one letter and one digit).
"""

import argparse

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main() -> None:
    parser = argparse.ArgumentParser(description="List admin accounts and/or reset an account's password directly in the database.")
    parser.add_argument("--database-url", required=True, help="postgresql+psycopg2://... connection string")
    parser.add_argument("--list", action="store_true", help="List all admin accounts")
    parser.add_argument("--email", help="Email of the account to update (used with --set-password)")
    parser.add_argument("--set-password", dest="new_password", help="New password to set for --email")
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        if args.list or not args.new_password:
            admins = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.created_at).all()
            if not admins:
                print("No admin accounts found.")
            else:
                print(f"Found {len(admins)} admin account(s):\n")
                for u in admins:
                    print(f"  {u.email:<35} name={u.full_name!r:<25} active={u.is_active} created={u.created_at}")

        if args.new_password:
            if not args.email:
                raise SystemExit("--email is required when using --set-password.")

            user = db.query(User).filter(User.email == args.email).first()
            if not user:
                raise SystemExit(f"No account found with email {args.email!r}.")

            if len(args.new_password) < 8:
                raise SystemExit("Password must be at least 8 characters (matches the app's own validation).")

            user.hashed_password = pwd_context.hash(args.new_password)
            db.commit()
            print(f"\nPassword updated for {user.email} (role={user.role.value}).")
            print("Log in at /login with this new password immediately — old sessions for this")
            print("account remain valid until their tokens naturally expire (this script doesn't")
            print("blacklist existing tokens; use the app's own Settings > Security > Change")
            print("Password flow instead if you specifically need that).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
