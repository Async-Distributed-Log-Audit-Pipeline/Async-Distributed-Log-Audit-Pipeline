"""UI components, design system, custom styling, and layout helpers."""
import html
import plotly.graph_objects as go
import streamlit as st

# Color Palette Constants
COLOR_INK = "#1B2430"
COLOR_PRIMARY = "#1F4E79"
COLOR_PAGE_BG = "#F6F7F9"
COLOR_SURFACE = "#FFFFFF"
COLOR_BORDER = "#D9DEE5"
COLOR_SUCCESS = "#2E7D5B"

SEVERITY_COLORS = {
    "INFO": "#4A7C9B",
    "WARN": "#D9A441",
    "ERROR": "#C8553D",
    "CRITICAL": "#7A1F3D",
}

STATUS_CONFIG = {
    "pending": {"label": "Queued", "class": "badge-queued"},
    "processing": {"label": "Processing", "class": "badge-processing"},
    "completed": {"label": "Completed", "class": "badge-completed"},
    "failed": {"label": "Failed", "class": "badge-failed"},
}


def inject_custom_css() -> None:
    """Inject typography, theme variables, and custom styling into Streamlit app."""
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], [class*="st-"] {{
        font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: {COLOR_INK};
    }}

    code, pre, .mono, [data-testid="stDataFrame"] td {{
        font-family: 'IBM Plex Mono', monospace !important;
    }}

    /* Global page layout adjustments */
    .block-container {{
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }}

    /* Top bar container */
    .topbar-container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    .topbar-title {{
        font-size: 1.6rem;
        font-weight: 700;
        color: {COLOR_INK};
        margin: 0;
        line-height: 1.2;
    }}
    .topbar-subtitle {{
        font-size: 0.88rem;
        color: #5A6A80;
        margin-top: 0.25rem;
    }}
    .topbar-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.75rem;
        border-radius: 4px;
        font-size: 0.84rem;
        font-weight: 500;
        border: 1px solid {COLOR_BORDER};
        background-color: {COLOR_SURFACE};
    }}
    .indicator-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }}
    .dot-connected {{
        background-color: {COLOR_SUCCESS};
        box-shadow: 0 0 0 2px rgba(46, 125, 91, 0.2);
    }}
    .dot-demo {{
        background-color: {SEVERITY_COLORS["WARN"]};
        box-shadow: 0 0 0 2px rgba(217, 164, 65, 0.2);
    }}
    .dot-unreachable {{
        background-color: {SEVERITY_COLORS["ERROR"]};
        box-shadow: 0 0 0 2px rgba(200, 85, 61, 0.2);
    }}

    /* KPI Cards */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    @media (max-width: 900px) {{
        .kpi-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}
    }}
    .kpi-card {{
        background: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 1.1rem 1.25rem;
        position: relative;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }}
    .kpi-card::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        border-radius: 6px 6px 0 0;
    }}
    .kpi-total::before {{ background: {COLOR_PRIMARY}; }}
    .kpi-warn::before {{ background: {SEVERITY_COLORS["WARN"]}; }}
    .kpi-error::before {{ background: {SEVERITY_COLORS["ERROR"]}; }}
    .kpi-critical::before {{ background: {SEVERITY_COLORS["CRITICAL"]}; }}

    .kpi-label {{
        font-size: 0.85rem;
        font-weight: 500;
        color: #5A6A80;
        margin-bottom: 0.4rem;
        text-transform: none;
    }}
    .kpi-value {{
        font-size: 1.9rem;
        font-weight: 700;
        font-family: 'IBM Plex Mono', monospace !important;
        color: {COLOR_INK};
        line-height: 1.1;
    }}
    .kpi-subtext {{
        font-size: 0.78rem;
        color: #718299;
        margin-top: 0.4rem;
    }}

    /* Service Health Cards */
    .service-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .service-card {{
        background: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }}
    .service-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
    }}
    .service-name {{
        font-size: 1rem;
        font-weight: 600;
        color: {COLOR_PRIMARY};
    }}
    .service-metric-row {{
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        padding: 0.25rem 0;
        border-bottom: 1px solid #EEF1F4;
    }}
    .service-metric-label {{
        color: #5A6A80;
    }}
    .service-metric-val {{
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
    }}
    .service-top-error {{
        margin-top: 0.75rem;
        font-size: 0.78rem;
        background: #F8FAFC;
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 0.45rem 0.6rem;
        color: #475569;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}

    /* Badges */
    .badge {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0.02em;
    }}
    .badge-queued {{
        background-color: #EBF2F7;
        color: {COLOR_PRIMARY};
        border: 1px solid #BDD4E7;
    }}
    @keyframes pulse-subtle {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.45; }}
        100% {{ opacity: 1; }}
    }}
    .badge-processing {{
        background-color: #FEF7EA;
        color: #8C5A00;
        border: 1px solid #F0C475;
        animation: pulse-subtle 2s infinite ease-in-out;
    }}
    .badge-completed {{
        background-color: #EAF5EE;
        color: #175C3B;
        border: 1px solid #9FD4B8;
    }}
    .badge-failed {{
        background-color: #FDF2F0;
        color: #932312;
        border: 1px solid #F1ADA2;
    }}
    .badge-healthy {{
        background-color: #EAF5EE;
        color: #175C3B;
        border: 1px solid #9FD4B8;
    }}
    .badge-degraded {{
        background-color: #FEF7EA;
        color: #8C5A00;
        border: 1px solid #F0C475;
    }}
    .badge-critical {{
        background-color: #FDF2F0;
        color: #932312;
        border: 1px solid #F1ADA2;
    }}

    /* Horizontal Pipeline Stepper */
    .stepper-container {{
        background: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 1.25rem 1.5rem;
        margin: 1.25rem 0;
    }}
    .stepper-title {{
        font-size: 0.84rem;
        font-weight: 600;
        color: #5A6A80;
        margin-bottom: 1rem;
    }}
    .stepper-track {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: relative;
    }}
    .stepper-step {{
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 2;
        width: 120px;
        text-align: center;
    }}
    .step-circle {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.82rem;
        font-weight: 600;
        background: #FFFFFF;
        border: 2px solid {COLOR_BORDER};
        color: #718299;
        margin-bottom: 0.4rem;
    }}
    .step-done .step-circle {{
        background: {COLOR_SUCCESS};
        border-color: {COLOR_SUCCESS};
        color: #FFFFFF;
    }}
    .step-active .step-circle {{
        background: {COLOR_PRIMARY};
        border-color: {COLOR_PRIMARY};
        color: #FFFFFF;
    }}
    .step-pulsing .step-circle {{
        background: {SEVERITY_COLORS["WARN"]};
        border-color: {SEVERITY_COLORS["WARN"]};
        color: #FFFFFF;
        animation: pulse-subtle 2s infinite ease-in-out;
    }}
    .step-failed .step-circle {{
        background: {SEVERITY_COLORS["ERROR"]};
        border-color: {SEVERITY_COLORS["ERROR"]};
        color: #FFFFFF;
    }}
    .step-label {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {COLOR_INK};
    }}
    .step-caption {{
        font-size: 0.72rem;
        color: #718299;
        margin-top: 0.15rem;
    }}
    .stepper-line {{
        position: absolute;
        top: 16px;
        left: 60px;
        right: 60px;
        height: 2px;
        background: {COLOR_BORDER};
        z-index: 1;
    }}
    .stepper-line-fill {{
        height: 100%;
        background: {COLOR_SUCCESS};
        transition: width 0.3s ease;
    }}

    /* Architecture Stage Cards */
    .arch-card {{
        background: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }}
    .arch-stage-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.3rem;
    }}
    .arch-stage-title {{
        font-size: 0.95rem;
        font-weight: 600;
        color: {COLOR_PRIMARY};
    }}
    .arch-stage-tech {{
        font-size: 0.78rem;
        font-family: 'IBM Plex Mono', monospace;
        color: #5A6A80;
    }}
    .arch-stage-desc {{
        font-size: 0.85rem;
        color: #334155;
        line-height: 1.4;
    }}

    /* Empty state box */
    .empty-state-box {{
        background: {COLOR_SURFACE};
        border: 1px dashed {COLOR_BORDER};
        border-radius: 6px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        margin: 1.5rem 0;
    }}
    .empty-state-title {{
        font-size: 1.05rem;
        font-weight: 600;
        color: {COLOR_INK};
        margin-bottom: 0.4rem;
    }}
    .empty-state-text {{
        font-size: 0.88rem;
        color: #5A6A80;
        max-width: 500px;
        margin: 0 auto;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_header(status: str, api_url: str) -> None:
    """Render top bar with project title and live connection indicator."""
    if status == "connected":
        indicator_html = """
        <div class="topbar-indicator">
            <span class="indicator-dot dot-connected"></span>
            <span>API connected</span>
        </div>
        """
    elif status == "demo":
        indicator_html = """
        <div class="topbar-indicator">
            <span class="indicator-dot dot-demo"></span>
            <span>Demo mode (mock data)</span>
        </div>
        """
    else:
        indicator_html = f"""
        <div class="topbar-indicator">
            <span class="indicator-dot dot-unreachable"></span>
            <span>API unreachable ({api_url})</span>
        </div>
        """

    html_code = f"""
    <div class="topbar-container">
        <div>
            <h1 class="topbar-title">Distributed Log & Audit Analytics Pipeline</h1>
            <div class="topbar-subtitle">Asynchronous telemetry ingest, worker parsing & distributed metrics console</div>
        </div>
        <div>
            {indicator_html}
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_kpi_cards(total_logs: int, errors: int, warnings: int, critical: int) -> None:
    """Render four prominent KPI cards with strict operational visual hierarchy."""
    kpi_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-total">
            <div class="kpi-label">Total processed logs</div>
            <div class="kpi-value">{total_logs:,}</div>
            <div class="kpi-subtext">Aggregated across services</div>
        </div>
        <div class="kpi-card kpi-warn">
            <div class="kpi-label">Warnings</div>
            <div class="kpi-value">{warnings:,}</div>
            <div class="kpi-subtext">Transient warnings reported</div>
        </div>
        <div class="kpi-card kpi-error">
            <div class="kpi-label">Errors</div>
            <div class="kpi-value">{errors:,}</div>
            <div class="kpi-subtext">Application-level exceptions</div>
        </div>
        <div class="kpi-card kpi-critical">
            <div class="kpi-label">Critical failures</div>
            <div class="kpi-value">{critical:,}</div>
            <div class="kpi-subtext">Requires immediate intervention</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)


def create_severity_bar_chart(df) -> go.Figure:
    """Create stacked bar chart of severity per service with designated palette."""
    fig = go.Figure()

    services = df["service_name"].tolist() if "service_name" in df else []

    # Map severity levels and colors
    categories = [
        ("INFO", "info_count", SEVERITY_COLORS["INFO"]),
        ("WARN", "warning_count", SEVERITY_COLORS["WARN"]),
        ("ERROR", "error_count", SEVERITY_COLORS["ERROR"]),
        ("CRITICAL", "critical_count", SEVERITY_COLORS["CRITICAL"]),
    ]

    for label, col, color in categories:
        values = df[col].tolist() if col in df else [0] * len(services)
        fig.add_trace(
            go.Bar(
                name=label,
                x=services,
                y=values,
                marker=dict(color=color, line=dict(color="#FFFFFF", width=0.5)),
                hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:,}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=320,
        margin=dict(l=20, r=20, t=25, b=30),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color=COLOR_INK),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text="",
        ),
        xaxis=dict(
            title="",
            tickfont=dict(size=12, color=COLOR_INK),
            showgrid=False,
            linecolor=COLOR_BORDER,
        ),
        yaxis=dict(
            title="Log count",
            tickfont=dict(family="IBM Plex Mono", size=11, color=COLOR_INK),
            showgrid=True,
            gridcolor="#EEF1F4",
            zeroline=False,
            linecolor=COLOR_BORDER,
        ),
    )
    return fig


def render_service_cards(services: list[dict]) -> None:
    """Render service health card for each microservice."""
    cards_html = ['<div class="service-grid">']
    for svc in services:
        name = svc.get("service_name", "unknown")
        total = int(svc.get("total_logs", 0))
        errors = int(svc.get("error_count", 0))
        critical = int(svc.get("critical_count", 0))

        # Derive health badge
        raw_health = str(svc.get("health", "")).lower()
        if raw_health in ("critical", "degraded", "healthy"):
            health = raw_health
        else:
            if critical > 0 or (total > 0 and (errors / total) > 0.05):
                health = "critical"
            elif errors > 0:
                health = "degraded"
            else:
                health = "healthy"

        health_badge_class = f"badge-{health}"
        health_label = health.capitalize()

        error_rate = (errors / total * 100) if total > 0 else 0.0
        top_err = svc.get("top_error") or "No errors recorded"

        card = f"""
        <div class="service-card">
            <div class="service-card-header">
                <span class="service-name">{html.escape(name)}</span>
                <span class="badge {health_badge_class}">{health_label}</span>
            </div>
            <div class="service-metric-row">
                <span class="service-metric-label">Total logs</span>
                <span class="service-metric-val">{total:,}</span>
            </div>
            <div class="service-metric-row">
                <span class="service-metric-label">Error rate</span>
                <span class="service-metric-val">{error_rate:.2f}%</span>
            </div>
            <div class="service-metric-row">
                <span class="service-metric-label">Critical issues</span>
                <span class="service-metric-val">{critical:,}</span>
            </div>
            <div class="service-top-error" title="{html.escape(top_err)}">
                {html.escape(top_err)}
            </div>
        </div>
        """
        cards_html.append(card)

    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """Return HTML markup for a colored status badge."""
    cfg = STATUS_CONFIG.get(status.lower(), {"label": status.capitalize(), "class": "badge-queued"})
    return f'<span class="badge {cfg["class"]}">{cfg["label"]}</span>'


def render_pipeline_stepper(status: str) -> None:
    """Render horizontal stepper showing pipeline lifecycle stages."""
    norm_status = status.lower()

    # Step states: 'done', 'active', 'pulsing', 'failed', 'upcoming'
    if norm_status == "pending":
        s1, s2, s3, s4 = "done", "active", "upcoming", "upcoming"
        fill_width = "33%"
        s4_label, s4_sub = "Completed", "Store metrics"
    elif norm_status == "processing":
        s1, s2, s3, s4 = "done", "done", "pulsing", "upcoming"
        fill_width = "66%"
        s4_label, s4_sub = "Completed", "Store metrics"
    elif norm_status == "completed":
        s1, s2, s3, s4 = "done", "done", "done", "done"
        fill_width = "100%"
        s4_label, s4_sub = "Completed", "Metrics saved"
    elif norm_status == "failed":
        s1, s2, s3, s4 = "done", "done", "done", "failed"
        fill_width = "100%"
        s4_label, s4_sub = "Failed", "Exception caught"
    else:
        s1, s2, s3, s4 = "upcoming", "upcoming", "upcoming", "upcoming"
        fill_width = "0%"
        s4_label, s4_sub = "Completed", "Store metrics"

    stepper_html = f"""
    <div class="stepper-container">
        <div class="stepper-title">Ingestion pipeline lifecycle progression</div>
        <div class="stepper-track">
            <div class="stepper-line">
                <div class="stepper-line-fill" style="width: {fill_width};"></div>
            </div>
            <div class="stepper-step step-{s1}">
                <div class="step-circle">1</div>
                <div class="step-label">Uploaded</div>
                <div class="step-caption">Client sent batch</div>
            </div>
            <div class="stepper-step step-{s2}">
                <div class="step-circle">2</div>
                <div class="step-label">Queued</div>
                <div class="step-caption">In S3 & broker</div>
            </div>
            <div class="stepper-step step-{s3}">
                <div class="step-circle">3</div>
                <div class="step-label">Processing</div>
                <div class="step-caption">Worker parsing</div>
            </div>
            <div class="stepper-step step-{s4}">
                <div class="step-circle">4</div>
                <div class="step-label">{s4_label}</div>
                <div class="step-caption">{s4_sub}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(stepper_html, unsafe_allow_html=True)


def get_stretch_kwarg(widget_func) -> dict:
    """Return width='stretch' if supported by the installed Streamlit version, else use_container_width=True."""
    import inspect
    if "width" in inspect.signature(widget_func).parameters:
        return {"width": "stretch"}
    return {"use_container_width": True}


def render_architecture_diagram() -> None:
    """Render the architecture diagram using Graphviz via st.graphviz_chart."""
    dot_graph = f"""
    digraph DistributedPipeline {{
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box, style="filled,rounded", fontname="IBM Plex Sans, sans-serif", fontsize=11, margin="0.25,0.12"];
        edge [fontname="IBM Plex Sans, sans-serif", fontsize=9, color="{COLOR_PRIMARY}", fontcolor="{COLOR_INK}", arrowsize=0.7];

        dashboard [label="Dashboard UI\\n(Streamlit Console)", fillcolor="#FFFFFF", color="{COLOR_PRIMARY}", penwidth=1.5];
        api [label="Ingestion API\\n(FastAPI Gateway)", fillcolor="#E8ECF1", color="{COLOR_PRIMARY}", penwidth=1.5];
        storage [label="Object Storage\\n(MinIO / AWS S3)", fillcolor="#FFFFFF", color="{SEVERITY_COLORS['INFO']}", penwidth=1.5];
        queue [label="Message Queue\\n(RabbitMQ / AWS SQS)", fillcolor="#FFFFFF", color="{SEVERITY_COLORS['WARN']}", penwidth=1.5];
        worker [label="Worker Pool\\n(Python Consumers)", fillcolor="#E8ECF1", color="{COLOR_PRIMARY}", penwidth=1.5];
        db [label="Metadata DB\\n(MongoDB / DynamoDB)", fillcolor="#FFFFFF", color="{COLOR_SUCCESS}", penwidth=1.5];

        dashboard -> api [label="POST /logs/upload\\n(file, service, env)"];
        api -> storage [label="Save raw archive\\n(immutable key)"];
        api -> db [label="Init batch record\\n(status: pending)"];
        api -> queue [label="Enqueue task\\n(ingest_id)"];
        queue -> worker [label="Dispatch task\\n(ack on success)"];
        worker -> storage [label="Fetch & stream\\nJSON Lines"];
        worker -> db [label="Write computed\\nmetrics & status"];
        dashboard -> db [label="Poll metrics & status\\n(non-blocking)", style=dashed, color="{SEVERITY_COLORS['INFO']}"];
    }}
    """
    st.graphviz_chart(dot_graph, **get_stretch_kwarg(st.graphviz_chart))


def render_empty_state(message: str, action_label: str | None = None) -> None:
    """Render clean, operations-grade empty state."""
    btn_html = ""
    if action_label:
        btn_html = f'<div style="margin-top: 0.8rem; font-size: 0.82rem; color: {COLOR_PRIMARY}; font-weight: 500;">Tip: {html.escape(action_label)}</div>'

    html_code = f"""
    <div class="empty-state-box">
        <div class="empty-state-title">No telemetry data available</div>
        <div class="empty-state-text">{html.escape(message)}</div>
        {btn_html}
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_ingestion_table(rows: list[dict]) -> None:
    """Render plain operations console table for session ingestions with status badges."""
    table_css = f"""
    <style>
    .ops-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        font-size: 0.85rem;
        background: #FFFFFF;
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        overflow: hidden;
    }}
    .ops-table th {{
        background-color: #F8FAFC;
        color: #475569;
        font-weight: 600;
        text-align: left;
        padding: 0.7rem 0.85rem;
        border-bottom: 1px solid {COLOR_BORDER};
        font-size: 0.78rem;
        text-transform: none;
    }}
    .ops-table td {{
        padding: 0.65rem 0.85rem;
        border-bottom: 1px solid #EEF1F4;
        color: {COLOR_INK};
    }}
    .ops-table tr:last-child td {{
        border-bottom: none;
    }}
    .ops-table tr:hover {{
        background-color: #F8FAFC;
    }}
    .ops-table .num-col {{
        font-family: 'IBM Plex Mono', monospace;
        text-align: right;
    }}
    .ops-table th.num-col {{
        text-align: right;
    }}
    </style>
    """

    headers = [
        "Ingestion ID",
        "Service",
        "Environment",
        "Submitted (UTC)",
        "Status",
        "Total logs",
        "Errors",
        "Warnings",
        "Critical",
        "Failure reason",
    ]
    th_html = "".join(f'<th class="{"num-col" if "logs" in h.lower() or "error" in h.lower() or "warning" in h.lower() or "critical" in h.lower() else ""}">{h}</th>' for h in headers)

    tr_html = []
    for r in rows:
        ingest_id = r.get("ingest_id", "")
        short_id = ingest_id[:8] + "..." if len(ingest_id) > 8 else ingest_id
        svc = html.escape(str(r.get("service_name", "")))
        env = html.escape(str(r.get("environment", "")))
        sub = html.escape(str(r.get("submitted_at", "")))
        badge = render_status_badge(r.get("status", "unknown"))

        tot = f"{r['total_logs']:,}" if r.get("total_logs") is not None else "-"
        err = f"{r['error_count']:,}" if r.get("error_count") is not None else "-"
        warn = f"{r['warning_count']:,}" if r.get("warning_count") is not None else "-"
        crit = f"{r['critical_count']:,}" if r.get("critical_count") is not None else "-"
        reason = html.escape(str(r.get("error_reason") or "-"))

        row_str = f"""
        <tr>
            <td style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; font-weight: 500;" title="{html.escape(ingest_id)}">{short_id}</td>
            <td>{svc}</td>
            <td>{env}</td>
            <td style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem;">{sub}</td>
            <td>{badge}</td>
            <td class="num-col">{tot}</td>
            <td class="num-col">{err}</td>
            <td class="num-col">{warn}</td>
            <td class="num-col">{crit}</td>
            <td style="color: {SEVERITY_COLORS['ERROR'] if reason != '-' else '#718299'}; font-size: 0.8rem;">{reason}</td>
        </tr>
        """
        tr_html.append(row_str)

    html_table = f"""
    {table_css}
    <div style="overflow-x: auto;">
        <table class="ops-table">
            <thead>
                <tr>{th_html}</tr>
            </thead>
            <tbody>
                {''.join(tr_html)}
            </tbody>
        </table>
    </div>
    """
    st.markdown(html_table, unsafe_allow_html=True)


def render_top_errors_table(summary: list[dict]) -> None:
    """Render plain table for top error per service in the Overview section."""
    rows = []
    for s in summary:
        svc = html.escape(str(s.get("service_name", "")))
        top = html.escape(str(s.get("top_error") or "No errors recorded"))
        errs = int(s.get("error_count", 0))
        crit = int(s.get("critical_count", 0))
        tot = int(s.get("total_logs", 0))

        raw_health = str(s.get("health", "")).lower()
        if raw_health in ("critical", "degraded", "healthy"):
            health = raw_health
        else:
            if crit > 0 or (tot > 0 and (errs / tot) > 0.05):
                health = "critical"
            elif errs > 0:
                health = "degraded"
            else:
                health = "healthy"

        badge = f'<span class="badge badge-{health}">{health.capitalize()}</span>'

        rows.append(f"""
        <tr>
            <td style="font-weight: 600; color: {COLOR_PRIMARY};">{svc}</td>
            <td style="font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #334155;">{top}</td>
            <td class="num-col">{errs:,}</td>
            <td class="num-col" style="color: {SEVERITY_COLORS['CRITICAL'] if crit > 0 else COLOR_INK}; font-weight: {600 if crit > 0 else 400};">{crit:,}</td>
            <td>{badge}</td>
        </tr>
        """)

    table_html = f"""
    <div style="overflow-x: auto;">
        <table class="ops-table">
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Top error message</th>
                    <th class="num-col">Errors</th>
                    <th class="num-col">Critical</th>
                    <th>Service health</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def render_batch_detail(rec: dict) -> None:
    """Render detailed lookup card for a specific batch query."""
    status = rec.get("status", "unknown")
    metrics = rec.get("metrics") or {}
    ingest_id = rec.get("ingest_id", "")
    created = rec.get("created_at") or "-"
    processed = rec.get("processed_at") or "-"
    err_reason = rec.get("error_reason")

    st.markdown(f"**Batch status:** {render_status_badge(status)}", unsafe_allow_html=True)
    render_pipeline_stepper(status)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total records", f"{metrics.get('total_logs', 0):,}" if metrics else "-")
    c2.metric("Errors", f"{metrics.get('error_count', 0):,}" if metrics else "-")
    c3.metric("Warnings", f"{metrics.get('warning_count', 0):,}" if metrics else "-")
    c4.metric("Critical", f"{metrics.get('critical_count', 0):,}" if metrics else "-")

    t1, t2 = st.columns(2)
    t1.caption(f"Created (UTC): {created}")
    t2.caption(f"Processed (UTC): {processed}")

    if err_reason:
        st.error(f"Failure reason: {err_reason}")


