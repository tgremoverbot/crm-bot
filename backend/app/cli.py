from __future__ import annotations

import argparse
import asyncio
import sys


async def _create_admin(email: str, password: str) -> None:
    from app.core.security import hash_password
    from app.db.session import get_engine, get_session_factory
    from app.repositories import admin_users as admin_repo

    get_engine()
    factory = get_session_factory()
    async with factory() as session:
        existing = await admin_repo.get_by_email(session, email)
        if existing:
            print(f"Error: admin '{email}' already exists.")
            sys.exit(1)
        admin = await admin_repo.create(
            session,
            email=email,
            password_hash=hash_password(password),
        )
        await session.commit()
        print(f"Admin created: {admin.email}  (id={admin.id})")


async def _list_admins() -> None:
    from sqlalchemy import select

    from app.db.session import get_engine, get_session_factory
    from app.models.admin_user import AdminUser

    get_engine()
    factory = get_session_factory()
    async with factory() as session:
        admins = (await session.scalars(select(AdminUser))).all()
        if not admins:
            print("No admin accounts found.")
            return
        for a in admins:
            print(f"{a.email}  (id={a.id}, active={a.is_active})")


async def _update_admin_email(current_email: str, new_email: str) -> None:
    from app.db.session import get_engine, get_session_factory
    from app.repositories import admin_users as admin_repo

    get_engine()
    factory = get_session_factory()
    async with factory() as session:
        admin = await admin_repo.get_by_email(session, current_email)
        if admin is None:
            print(f"Error: no admin found with email '{current_email}'.")
            sys.exit(1)
        conflict = await admin_repo.get_by_email(session, new_email)
        if conflict:
            print(f"Error: admin '{new_email}' already exists.")
            sys.exit(1)
        admin.email = new_email.lower()
        await session.commit()
        print(f"Admin email updated: {current_email} -> {admin.email}  (id={admin.id})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-admin", help="Bootstrap the first admin user")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)

    sub.add_parser("list-admins", help="List all admin accounts")

    p2 = sub.add_parser("update-admin-email", help="Change an existing admin's login email")
    p2.add_argument("--email", required=True, help="Current login email")
    p2.add_argument("--new-email", required=True, help="New login email")

    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(_create_admin(args.email, args.password))
    elif args.command == "list-admins":
        asyncio.run(_list_admins())
    elif args.command == "update-admin-email":
        asyncio.run(_update_admin_email(args.email, args.new_email))


if __name__ == "__main__":
    main()
