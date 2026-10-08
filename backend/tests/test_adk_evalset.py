from google.adk.evaluation.eval_set import EvalSet

from app.evaluation.trajectory.export import build_evalset


def test_adk_evalset_contract():
    dataset = EvalSet.model_validate(build_evalset())
    assert len(dataset.eval_cases) == 3
