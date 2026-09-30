"""Every scenario must be solvable: its reference oracle passes all static assertions,
and a do-nothing agent must fail every write scenario's critical static checks."""
import pytest

from emailbench.api import EmailBenchAPI
from emailbench.grader import grade
from emailbench.scenarios import all_scenarios, holdout2_scenarios

SC = all_scenarios() + holdout2_scenarios()


@pytest.mark.parametrize("sc", SC, ids=[s.id for s in SC])
def test_oracle_passes_static(sc):
    api = EmailBenchAPI()
    assert sc.oracle is not None, "missing oracle"
    answer = sc.oracle(api)
    g = grade(sc, api.snapshot(), answer, [], judge=None)
    failed = [x["desc"] for x in g["static"] if not x["passed"]]
    assert not failed, f"{sc.id} oracle failed: {failed}; answer={answer!r}"


@pytest.mark.parametrize("sc", SC, ids=[s.id for s in SC])
def test_empty_agent_fails(sc):
    api = EmailBenchAPI()
    g = grade(sc, api.snapshot(), "I have completed the task.", [], judge=None)
    # a generic non-answer with no actions should not pass the static critical checks
    if sc.id in ("MD-003",):  # correct behaviour is "no action" + explanation, judged by rubric
        return
    assert not (g["critical_ok"] and g["s_static"] == 1.0), f"{sc.id} passes with an empty agent"
