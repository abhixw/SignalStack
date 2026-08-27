"""One-off CLI to promote an existing user to the admin role.

Admin accounts are intentionally not self-registerable via POST /auth/register.
Usage (run from backend/):
    venv/bin/python scripts/promote_admin.py user@example.com
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import AsyncMongoClient  # noqa: E402

from app.config.config import config  # noqa: E402
from app.constants import UserRole  # noqa: E402


async def main(email: str):
    client = AsyncMongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        db = client[config.MONGODB_ACTIVE_DATABASE]
        result = await db.users.update_one({"email": email}, {"$set": {"role": UserRole.ADMIN}})
        if result.matched_count == 0:
            print(f"No user found with email {email}. Register the account first via POST /auth/register.")
            sys.exit(1)
        print(f"{email} is now an admin.")
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
