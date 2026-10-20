"""Distributed Log & Audit Analytics Pipeline - Modern Observability Console."""

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
    render_sidebar_system_status,
    render_kpi_cards,
    create_severity_bar_chart,
    create_error_timeline_chart,
    create_severity_donut_chart,
    generate_demo_timeline_data,
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

st.set_page_config(
    page_title="LogPulse - Distributed Log & Audit Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session defaults (theme must exist before CSS is injected)
st.session_state.setdefault("ingestions", [])
st.session_state.setdefault("demo_created", {})
st.session_state.setdefault("ui_theme", "Light")
st.session_state.setdefault("upload_feedback", None)

# Global theme CSS: owns background, text, inputs, tabs and charts so nothing
# depends on the OS dark/light preference.
inject_custom_css()

if is_demo_mode():
    init_demo_state(st.session_state)

connection_status = check_api_connection()
render_header(connection_status, get_api_base_url())


def _num_col(df: pd.DataFrame, col: str) -> None:
    if col not in df:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)


# ==============================================================================
# Sidebar
# ==============================================================================
with st.sidebar:
    render_sidebar_system_status()

    st.markdown("### Appearance")
    st.radio("Theme", ["Light", "Dark"], horizontal=True, key="ui_theme", label_visibility="collapsed")

    st.markdown("### Controls & Sync")
    auto_refresh = st.toggle("Auto-refresh (5s)", value=True)
    if st.button("Sync Now", **get_stretch_kwarg(st.button)):
        st.rerun()

    st.divider()

    st.markdown("### Telemetry Scope")
    env_filter = st.selectbox("Environment", ["All environments", "prod", "staging", "dev"], index=0)

    available_services = ["All services"]
    try:
        for item in api_summary():
            svc_name = item.get("service_name")
            if svc_name and svc_name not in available_services:
                available_services.append(svc_name)
    except Exception:
        available_services = [
            "All services", "api-gateway", "audit-service",
            "auth-service", "course-service", "service-registry", "student-service",
        ]

    service_filter = st.selectbox("Service", available_services, index=0)

    st.divider()
    st.caption(f"**Endpoint:** `{get_api_base_url()}`")
    st.caption(f"**Execution Mode:** `{'Demo Mock' if is_demo_mode() else 'Production API'}`")
    st.caption(f"**Last refresh:** `{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC`")


# ==============================================================================
# Tab 1: Overview & Service Health Matrix
# ==============================================================================
def render_overview(selected_svc: str, selected_env: str) -> None:
    try:
        summary_data = api_summary()
    except Exception as exc:
        st.error(
            f"Unable to load metrics from {get_api_base_url()}/metrics/summary. "
            f"Ensure the ingestion API service is running. Details: {exc}"
        )
        return

    if not summary_data:
        render_empty_state(
            "No processed batches recorded yet. Telemetry appears once worker processes complete ingestion jobs.",
            action_label="Open the 'Ingestion & Pipeline' tab to submit a test log batch.",
            title="No Telemetry Stream Available",
        )
        return

    filtered = summary_data
    if selected_svc != "All services":
        filtered = [s for s in filtered if s.get("service_name") == selected_svc]
    # Environment filter applies whenever the API reports an environment per record
    if selected_env != "All environments" and any("environment" in s for s in filtered):
        filtered = [s for s in filtered if s.get("environment") == selected_env]

    if not filtered:
        render_empty_state(
            f"No telemetry records matched service '{selected_svc}' in '{selected_env}'.",
            action_label="Change the filters in the sidebar.",
            title="No Matching Records",
        )
        return

    df = pd.DataFrame(filtered)
    for col in ("error_count", "warning_count", "critical_count", "total_logs"):
        _num_col(df, col)

    total_logs = int(df["total_logs"].sum())
    total_errors = int(df["error_count"].sum())
    total_warnings = int(df["warning_count"].sum())
    total_critical = int(df["critical_count"].sum())
    df["info_count"] = (df["total_logs"] - df["error_count"] - df["warning_count"] - df["critical_count"]).clip(lower=0)
    total_info = int(df["info_count"].sum())

    render_kpi_cards(total_logs, total_errors, total_warnings, total_critical)

    col_bar, col_donut = st.columns([7, 5])
    with col_bar:
        st.markdown("#### Severity Distribution by Service")
        chart_df = df[["service_name", "info_count", "warning_count", "error_count", "critical_count"]]
        st.plotly_chart(create_severity_bar_chart(chart_df), theme=None, **get_stretch_kwarg(st.plotly_chart))

    with col_donut:
        st.markdown("#### Aggregate Severity & SLA")
        fig_donut = create_severity_donut_chart(total_logs, total_errors, total_warnings, total_critical, total_info)
        st.plotly_chart(fig_donut, theme=None, **get_stretch_kwarg(st.plotly_chart))

    st.markdown("#### Service Health Status")
    render_service_cards(filtered)

    st.markdown("#### Top Error Signatures per Service")
    render_top_errors_table(filtered)


