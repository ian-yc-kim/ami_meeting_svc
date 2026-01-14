import logging
import pytest
from sqlalchemy.exc import IntegrityError

from ami_meeting_svc.models import User


def test_create_read_update_delete(db_session):
    logger = logging.getLogger(__name__)
    try:
        user = User(username="alice", email="alice@example.com", password_hash="hash1")
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

        fetched = db_session.get(User, user.id)
        assert fetched.username == "alice"

        fetched.password_hash = "hash2"
        db_session.commit()
        assert db_session.get(User, user.id).password_hash == "hash2"

        db_session.delete(fetched)
        db_session.commit()
        assert db_session.get(User, user.id) is None
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def test_unique_constraints(db_session):
    logger = logging.getLogger(__name__)
    try:
        u1 = User(username="bob", email="bob@example.com", password_hash="h")
        db_session.add(u1)
        db_session.commit()

        u2 = User(username="bob", email="bob2@example.com", password_hash="h2")
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
    finally:
        try:
            db_session.rollback()
        except Exception:
            pass

    try:
        u3 = User(username="bob3", email="bob@example.com", password_hash="h3")
        db_session.add(u3)
        with pytest.raises(IntegrityError):
            db_session.commit()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
    finally:
        try:
            db_session.rollback()
        except Exception:
            pass
