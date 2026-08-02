from intent_compiler.models import ObjectiveSpecification
from intent_compiler.storage import JsonStore


def test_store_round_trip(tmp_path):
    store = JsonStore(tmp_path)
    objective = ObjectiveSpecification(
        desired_outcome="Create a verified bounded output for testing.",
        primary_user="tester",
        scope=["one file"],
        success_criteria=["file verified"],
        consequence_of_failure="test fails",
    )
    store.save_artifact(objective)
    loaded = store.load_artifact(objective.artifact_id, ObjectiveSpecification)
    assert loaded == objective