# ==============================================================================
# Tab 2: Error & Time-Series Analytics
# ==============================================================================
def render_analytics(selected_svc: str) -> None:
    st.subheader("Error & Anomaly Time-Series Breakdown")
    st.write("Monitor log volume, error spikes, and critical anomalies across time buckets.")

    try:
        summary_data = api_summary()
    except Exception:
        summary_data = []

    if selected_svc != "All services":
        summary_data = [s for s in summary_data if s.get("service_name") == selected_svc]

    timeline_df = generate_demo_timeline_data(summary_data)

    st.plotly_chart(create_error_timeline_chart(timeline_df), theme=None, **get_stretch_kwarg(st.plotly_chart))
    st.caption("Hourly buckets are derived from the aggregate counters until a time-series endpoint is exposed by the API.")

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("#### Anomaly Thresholds & Trigger Rules")
        st.info("⚡ **Rule ERR-01:** Error rate > 5.0% triggers Degraded cluster state.")
        st.warning("⚠️ **Rule CRIT-01:** Any unhandled Critical failure flags immediate intervention.")
        st.success("✓ **SLA Target:** 99.9% fault-free ingestion throughput maintained.")

    with a2:
        st.markdown("#### Telemetry Volume Aggregation")
        tot_events = int(timeline_df[["info", "warn", "error", "critical"]].sum().sum())
        peak_row = timeline_df.assign(bad=timeline_df["error"] + timeline_df["critical"]).sort_values("bad").iloc[-1]
        m1, m2 = st.columns(2)
        m1.metric("Events Sampled (24h)", f"{tot_events:,}")
        m2.metric("Peak Error Hour (UTC)", peak_row["timestamp"].strftime("%H:00"))
        st.caption("Aggregated in 60-minute tumbling windows from worker telemetry collectors.")


# ==============================================================================
# Tab 3: Upload Logs
# ==============================================================================
def render_upload() -> None:
    st.subheader("Upload a log batch")
    st.write(
        "Accepts `.json`, `.jsonl`, or `.json.gz` archives up to 10 MB in JSON Lines format."
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
            st.session_state["upload_feedback"] = ("error", "Validation error: Service name is required.")
        elif uploaded_file is None:
            st.session_state["upload_feedback"] = ("error", "Validation error: Please select a log archive file.")
        else:
            is_valid, error_msg = validate_log_file(uploaded_file)
            if not is_valid:
                st.session_state["upload_feedback"] = ("error", f"Client validation failed: {error_msg}")
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
                    st.session_state["upload_feedback"] = (
                        "success",
                        f"Log batch accepted by pipeline. Batch ID: `{ingest_id}` (Initial: {status.capitalize()}).",
                    )
                except Exception as upload_err:
                    st.session_state["upload_feedback"] = (
                        "error",
                        f"Upload rejected: {upload_err}. Check that the ingestion API is operational at {get_api_base_url()}.",
                    )

    # Feedback message
    feedback = st.session_state.get("upload_feedback")
    if feedback:
        kind, text = feedback
        (st.success if kind == "success" else st.error)(text)

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


# ==============================================================================
# Tab 4: Ingestion Status & Diagnostics
# ==============================================================================
def render_status() -> None:
    st.subheader("Session ingestion batches")

    session_ingestions = st.session_state.get("ingestions", [])
    if not session_ingestions:
        render_empty_state(
            "No log batches have been uploaded in this session.",
            action_label="Submit a batch via the 'Upload logs' tab to track real-time pipeline status.",
            title="No Batches Submitted",
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
        selected_label = st.selectbox("Select batch to inspect lifecycle progression", options, key="status_stepper_select")
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


# ==============================================================================
# Tabs & auto-refresh fragments (prevents whole-page flicker)
# ==============================================================================
tab_overview, tab_analytics, tab_upload, tab_status = st.tabs([
    "📊 Telemetry Overview",
    "📈 Error & Timeline Analytics",
    "📤 Upload logs",
    "⚡ Ingestion status",
])

refresh_interval = 5 if auto_refresh else None


@st.fragment(run_every=refresh_interval)
def overview_fragment():
    render_overview(service_filter, env_filter)


@st.fragment(run_every=refresh_interval)
def analytics_fragment():
    render_analytics(service_filter)


@st.fragment(run_every=refresh_interval)
def upload_fragment():
    render_upload()


@st.fragment(run_every=refresh_interval)
def status_fragment():
    render_status()


with tab_overview:
    overview_fragment()

with tab_analytics:
    analytics_fragment()

with tab_upload:
    upload_fragment()

with tab_status:
    status_fragment()