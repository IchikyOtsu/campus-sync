def test_user_pae_course_identity_is_composite():
    from app.models.models import UserPAECourse
    assert set(UserPAECourse.__table__.primary_key.columns.keys()) == {"user_pae_id", "course_offering_id"}
