import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.graph.state import RefundCaseState
from app.graph.nodes import extract_evidence_node, audit_evidence_node, rule_engine_node, draft_claim_node, dispatch_claim_node
from app.graph.edges import route_after_audit, route_after_rule_engine

load_dotenv()
CHECKPOINT_PATH = Path(os.getenv('CHECKPOINT_DATABASE_PATH', 'data/refund_checkpoints.sqlite'))
CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
_connection = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False, timeout=30)
_checkpointer = SqliteSaver(_connection)
_checkpointer.setup()


def build_workflow():
    builder = StateGraph(RefundCaseState)
    builder.add_node('extract_evidence_node', extract_evidence_node)
    builder.add_node('audit_evidence_node', audit_evidence_node)
    builder.add_node('rule_engine_node', rule_engine_node)
    builder.add_node('draft_claim_node', draft_claim_node)
    builder.add_node('dispatch_claim_node', dispatch_claim_node)
    builder.add_edge(START, 'extract_evidence_node')
    builder.add_edge('extract_evidence_node', 'audit_evidence_node')
    builder.add_conditional_edges('audit_evidence_node', route_after_audit, {'rule_engine_node': 'rule_engine_node', 'end': END})
    builder.add_conditional_edges('rule_engine_node', route_after_rule_engine, {'draft_claim_node': 'draft_claim_node', 'end': END})
    builder.add_edge('draft_claim_node', 'dispatch_claim_node')
    return builder.compile(checkpointer=_checkpointer, interrupt_before=['dispatch_claim_node'])


refund_graph = build_workflow()


def run_refund_case(initial_state: dict, thread_id: str) -> dict:
    config = {'configurable': {'thread_id': thread_id}}
    initial_state = {**initial_state, 'thread_id': thread_id, 'approval_status': 'not_requested'}
    return refund_graph.invoke(initial_state, config=config)


def approve_refund_case(thread_id: str) -> dict:
    config = {'configurable': {'thread_id': thread_id}}
    snapshot = refund_graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise ValueError('Refund case workflow checkpoint not found.')
    state = snapshot.values
    if 'dispatch_claim_node' not in snapshot.next:
        raise ValueError('This case is not waiting for human approval.')
    if state.get('eligible_for_compensation') is not True or not state.get('drafted_email'):
        raise ValueError('This case is not eligible or its claim draft is missing.')
    refund_graph.update_state(config, {'approval_status': 'approved'})
    return refund_graph.invoke(None, config=config)


def reject_refund_case(thread_id: str) -> dict:
    config = {'configurable': {'thread_id': thread_id}}
    snapshot = refund_graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise ValueError('Refund case workflow checkpoint not found.')
    if 'dispatch_claim_node' not in snapshot.next:
        raise ValueError('This case is not waiting for human approval.')
    refund_graph.update_state(config, {'approval_status': 'rejected', 'status': 'rejected'})
    return refund_graph.get_state(config).values


def get_workflow_state(thread_id: str) -> dict:
    snapshot = refund_graph.get_state({'configurable': {'thread_id': thread_id}})
    return dict(snapshot.values) if snapshot and snapshot.values else {}
