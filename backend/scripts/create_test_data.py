import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import AsyncSessionLocal
from app.models.models import Tenant, User, Agent
from app.core.security import hash_password
from app.core.logger import get_logger

logger = get_logger(__name__)


async def create_test_data():
    """Creates a test tenant, user and agent for development."""
    
    async with AsyncSessionLocal() as db:
        # Create test tenant
        tenant = Tenant(
            name="Acme Corp",
            slug="acme-corp",
            is_active=True
        )
        db.add(tenant)
        await db.flush()  # get the tenant id without committing
        logger.info(f"Created tenant: {tenant.name} id={tenant.id}")

        # Create admin user
        user = User(
            tenant_id=tenant.id,
            email="admin@acme.com",
            hashed_password=hash_password("password123"),
            role="admin",
            is_active=True
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created user: {user.email} id={user.id}")

        # Create HR agent
        agent = Agent(
            tenant_id=tenant.id,
            name="HR Agent",
            slug="hr-agent",
            system_prompt="You are a helpful HR assistant. Answer questions based on company HR policies.",
            tools_enabled=[],
            is_active=True
        )
        db.add(agent)
        await db.flush()
        logger.info(f"Created agent: {agent.name} id={agent.id}")

        await db.commit()
        logger.info("Test data created successfully")
        
        print(f"\nTest Data Created:")
        print(f"Tenant:  {tenant.name} (id: {tenant.id})")
        print(f"User:    {user.email} / password123 (id: {user.id})")
        print(f"Agent:   {agent.name} (id: {agent.id})")


if __name__ == "__main__":
    asyncio.run(create_test_data())