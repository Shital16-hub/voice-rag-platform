from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Tenant, Agent, User
from app.core.security import hash_password
from app.core.logger import get_logger

logger = get_logger(__name__)


async def create_tenant(
    name: str,
    slug: str,
    db: AsyncSession
) -> Tenant:
    """Create a new tenant."""

    # check slug is unique
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Tenant slug already exists: {slug}")

    tenant = Tenant(name=name, slug=slug, is_active=True)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant created name={name} id={tenant.id}")
    return tenant


async def create_agent(
    tenant_id: str,
    name: str,
    slug: str,
    system_prompt: str,
    db: AsyncSession
) -> Agent:
    """Create a new agent for a tenant."""

    agent = Agent(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        system_prompt=system_prompt,
        tools_enabled=[],
        is_active=True
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    logger.info(
        f"Agent created "
        f"name={name} "
        f"tenant_id={tenant_id} "
        f"id={agent.id}"
    )
    return agent


async def create_user(
    tenant_id: str,
    email: str,
    password: str,
    role: str,
    db: AsyncSession
) -> User:
    """Create a new user for a tenant."""

    # check email unique within tenant
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.tenant_id == tenant_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Email already exists: {email}")

    user = User(
        tenant_id=tenant_id,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        f"User created "
        f"email={email} "
        f"tenant_id={tenant_id} "
        f"id={user.id}"
    )
    return user


async def get_all_tenants(db: AsyncSession) -> list[Tenant]:
    """Get all tenants. Platform admin only."""
    result = await db.execute(select(Tenant))
    return result.scalars().all()


async def get_tenant_agents(
    tenant_id: str,
    db: AsyncSession
) -> list[Agent]:
    """Get all agents for a tenant."""
    result = await db.execute(
        select(Agent).where(Agent.tenant_id == tenant_id)
    )
    return result.scalars().all()