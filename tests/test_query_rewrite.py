from app.services.query_rewrite_service import QueryRewriteService


def test_rule_rewrite_uses_related_context_from_summary() -> None:
    service = QueryRewriteService()

    result = service.rewrite_with_rules(
        question="那热插拔恢复时间要求是多少？",
        conversation_summary=(
            "user: 接口稳定性测试里对热插拔有什么要求 | "
            "assistant: 根据接口稳定性测试规范，光模块热插拔后接口应在 30 秒内恢复"
        ),
        recent_turns=[
            {"role": "user", "content": "接口稳定性测试里对热插拔有什么要求"},
            {"role": "assistant", "content": "根据接口稳定性测试规范，光模块热插拔后接口应在 30 秒内恢复"},
        ],
    )

    assert result.strategy == "rule_context"
    assert "热插拔" in result.rewritten_question
    assert "相关上下文" in result.rewritten_question


def test_rule_rewrite_uses_previous_user_turn_for_pronouns() -> None:
    service = QueryRewriteService()

    result = service.rewrite_with_rules(
        question="那它支持哪些协议？",
        conversation_summary="user: 某型号交换机支持哪些管理功能",
        recent_turns=[
            {"role": "user", "content": "某型号交换机支持哪些管理功能"},
            {"role": "assistant", "content": "支持 SNMP、SSH、Telnet 等"},
        ],
    )

    assert result.strategy == "rule_followup"
    assert "某型号交换机支持哪些管理功能" in result.rewritten_question
    assert "支持哪些协议" in result.rewritten_question
