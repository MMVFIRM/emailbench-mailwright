from emailbench.api import EmailBenchAPI
from emailbench.llm import MockLLM
from framework.agent import FrameworkAgent


def test_framework_loop_autopage_and_verify():
    script = [
        '{"requirements": ["count unread"], "report": ["count"], "constraints": [], "unavailable": []}',   # plan
        [("messages_list", {"folderId": "inbox", "filter": "isRead eq false", "top": 5})],                  # act
        "You have 16 unread emails.",                                                                         # answer
        '{"complete": true, "gaps": [], "answer_fixes": []}',                                                 # verify
    ]
    api = EmailBenchAPI()
    ag = FrameworkAgent(MockLLM(script))
    out = ag.run("How many unread emails?", api)
    assert out["answer"] == "You have 16 unread emails."
    assert out["trace"][0]["result"].count('"id":"msg-') == 16          # autopage ignored top=5 and fetched all
    assert out["extra"]["verify_rounds"] == 1


def test_framework_feedback_round():
    script = ['{}', "done", '{"complete": false, "gaps": ["msg-012 not marked read"]}',
              [("messages_update", {"id": "msg-012", "patch": {"isRead": True}})], "Marked msg-012 read.", '{"complete": true}']
    api = EmailBenchAPI()
    out = FrameworkAgent(MockLLM(script)).run("Mark GasBank emails read", api)
    assert out["answer"] == "Marked msg-012 read." and api.snapshot()["messages"][11]["isRead"]
