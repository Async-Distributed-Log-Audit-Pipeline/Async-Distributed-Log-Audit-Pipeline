"""Distributed Log & Audit Analytics Pipeline - Observability Console.

Talks to the ingestion API:
  POST /logs/upload        -> {ingest_id, status}
  GET  /logs/status?id=    -> full record + metrics
  GET  /metrics/summary    -> [{service_name, total_logs, error_count, warning_count, critical_count, health, top_error?}]

Set DEMO_MODE=true to run with mock data when the API is unavailable.
"""
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from api import (
    api_upload,
    api_status,
    api_summary,
    check_api_connection,
    is_demo_mode,
    get_api_base_url,
)
from mock import init_demo_state, generate_sample_logs
from ui import (
    inject_custom_css,
    render_header,
    render_kpi_cards,
    create_severity_bar_chart,
    render_service_cards,
    render_pipeline_stepper,
    render_empty_state,
    render_ingestion_table,
    render_top_errors_table,
    render_batch_detail,
    render_architecture_diagram,
    render_architecture_stages,
    get_stretch_kwarg,
)
from validation import validate_log_file

# Configure Streamlit page without emojis
st.set_page_config(
    page_title="Log & Audit Analytics Pipeline",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global operations console styling and typography
inject_custom_css()

# Initialize session state tracking
st.session_state.setdefault("ingestions", [])
st.session_state.setdefault("demo_created", {})
if is_demo_mode():
    init_demo_state(st.session_state)

# Header with live connection indicator
connection_status = check_api_connection()
render_header(connection_status, get_api_base_url())

# Sidebar controls and filters
with st.sidebar:
    st.subheader("Console controls")
    auto_refresh = st.toggle("Auto-refresh data (5s)", value=True)
    if st.button("Refresh data", **get_stretch_kwarg(st.button)):
        st.rerun()

    st.divider()
    st.subheader("Overview filters")
    env_filter = st.selectbox(
        "Filter environment",
        ["All environments", "prod", "staging", "dev"],
        index=0,
    )

    # Dynamically extract available services from summary data if possible
    available_services = ["All services"]
    try:
        raw_summary = api_summary()
        for item in raw_summary:
            svc_name = item.get("service_name")
            if svc_name and svc_name not in available_services:
                available_services.append(svc_name)
    except Exception:
        available_services = ["All services", "api-gateway", "audit-service", "auth-service", "course-service", "service-registry", "student-service"]

    service_filter = st.selectbox(
        "Filter service",
        available_services,
        index=0,
    )

    st.divider()
    st.caption("Deployment details")
    st.caption(f"API endpoint: {get_api_base_url()}")
    st.caption(f"Operation mode: {'Demo Mode (Mock)' if is_demo_mode() else 'Live API'}")


# ---------------- Tab 1: Overview ----------------
def render_overview(selected_svc: str, selected_env: str) -> None:
    st.subheader("System telemetry overview")

    try:
        summary_data = api_summary()
    except Exception as exc:
        st.error(
            f"Unable to load metrics from {get_api_base_url()}/metrics/summary. "
            f"Ensure the ingestion API service is running and healthy. Details: {exc}"
        )
        return

    if not summary_data:
        render_empty_state(
            "No processed batches recorded yet. Telemetry appears once worker processes complete ingestion jobs.",
            action_label="Navigate to 'Upload logs' to submit a test log batch.",
        )
        return

    # Filter by service if specified
    filtered = summary_data
    if selected_svc != "All services":
        filtered = [s for s in summary_data if s.get("service_name") == selected_svc]

    if not filtered:
        render_empty_state(f"No telemetry records matched service filter '{selected_svc}'.")
        return

    df = pd.DataFrame(filtered)
    for col in ("error_count", "warning_count", "critical_count", "total_logs"):
        if col not in df:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    total_logs = int(df["total_logs"].sum())
    total_errors = int(df["error_count"].sum())
    total_warnings = int(df["warning_count"].sum())
    total_critical = int(df["critical_count"].sum())

    # 4 KPI cards
    render_kpi_cards(total_logs, total_errors, total_warnings, total_critical)

    # Plotly stacked bar chart
    st.markdown("#### Severity distribution by service")
    df["info_count"] = (df["total_logs"] - df["error_count"] - df["warning_count"] - df["critical_count"]).clip(lower=0)
    chart_df = df[["service_name", "info_count", "warning_count", "error_count", "critical_count"]]
    fig = create_severity_bar_chart(chart_df)
    st.plotly_chart(fig, **get_stretch_kwarg(st.plotly_chart))

    # Service Health cards
    st.markdown("#### Service health indicators")
    render_service_cards(filtered)

    # Top error per service plain table
    st.markdown("#### Top error per service")
    render_top_errors_table(filtered)


# ---------------- Tab 2: Upload Logs ----------------
def render_upload() -> None:
    st.subheader("Upload a log batch")
    st.write(
        "Accepts `.json`, `.jsonl`, or `.json.gz` archives up to 10 MB in JSON Lines format. "
        "Each line must be a JSON object containing `timestamp`, `level`, `service`, and `message`."
    )

    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "Select log archive",
            type=["json", "gz", "jsonl"],
            help="Files supported: .json, .jsonl, .json.gz (max 10 MB)",
        )
        col1, col2 = st.columns(2)
        service_input = col1.text_input("Service name", placeholder="coupon-service")
        env_input = col2.selectbox("Target environment", ["prod", "staging", "dev"])
        submit_button = st.form_submit_button("Upload logs", type="primary")

    if submit_button:
        if not service_input or not service_input.strip():
            st.error("Validation error: Service name is required.")
        elif uploaded_file is None:
            st.error("Validation error: Please select a log archive file.")
        else:
            # Client-side validation: size, compression, required fields
            is_valid, error_msg = validate_log_file(uploaded_file)
            if not is_valid:
                st.error(f"Client validation failed: {error_msg}")
            else:
                try:
                    res = api_upload(uploaded_file, service_input.strip(), env_input)
                    ingest_id = res.get("ingest_id")
                    status = res.get("status", "pending")

                    # Register in session state
                    st.session_state["last_uploaded_id"] = ingest_id
                    st.session_state["ingestions"].insert(
                        0,
                        {
                            "ingest_id": ingest_id,
                            "service_name": service_input.strip(),
                            "environment": env_input,
                            "submitted_at": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                        },
                    )
                    st.success(f"Log batch accepted by pipeline. Initial status: {status.capitalize()}.")
                except Exception as upload_err:
                    st.error(
                        f"Upload rejected: {upload_err}. "
                        f"Check that the ingestion API is operational at {get_api_base_url()}."
                    )

    # Monospace copyable box for the latest upload ID
    latest_id = st.session_state.get("last_uploaded_id")
    if latest_id:
        st.markdown("#### Ingestion identifier")
        st.caption("Copy this unique batch identifier to inspect status or track via external APIs:")
        st.code(latest_id, language="text")

    st.divider()
    st.subheader("Sample log generator")
    st.write("Generate a pre-validated JSON Lines log archive with realistic distributed system entries for demo purposes.")
    sample_content = generate_sample_logs()
    st.download_button(
        label="Download sample log file",
        data=sample_content,
        file_name="sample_pipeline_logs.jsonl",
        mime="application/x-ndjson",
    )


