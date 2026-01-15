from datetime import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from ami_meeting_svc.models import Meeting, User


def _create_user(session):
    user = User(username="testuser", email="testuser@example.com", password_hash="fakehash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_meeting_crud(db_session):
    session = db_session
    user = _create_user(session)

    meeting = Meeting(
        owner_id=user.id,
        title="Sprint Planning",
        date=datetime.utcnow(),
        attendees=["alice", "bob"],
        notes="Discuss sprint backlog"
    )

    # create
    session.add(meeting)
    session.commit()
    session.refresh(meeting)
    assert meeting.id is not None

    # read
    m = session.get(Meeting, meeting.id)
    assert m is not None
    assert m.title == "Sprint Planning"

    # update
    m.title = "Updated Title"
    session.commit()
    session.refresh(m)
    assert m.title == "Updated Title"

    # delete
    session.delete(m)
    session.commit()
    assert session.get(Meeting, meeting.id) is None


def test_owner_id_not_null(db_session):
    session = db_session
    meeting = Meeting(
        owner_id=None,
        title="No Owner",
        date=datetime.utcnow(),
        attendees=[],
        notes="No owner"
    )
    session.add(meeting)
    with pytest.raises(IntegrityError):
        session.commit()
