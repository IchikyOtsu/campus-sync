from app.db.seed import SEED_COURSES


def test_ulb_mapping_to_provider_codes():
    assert ("INFO-Y024", "uclouvain", "LINFO2145", "Cloud Computing") in SEED_COURSES
