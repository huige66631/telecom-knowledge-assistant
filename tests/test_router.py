from app.agent.router import KBFirstRouter


def test_router_marks_out_of_scope_query() -> None:
    router = KBFirstRouter()

    route = router.decide({"question": "今天天气怎么样", "matches": []})

    assert route == "out_of_scope"


def test_router_marks_clarify_when_no_matches() -> None:
    router = KBFirstRouter()

    route = router.decide({"question": "某设备支持哪些协议", "matches": []})

    assert route == "clarify"