# ---------------- Tab 3: Ingestion Status ----------------
def render_status() -> None:
    st.subheader("Session ingestion batches")

    session_ingestions = st.session_state.get("ingestions", [])
    if not session_ingestions:
        render_empty_state(
            "No log batches have been uploaded in this session.",
            action_label="Submit a batch via the 'Upload logs' tab to track real-time pipeline status.",
        )
    else:
        # Fetch current record for each ingestion
        table_rows = []
        for item in session_ingestions:
            iid = item.get("ingest_id")
            try:
                rec = api_status(iid)
            except Exception:
                rec = {"status": "unknown"}

            metrics = rec.get("metrics") or {}
            table_rows.append({
                "ingest_id": iid,
                "service_name": item.get("service_name"),
                "environment": item.get("environment", "prod"),
                "submitted_at": item.get("submitted_at"),
                "status": rec.get("status", "unknown"),
                "total_logs": metrics.get("total_logs"),
                "error_count": metrics.get("error_count"),
                "warning_count": metrics.get("warning_count"),
                "critical_count": metrics.get("critical_count"),
                "error_reason": rec.get("error_reason"),
            })

        render_ingestion_table(table_rows)

        # Horizontal Pipeline Stepper for selected ingestion
        st.markdown("#### Ingestion pipeline inspector")
        options = [f"{r['ingest_id'][:8]}... ({r['service_name']})" for r in table_rows]
        selected_label = st.selectbox("Select batch to inspect lifecycle progression", options)
        selected_idx = options.index(selected_label) if selected_label in options else 0
        selected_record = table_rows[selected_idx]
        render_pipeline_stepper(selected_record["status"])
        try:
            full_record = api_status(selected_record["ingest_id"])
            render_batch_detail(full_record)
        except Exception:
            render_batch_detail(selected_record)

    st.divider()
    st.subheader("Query ingestion by ID")
    st.caption("Inspect metadata and computed metrics for any batch in the distributed store.")
    lookup_col1, lookup_col2 = st.columns([3, 1])
    lookup_input = lookup_col1.text_input("Ingestion UUID", placeholder="Enter batch UUID", label_visibility="collapsed")
    lookup_btn = lookup_col2.button("Query status", **get_stretch_kwarg(st.button))

    if lookup_btn or (lookup_input and lookup_input.strip()):
        cleaned_id = lookup_input.strip()
        if not cleaned_id:
            st.warning("Please enter an ingestion batch UUID.")
        else:
            try:
                result = api_status(cleaned_id)
                render_batch_detail(result)
            except Exception as e:
                st.error(f"Failed to query batch status: {e}")


