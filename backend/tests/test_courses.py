def test_user_course_identity_is_composite():
    from app.models.models import UserCourse
    assert set(UserCourse.__table__.primary_key.columns.keys()) == {"user_id", "course_offering_id"}
