import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import AsyncSessionLocal
from app.models.models import User, Agent
from app.core.security import hash_password
from app.core.logger import get_logger

logger = get_logger(__name__)

# Beta Ltd tenant id from what we just created
BETA_TENANT_ID = "f63848c8-3234-4cf0-8ba5-3ff6e5951e02"


async def create_beta_data():
    async with AsyncSessionLocal() as db:

        # create admin user for Beta Ltd
        user = User(
            tenant_id=BETA_TENANT_ID,
            email="admin@beta.com",
            hashed_password=hash_password("password123"),
            role="admin",
            is_active=True
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created Beta user: {user.email} id={user.id}")

        # create support agent for Beta Ltd
        agent = Agent(
            tenant_id=BETA_TENANT_ID,
            name="Support Agent",
            slug="support-agent",
            system_prompt="You are a helpful support agent. Answer questions based on support documentation.",
            tools_enabled=[],
            is_active=True
        )
        db.add(agent)
        await db.flush()
        logger.info(f"Created Beta agent: {agent.name} id={agent.id}")

        await db.commit()

        print(f"\nBeta Ltd Data Created:")
        print(f"Tenant ID: {BETA_TENANT_ID}")
        print(f"User:      admin@beta.com / password123")
        print(f"Agent:     {agent.name} (id: {agent.id})")


if __name__ == "__main__":
    asyncio.run(create_beta_data())