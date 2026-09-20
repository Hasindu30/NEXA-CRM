import pytest
pytestmark = pytest.mark.asyncio(loop_scope='session')
import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, select
from app.modules.users.model import User
from app.modules.workspaces.model import Workspace, WorkspaceMembership



async def test_duplicate_normalized_email_rejected(db_session):
    email = "test@example.com"
    user1 = User(email=email)
    db_session.add(user1)
    await db_session.commit()
    
    user2 = User(email=email)
    db_session.add(user2)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "uq_users_email" in str(exc.value)

async def test_mixed_case_email_rejection(db_session):
    user = User(email="Test@Example.com")
    db_session.add(user)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "ck_users_email_lowercase" in str(exc.value)

async def test_whitespace_email_rejection(db_session):
    user = User(email=" test@example.com ")
    db_session.add(user)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "ck_users_email_lowercase" in str(exc.value)

async def test_duplicate_workspace_slug_rejected(db_session):
    slug = "acme-corp"
    w1 = Workspace(name="Acme", slug=slug)
    db_session.add(w1)
    await db_session.commit()
    
    w2 = Workspace(name="Acme 2", slug=slug)
    db_session.add(w2)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "uq_workspaces_slug" in str(exc.value)

async def test_invalid_slug_format_rejection(db_session):
    w1 = Workspace(name="Acme", slug="Invalid Slug!")
    db_session.add(w1)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "ck_workspaces_slug_format" in str(exc.value)

async def test_duplicate_workspace_membership_rejected(db_session):
    u = User(email="user@example.com")
    w = Workspace(name="Acme", slug="acme")
    db_session.add_all([u, w])
    await db_session.commit()
    
    m1 = WorkspaceMembership(user_id=u.id, workspace_id=w.id)
    db_session.add(m1)
    await db_session.commit()
    
    m2 = WorkspaceMembership(user_id=u.id, workspace_id=w.id)
    db_session.add(m2)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "pk_workspace_members" in str(exc.value)

async def test_invalid_user_foreign_key(db_session):
    w = Workspace(name="Acme", slug="acme")
    db_session.add(w)
    await db_session.commit()
    
    m = WorkspaceMembership(user_id=uuid.uuid4(), workspace_id=w.id)
    db_session.add(m)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "fk_workspace_members_user_id_users" in str(exc.value)

async def test_invalid_workspace_foreign_key(db_session):
    u = User(email="user@example.com")
    db_session.add(u)
    await db_session.commit()
    
    m = WorkspaceMembership(user_id=u.id, workspace_id=uuid.uuid4())
    db_session.add(m)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "fk_workspace_members_workspace_id_workspaces" in str(exc.value)

async def test_timestamps_persisted(db_session):
    u = User(email="time@example.com")
    db_session.add(u)
    await db_session.commit()
    
    # Refresh to get DB generated defaults
    await db_session.refresh(u)
    assert u.created_at is not None
    assert u.updated_at is not None

async def test_updated_at_behavior_after_update(db_session):
    w = Workspace(name="Acme", slug="acme")
    db_session.add(w)
    await db_session.commit()
    await db_session.refresh(w)
    
    import datetime
    # Artificially age the timestamp because Postgres now() is constant for the entire test transaction
    original_updated_at = w.updated_at - datetime.timedelta(seconds=1)
    
    # Update
    w.name = "Acme Inc"
    await db_session.commit()
    await db_session.refresh(w)
    
    assert w.updated_at > original_updated_at

async def test_on_delete_cascade_user_membership(db_session):
    u = User(email="del@example.com")
    w = Workspace(name="Del", slug="del")
    db_session.add_all([u, w])
    await db_session.commit()
    
    m = WorkspaceMembership(user_id=u.id, workspace_id=w.id)
    db_session.add(m)
    await db_session.commit()
    
    await db_session.delete(u)
    await db_session.commit()
    
    stmt = select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == w.id)
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 0

async def test_on_delete_cascade_workspace_membership(db_session):
    u = User(email="del2@example.com")
    w = Workspace(name="Del2", slug="del2")
    db_session.add_all([u, w])
    await db_session.commit()
    
    m = WorkspaceMembership(user_id=u.id, workspace_id=w.id)
    db_session.add(m)
    await db_session.commit()
    
    await db_session.delete(w)
    await db_session.commit()
    
    stmt = select(WorkspaceMembership).where(WorkspaceMembership.user_id == u.id)
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 0
