from langgraph.graph import StateGraph, START, END

from app.ecommerce.graph.state import RefundAgentState
from app.ecommerce.graph.nodes import (
    verify_order_node,
    policy_check_node,
    risk_assessment_node,
    decision_node,
    execute_refund_node,
    pending_review_node,
)
from app.ecommerce.graph.edges import route_after_verification


def route_after_decision(state: RefundAgentState):
    decision = state.get("decision")

    if decision == "auto_approve":
        return "execute"

    if decision == "human_review":
        return "review"

    return "end"


def build_refund_graph():
    graph = StateGraph(RefundAgentState)

    graph.add_node("verify_order", verify_order_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("decision", decision_node)
    graph.add_node("execute_refund", execute_refund_node)
    graph.add_node("pending_review", pending_review_node)

    graph.add_edge(START, "verify_order")

    graph.add_conditional_edges(
        "verify_order",
        route_after_verification,
        {
            "policy": "policy_check",
            "decision": "decision",
        },
    )

    graph.add_edge("policy_check", "risk_assessment")
    graph.add_edge("risk_assessment", "decision")

    graph.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "execute": "execute_refund",
            "review": "pending_review",
            "end": END,
        },
    )

    graph.add_edge("execute_refund", END)
    graph.add_edge("pending_review", END)

    return graph.compile()


refund_graph = build_refund_graph()
