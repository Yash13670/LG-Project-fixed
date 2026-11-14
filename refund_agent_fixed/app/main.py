import os
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv

from app.database import initialize_database, create_case, get_case, update_case, get_escalated_cases, get_all_cases
from app.graph.workflow import run_refund_case, approve_refund_case, reject_refund_case, get_workflow_state

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}

app = FastAPI(title='Autonomous Refund & Chargeback Recovery Agent',
              description='Evidence extraction, deterministic TAT assessment and human-approved claim drafting.',
              version='2.0.0')


@app.on_event('startup')
def startup_event():
    initialize_database()


def _public_state(state: dict) -> dict:
    keys = ['category', 'transaction_id', 'merchant_name', 'amount', 'transaction_date',
            'upi_transaction_type', 'is_domestic', 'is_evidence_valid', 'missing_info_prompt',
            'assessment_date', 'tat_days', 'deadline_passed', 'delay_days', 'penalty_owed',
            'eligible_for_compensation', 'rule_applicable', 'rule_reason', 'drafted_email',
            'approval_status', 'status', 'dispatch_error', 'extraction_notes']
    return {key: state.get(key) for key in keys if key in state}


@app.get('/')
def home():
    return {'message': 'Refund Recovery Agent API is running.', 'status': 'active'}


@app.get('/health')
def health_check():
    return {'status': 'healthy', 'workflow': 'langgraph_enabled'}


@app.post('/start')
def start_refund_case(
    category: str = Form(...),
    domestic_status: str = Form('unknown'),
    customer_fault: str = Form('unknown'),
    file: UploadFile = File(...),
):
    if category not in ('upi_failed', 'ecommerce_return'):
        raise HTTPException(status_code=400, detail='Invalid transaction category.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail='Upload a JPG, PNG or WEBP screenshot. PDF is not supported yet.')
    content = file.file.read()
    max_bytes = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10')) * 1024 * 1024
    if not content or len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f'File is empty or exceeds {max_bytes // (1024 * 1024)} MB.')
    thread_id = str(uuid4())
    saved_path = UPLOAD_DIR / f'{thread_id}{suffix}'
    saved_path.write_bytes(content)
    initial_state = {
        'image_path': str(saved_path), 'category': category,
        'is_domestic': True if domestic_status == 'yes' else False if domestic_status == 'no' else None,
        'failure_attributable_to_customer': True if customer_fault == 'yes' else False if customer_fault == 'no' else None,
    }
    try:
        create_case({'thread_id': thread_id, 'image_path': str(saved_path), 'category': category, 'status': 'pending', 'state': {}})
        result = run_refund_case(initial_state, thread_id)
        status = result.get('status', 'workflow_error')
        update_case(thread_id, {'status': status, 'approval_status': result.get('approval_status', 'not_requested'), 'state': result})
        return {'message': 'Refund case processed by LangGraph.', 'thread_id': thread_id,
                'status': status, 'workflow_mode': 'langgraph', 'result': _public_state(result)}
    except Exception as exc:
        update_case(thread_id, {'status': 'workflow_error', 'state': {'status': 'workflow_error', 'dispatch_error': str(exc)}})
        raise HTTPException(status_code=500, detail=f'Workflow execution failed: {exc}')


@app.get('/case/{thread_id}')
def read_case(thread_id: str):
    case = get_case(thread_id)
    if not case:
        raise HTTPException(status_code=404, detail='Refund case not found.')
    # Refresh from LangGraph checkpoint where available.
    state = get_workflow_state(thread_id) or case.get('state', {})
    return {'thread_id': thread_id, 'status': case['status'], 'approval_status': case['approval_status'], 'result': _public_state(state)}


@app.get('/cases')
def list_cases():
    cases = get_all_cases()
    return {'total': len(cases), 'cases': [
        {'thread_id': c['thread_id'], 'category': c['category'], 'status': c['status'],
         'approval_status': c['approval_status'], 'created_at': c['created_at']}
        for c in cases
    ]}


@app.post('/approve')
def review_case(thread_id: str = Form(...), approved: bool = Form(...)):
    case = get_case(thread_id)
    if not case:
        raise HTTPException(status_code=404, detail='Refund case not found.')
    if case['approval_status'] != 'not_requested':
        raise HTTPException(status_code=400, detail='This case has already been reviewed.')
    if case['status'] != 'awaiting_approval':
        raise HTTPException(status_code=400, detail='This case is not waiting for approval. Check the case assessment first.')
    try:
        if approved:
            result = approve_refund_case(thread_id)
            status = result.get('status', 'workflow_error')
            update_case(thread_id, {'approval_status': 'approved', 'status': status, 'state': result})
            return {'message': 'Human approval recorded. Claim dispatch simulation completed.', 'thread_id': thread_id,
                    'approval_status': 'approved', 'status': status, 'result': _public_state(result)}
        result = reject_refund_case(thread_id)
        update_case(thread_id, {'approval_status': 'rejected', 'status': 'rejected', 'state': result})
        return {'message': 'Claim draft rejected. No email was sent.', 'thread_id': thread_id,
                'approval_status': 'rejected', 'status': 'rejected'}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Human review failed: {exc}')


@app.post('/escalate')
def escalate_case(thread_id: str = Form(...), reason: str = Form(...)):
    case = get_case(thread_id)
    if not case:
        raise HTTPException(status_code=404, detail='Refund case not found.')
    if case['status'] in ('resolved', 'rejected', 'claim_dispatched', 'escalated'):
        raise HTTPException(status_code=400, detail='This case cannot be escalated in its current status.')
    if not reason.strip():
        raise HTTPException(status_code=400, detail='Escalation reason is required.')
    update_case(thread_id, {'status': 'escalated', 'escalation_tier': 2, 'escalation_reason': reason.strip()})
    return {'message': 'Case escalated to Level 2 support.', 'thread_id': thread_id, 'status': 'escalated'}


@app.get('/escalations')
def list_escalations():
    cases = get_escalated_cases()
    return {'total_escalations': len(cases), 'cases': cases}


@app.post('/resolve/{thread_id}')
def resolve_case(thread_id: str):
    case = get_case(thread_id)
    if not case:
        raise HTTPException(status_code=404, detail='Case not found.')
    if case['status'] != 'escalated':
        raise HTTPException(status_code=400, detail='Only escalated cases can be resolved.')
    update_case(thread_id, {'status': 'resolved'})
    return {'message': 'Case resolved successfully.', 'thread_id': thread_id, 'status': 'resolved'}


# E-commerce autonomous refund routes (shares the existing SQLite database)
from app.ecommerce.api import router as ecommerce_router
app.include_router(ecommerce_router)
