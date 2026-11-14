from app.ecommerce.graph.state import RefundAgentState


def route_after_verification(state: RefundAgentState):
    if not state.get("order_verified"):
        return "decision"
    return "policy"


def route_after_risk(state: RefundAgentState):
    return "decision"
