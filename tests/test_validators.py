import pytest

from intent_compiler.errors import ValidationFailure
from intent_compiler.models import ActionPlan, ActionStep
from intent_compiler.validators import validate_plan


def test_plan_rejects_missing_dependency():
    step = ActionStep(
        title="second",
        owner="owner",
        dependencies=["missing"],
        acceptance_criteria=["done"],
        checkpoint="review",
    )
    plan = ActionPlan(
        objective_id="obj-1",
        steps=[step],
        stopping_conditions=["complete"],
    )
    with pytest.raises(ValidationFailure, match="missing dependency"):
        validate_plan(plan)


def test_plan_rejects_cycle():
    first = ActionStep(
        step_id="a",
        title="a",
        owner="owner",
        dependencies=["b"],
        acceptance_criteria=["done"],
        checkpoint="review",
    )
    second = ActionStep(
        step_id="b",
        title="b",
        owner="owner",
        dependencies=["a"],
        acceptance_criteria=["done"],
        checkpoint="review",
    )
    plan = ActionPlan(
        objective_id="obj-1",
        steps=[first, second],
        stopping_conditions=["complete"],
    )
    with pytest.raises(ValidationFailure, match="cycle"):
        validate_plan(plan)
