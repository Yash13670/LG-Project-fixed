import os
import streamlit as st
import requests

st.set_page_config(
    page_title="Autonomous Refund Agent",
    page_icon="💳",
    layout="wide"
)

try:
    API_URL = st.secrets["BACKEND_URL"]
except Exception:
    API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

API_URL = API_URL.rstrip("/")

st.title("💳 Intelligent Refund & Escalation Agent")
st.caption(
    "UPI claim recovery • E-commerce refunds • Risk assessment "
    "• Human review"
)

# --------------------------------------------------
# BACKEND HEALTH
# --------------------------------------------------
try:
    health = requests.get(f"{API_URL}/health", timeout=5)
    if health.status_code == 200:
        st.success("Backend connected")
    else:
        st.error("Backend is not responding correctly")
except requests.RequestException:
    st.error("Backend is offline. Start FastAPI first.")

st.divider()

menu = st.sidebar.radio(
    "Navigation",
    [
        "UPI Refund Claim",
        "E-commerce Refund",
        "Approve / Reject",
        "E-commerce Refund History",
        "Escalate Case",
        "Level 2 Support"
    ]
)

# --------------------------------------------------
# 1. EXISTING UPI WORKFLOW
# --------------------------------------------------
if menu == "UPI Refund Claim":

    st.header("Submit UPI Refund Claim")
    st.caption("Existing UPI evidence and claim workflow")

    uploaded_file = st.file_uploader(
        "Upload transaction screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        key="upi_upload"
    )

    domestic = st.selectbox(
        "Was this a domestic transaction?",
        ["Unknown", "Yes", "No"]
    )

    customer_fault = st.selectbox(
        "Was the failure caused by customer error?",
        ["Unknown", "Yes", "No"]
    )

    if st.button("Submit UPI Claim", type="primary"):

        if uploaded_file is None:
            st.warning("Please upload transaction evidence.")
        else:
            try:
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                    )
                }

                data = {
                    "category": "upi_failed",
                    "domestic_status": domestic.lower(),
                    "customer_fault": customer_fault.lower()
                }

                response = requests.post(
                    f"{API_URL}/start",
                    data=data,
                    files=files,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success("UPI claim submitted successfully")
                    st.code(result.get("thread_id", ""))
                    st.write("Status:", result.get("status"))
                    st.json(result.get("result", result))
                else:
                    st.error(response.text)

            except requests.RequestException as error:
                st.error(f"API error: {error}")


# --------------------------------------------------
# 2. E-COMMERCE REFUND WORKFLOW
# --------------------------------------------------
elif menu == "E-commerce Refund":

    st.header("🛒 E-commerce Refund Request")
    st.caption(
        "The agent verifies the order, checks return policy "
        "and evaluates refund risk."
    )

    with st.form("ecommerce_refund_form"):

        col1, col2 = st.columns(2)

        with col1:
            customer_id = st.text_input(
                "Customer ID",
                placeholder="Example: CUST-001"
            )
            order_id = st.text_input(
                "Order ID",
                placeholder="Example: ORD-1001"
            )

        with col2:
            product_id = st.text_input(
                "Product ID",
                placeholder="Example: P200"
            )
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=100,
                value=1
            )

        reason = st.selectbox(
            "Refund Reason",
            [
                "damaged",
                "missing_item",
                "wrong_item",
                "not_as_described",
                "other"
            ]
        )

        description = st.text_area(
            "Describe the issue",
            placeholder="Explain why you are requesting a refund..."
        )

        submitted = st.form_submit_button(
            "Evaluate Refund Request",
            type="primary"
        )

    if submitted:

        if not all([
            customer_id.strip(),
            order_id.strip(),
            product_id.strip()
        ]):
            st.warning("Please fill in Customer ID, Order ID and Product ID.")

        else:
            payload = {
                "customer_id": customer_id.strip(),
                "order_id": order_id.strip(),
                "product_id": product_id.strip(),
                "quantity": int(quantity),
                "reason": reason,
                "description": description.strip()
            }

            try:
                response = requests.post(
                    f"{API_URL}/ecommerce/start",
                    json=payload,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()

                    st.success("Refund request evaluated!")

                    st.write("**Request ID:**")
                    st.code(result.get("thread_id", ""))

                    st.write(
                        "**Status:**",
                        result.get("status", "unknown")
                    )

                    st.json(result.get("result", result))

                    if result.get("status") == "refunded":
                        st.success("Mock refund executed successfully.")
                    elif result.get("status") == "awaiting_approval":
                        st.warning("This request requires human review.")
                    elif result.get("status") == "rejected":
                        st.error("This request was rejected by the policy checks.")

                else:
                    st.error(response.text)

            except requests.RequestException as error:
                st.error(f"API error: {error}")


# --------------------------------------------------
# 3. HUMAN APPROVAL / REJECTION
# --------------------------------------------------
elif menu == "Approve / Reject":

    st.header("Human Review")

    case_type = st.radio(
        "Select case type",
        ["E-commerce", "UPI"],
        horizontal=True
    )

    thread_id = st.text_input("Enter Case / Thread ID")

    if st.button("Fetch Case Details"):

        if not thread_id.strip():
            st.warning("Enter a valid case ID.")
        else:
            endpoint = (
                f"/ecommerce/case/{thread_id.strip()}"
                if case_type == "E-commerce"
                else f"/case/{thread_id.strip()}"
            )

            try:
                response = requests.get(
                    f"{API_URL}{endpoint}",
                    timeout=15
                )

                if response.status_code == 200:
                    st.session_state["review_case"] = response.json()
                    st.session_state["review_case_type"] = case_type
                    st.session_state["review_thread_id"] = thread_id.strip()
                else:
                    st.error(response.text)

            except requests.RequestException as error:
                st.error(f"API error: {error}")

    if "review_case" in st.session_state:
        if (
            st.session_state.get("review_case_type") == case_type
            and st.session_state.get("review_thread_id") == thread_id.strip()
        ):
            st.subheader("Case Details")
            st.json(st.session_state["review_case"])

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Approve", type="primary"):
                    try:
                        if case_type == "E-commerce":
                            response = requests.post(
                                f"{API_URL}/ecommerce/approve",
                                json={
                                    "thread_id": thread_id.strip(),
                                    "approved": True
                                },
                                timeout=60
                            )
                        else:
                            response = requests.post(
                                f"{API_URL}/approve",
                                data={
                                    "thread_id": thread_id.strip(),
                                    "approved": "true"
                                },
                                timeout=60
                            )

                        if response.status_code == 200:
                            st.success("Approval processed.")
                            st.json(response.json())
                            st.session_state.pop("review_case", None)
                        else:
                            st.error(response.text)

                    except requests.RequestException as error:
                        st.error(f"API error: {error}")

            with col2:
                if st.button("Reject"):
                    try:
                        if case_type == "E-commerce":
                            response = requests.post(
                                f"{API_URL}/ecommerce/approve",
                                json={
                                    "thread_id": thread_id.strip(),
                                    "approved": False
                                },
                                timeout=30
                            )
                        else:
                            response = requests.post(
                                f"{API_URL}/approve",
                                data={
                                    "thread_id": thread_id.strip(),
                                    "approved": "false"
                                },
                                timeout=30
                            )

                        if response.status_code == 200:
                            st.info("Case rejected.")
                            st.json(response.json())
                            st.session_state.pop("review_case", None)
                        else:
                            st.error(response.text)

                    except requests.RequestException as error:
                        st.error(f"API error: {error}")


# --------------------------------------------------
# 4. E-COMMERCE REFUND HISTORY
# --------------------------------------------------
elif menu == "E-commerce Refund History":

    st.header("📜 E-commerce Refund History")

    if st.button("Refresh Refund History", type="primary"):

        try:
            response = requests.get(
                f"{API_URL}/ecommerce/refund-history",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                st.json(data)
            else:
                st.error(response.text)

        except requests.RequestException as error:
            st.error(f"API error: {error}")


# --------------------------------------------------
# 5. EXISTING ESCALATION WORKFLOW
# --------------------------------------------------
elif menu == "Escalate Case":

    st.header("Escalate Case to Level 2")

    thread_id = st.text_input("Enter Case / Thread ID")

    reason = st.text_area(
        "Escalation Reason",
        placeholder="Explain why this case needs Level 2 support..."
    )

    if st.button("Escalate Case", type="primary"):

        if not thread_id.strip() or not reason.strip():
            st.warning("Both fields are required.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/escalate",
                    json={
                        "thread_id": thread_id.strip(),
                        "reason": reason.strip()
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    st.success("Case escalated successfully.")
                    st.json(response.json())
                else:
                    st.error(response.text)

            except requests.RequestException as error:
                st.error(f"API error: {error}")


# --------------------------------------------------
# 6. EXISTING LEVEL 2 SUPPORT
# --------------------------------------------------
elif menu == "Level 2 Support":

    st.header("🎧 Level 2 Support Dashboard")
    st.caption("Review and resolve escalated cases")

    if st.button("Refresh Escalated Cases", type="primary"):

        try:
            response = requests.get(
                f"{API_URL}/escalations",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()

                st.metric(
                    "Total Escalated Cases",
                    data.get("total_escalations", 0)
                )

                for case in data.get("cases", []):

                    with st.expander(
                        f"Case: {case.get('thread_id', 'Unknown')}"
                    ):
                        st.write("Category:", case.get("category", "N/A"))
                        st.write(
                            "Reason:",
                            case.get("escalation_reason", "N/A")
                        )
                        st.write("Status:", case.get("status", "N/A"))

                        case_id = case.get("thread_id")

                        if st.button(
                            "Mark as Resolved",
                            key=f"resolve_{case_id}"
                        ):
                            result = requests.post(
                                f"{API_URL}/resolve/{case_id}",
                                timeout=15
                            )

                            if result.status_code == 200:
                                st.success("Case resolved.")
                                st.rerun()
                            else:
                                st.error(result.text)

                if not data.get("cases"):
                    st.info("No escalated cases found.")

            else:
                st.error(response.text)

        except requests.RequestException as error:
            st.error(f"API error: {error}")