def render_architecture_stages() -> None:
    """Render the 6 pipeline stages with one-line captions for viva defense."""
    stages = [
        (
            "1. Dashboard UI",
            "Streamlit (Python)",
            "Observability console providing real-time telemetry analytics, multi-environment log ingestion, and batch lifecycle tracking.",
        ),
        (
            "2. Ingestion API",
            "FastAPI Gateway",
            "Stateless REST gateway validating incoming JSONL archives, archiving raw files to storage, and returning 201 Created immediately.",
        ),
        (
            "3. Object Storage",
            "MinIO / Amazon S3",
            "Durable and immutable object store maintaining raw audit and service log archives indexed by ingestion batch IDs.",
        ),
        (
            "4. Message Queue",
            "RabbitMQ / Amazon SQS",
            "Asynchronous buffer decoupling ingestion traffic from workers, absorbing traffic spikes, and isolating failures with a Dead Letter Queue (DLQ).",
        ),
        (
            "5. Worker Pool",
            "Python Consumers / AWS Lambda",
            "Horizontally scalable workers dequeuing tasks, streaming JSONL records line-by-line, parsing severity, and aggregating telemetry.",
        ),
        (
            "6. Metadata DB",
            "MongoDB / Amazon DynamoDB",
            "Document store preserving batch lifecycle states, computed severity counters, and service-level health aggregates.",
        ),
    ]

    for title, tech, caption in stages:
        st.markdown(
            f"""
            <div class="arch-card">
                <div class="arch-stage-header">
                    <span class="arch-stage-title">{title}</span>
                    <span class="arch-stage-tech">{tech}</span>
                </div>
                <div class="arch-stage-desc">{caption}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

