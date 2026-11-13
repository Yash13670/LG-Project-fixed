import streamlit as st
import requests
import os

API_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000"
).rstrip("/")
st.set_page_config(page_title='Refund Recovery Agent', page_icon='💳', layout='wide')
st.title('💳 Autonomous Refund & Chargeback Recovery Agent')
st.caption('Evidence extraction • Deterministic TAT assessment • Human approval • Escalation')

try:
    health = requests.get(f'{API_URL}/health', timeout=4)
    if health.ok:
        st.success('Backend connected • LangGraph enabled')
    else:
        st.error('Backend health check failed.')
except requests.RequestException:
    st.error('Backend offline. Start FastAPI in the first terminal.')
    st.stop()

menu = st.sidebar.radio('Navigation', ['New Claim', 'Case Review', 'All Cases', 'Escalate Case', 'Level 2 Support'])


def show_result(result: dict):
    if not result:
        return
    st.subheader('Workflow assessment')
    a, b, c = st.columns(3)
    a.metric('Status', result.get('status', 'N/A'))
    b.metric('Eligible for compensation', 'Yes' if result.get('eligible_for_compensation') else 'No / unconfirmed')
    b.metric('Calculated compensation', f"₹{result.get('penalty_owed', 0) or 0}")
    c.metric('Delay days', result.get('delay_days', 0) or 0)
    st.write('**Extracted transaction details**')
    st.json({k: result.get(k) for k in ['category', 'transaction_id', 'merchant_name', 'amount', 'transaction_date', 'upi_transaction_type', 'is_domestic']})
    if result.get('missing_info_prompt'):
        st.warning(result['missing_info_prompt'])
    if result.get('rule_reason'):
        st.info(result['rule_reason'])
    if result.get('dispatch_error'):
        st.warning(result['dispatch_error'])
    if result.get('drafted_email'):
        st.markdown('**Generated claim draft (not sent):**')
        st.text_area('Draft email', result['drafted_email'], height=260)


if menu == 'New Claim':
    st.header('Submit transaction evidence')
    category = st.selectbox('Claim category', ['upi_failed', 'ecommerce_return'], format_func=lambda x: 'Failed UPI transaction' if x == 'upi_failed' else 'E-commerce return')
    file = st.file_uploader('Upload payment/order screenshot', type=['png', 'jpg', 'jpeg', 'webp'])
    st.caption('Upload a clear screenshot. PDF files are not supported in this version.')
    domestic = st.selectbox('Is this a domestic transaction?', ['unknown', 'yes', 'no'], format_func=lambda x: {'unknown': 'Not sure', 'yes': 'Yes', 'no': 'No'}[x])
    customer_fault = st.selectbox('Was the failure caused by the customer?', ['unknown', 'no', 'yes'], format_func=lambda x: {'unknown': 'Not sure', 'no': 'No', 'yes': 'Yes'}[x])
    st.caption('If either answer is unknown, the system will avoid asserting compensation eligibility and may require manual review.')
    if st.button('Analyze claim', type='primary', disabled=file is None):
        try:
            with st.spinner('Running evidence extraction and LangGraph assessment...'):
                response = requests.post(f'{API_URL}/start', data={'category': category, 'domestic_status': domestic, 'customer_fault': customer_fault}, files={'file': (file.name, file.getvalue(), file.type)}, timeout=180)
            if response.ok:
                data = response.json()
                st.success('Case processed.')
                st.write('**Thread ID**')
                st.code(data['thread_id'])
                show_result(data.get('result', {}))
            else:
                st.error(response.text)
        except requests.RequestException as exc:
            st.error(f'API error: {exc}')

elif menu == 'Case Review':
    st.header('Human approval / rejection')
    thread_id = st.text_input('Refund Thread ID')
    if st.button('Load case'):
        try:
            response = requests.get(f'{API_URL}/case/{thread_id.strip()}', timeout=15)
            if response.ok:
                data = response.json()
                st.write('**Current status:**', data['status'])
                st.write('**Approval:**', data['approval_status'])
                show_result(data.get('result', {}))
                st.session_state['review_case_id'] = thread_id.strip()
                st.session_state['review_case_status'] = data['status']
            else:
                st.error(response.text)
        except requests.RequestException as exc:
            st.error(str(exc))
    if st.session_state.get('review_case_id') == thread_id.strip() and st.session_state.get('review_case_status') == 'awaiting_approval':
        st.warning('Approval will only run a local dispatch simulation. No real email is sent.')
        left, right = st.columns(2)
        with left:
            if st.button('Approve and simulate dispatch', type='primary'):
                response = requests.post(f'{API_URL}/approve', data={'thread_id': thread_id.strip(), 'approved': 'true'}, timeout=45)
                if response.ok:
                    st.success(response.json()['message'])
                    show_result(response.json().get('result', {}))
                else:
                    st.error(response.text)
        with right:
            if st.button('Reject draft'):
                response = requests.post(f'{API_URL}/approve', data={'thread_id': thread_id.strip(), 'approved': 'false'}, timeout=20)
                if response.ok:
                    st.info(response.json()['message'])
                else:
                    st.error(response.text)

elif menu == 'All Cases':
    st.header('Case history')
    if st.button('Refresh cases'):
        response = requests.get(f'{API_URL}/cases', timeout=15)
        if response.ok:
            data = response.json()
            st.metric('Total cases', data['total'])
            if data['cases']:
                st.dataframe(data['cases'], use_container_width=True, hide_index=True)
            else:
                st.info('No cases yet.')
        else:
            st.error(response.text)

elif menu == 'Escalate Case':
    st.header('Escalate to Level 2 support')
    thread_id = st.text_input('Refund Thread ID')
    reason = st.text_area('Escalation reason')
    if st.button('Escalate', type='primary'):
        response = requests.post(f'{API_URL}/escalate', data={'thread_id': thread_id.strip(), 'reason': reason.strip()}, timeout=15)
        if response.ok:
            st.success(response.json()['message'])
        else:
            st.error(response.text)

elif menu == 'Level 2 Support':
    st.header('Level 2 support dashboard')
    if st.button('Refresh escalated cases'):
        response = requests.get(f'{API_URL}/escalations', timeout=15)
        if response.ok:
            data = response.json()
            st.metric('Total escalated cases', data['total_escalations'])
            for case in data['cases']:
                with st.expander(f"{case['thread_id']} • {case['category']}"):
                    st.write('**Reason:**', case.get('escalation_reason'))
                    st.write('**Status:**', case.get('status'))
                    if st.button('Mark resolved', key=f"resolve_{case['thread_id']}"):
                        result = requests.post(f"{API_URL}/resolve/{case['thread_id']}", timeout=15)
                        if result.ok:
                            st.success('Case resolved.')
                            st.rerun()
                        else:
                            st.error(result.text)
        else:
            st.error(response.text)
