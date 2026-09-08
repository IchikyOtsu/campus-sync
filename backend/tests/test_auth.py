def test_no_password_column_is_stored():
    from app.models.models import UserProfile
    assert "password" not in UserProfile.__table__.columns
