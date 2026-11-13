from typing import Literal
from app.graph.state import RefundCaseState


def route_after_audit(state: RefundCaseState) -> Literal['rule_engine_node', 'end']:
    return 'rule_engine_node' if state.get('is_evidence_valid') is True else 'end'


def route_after_rule_engine(state: RefundCaseState) -> Literal['draft_claim_node', 'end']:
    if state.get('status') == 'evidence_invalid':
        return 'end'
    return 'draft_claim_node' if state.get('eligible_for_compensation') is True else 'end'