# ---------------- Tab 4: Architecture ----------------
def render_architecture() -> None:
    st.subheader("System architecture & pipeline design")
    st.write(
        "An asynchronous, decoupled distributed architecture designed to absorb high-throughput "
        "microservice log streams without blocking calling clients."
    )

    render_architecture_diagram()

    st.markdown("#### Stage breakdown & distributed responsibilities")
    render_architecture_stages()

    st.markdown("#### Viva evaluation highlights")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            **1. Non-blocking Ingestion**
            * The API gateway validates format and saves raw files immediately.
            * Returns `HTTP 201 Created` with a unique `ingest_id` without waiting for parsing.
            * Isolates client latency from batch processing times.
            """
        )
        st.markdown(
            """
            **2. Worker Scalability & Backpressure**
            * Message queues buffer incoming batches during sudden traffic spikes.
            * Worker pool scales out horizontally based on queue depth metrics.
            * At-least-once delivery with worker acknowledgments guarantees reliable processing.
            """
        )
    with c2:
        st.markdown(
            """
            **3. Fault Isolation & Dead Letter Queues (DLQ)**
            * Poison-pill batches or malformed records do not halt the entire queue.
            * Unrecoverable tasks automatically transition to DLQ after 3 retries.
            * Batch marked as `failed` with descriptive `error_reason` in Metadata DB.
            """
        )
        st.markdown(
            """
            **4. Eventual Consistency & Query Efficiency**
            * Aggregated telemetry stored separately from raw line-level audit logs.
            * Fast indexing by `service_name` enables real-time sub-second dashboard rendering.
            """
        )


# Setup Tabs
tab_overview, tab_upload, tab_status, tab_arch = st.tabs([
    "Overview",
    "Upload logs",
    "Ingestion status",
    "Architecture",
])

# Create non-annoying auto-refresh fragments for data views
@st.fragment(run_every=5 if auto_refresh else None)
def overview_fragment():
    render_overview(service_filter, env_filter)


@st.fragment(run_every=5 if auto_refresh else None)
def status_fragment():
    render_status()


with tab_overview:
    overview_fragment()

with tab_upload:
    render_upload()

with tab_status:
    status_fragment()

with tab_arch:
    render_architecture()
