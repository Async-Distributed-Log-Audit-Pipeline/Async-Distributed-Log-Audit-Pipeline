"""UI components, design system, theming, and layout helpers for Distributed Log Analytics (LogPulse)."""

from __future__ import annotations

import html
import inspect
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# Design System & Color Palette Tokens
# ==============================================================================
COLOR_PRIMARY = "#2563EB"  # High-contrast Cobalt Blue
COLOR_PRIMARY_HOVER = "#1D4ED8"
COLOR_PAGE_BG = "#F8FAFC"
COLOR_SURFACE = "#FFFFFF"
COLOR_BORDER = "#E2E8F0"
COLOR_INK = "#0F172A"
COLOR_MUTED = "#64748B"

SEVERITY_COLORS = {
    "INFO": "#0284C7",
    "WARN": "#F59E0B",
    "ERROR": "#EF4444",
    "CRITICAL": "#B91C1C",
}

STATUS_CONFIG = {
    "pending": {"label": "Queued", "class": "badge-queued", "icon": "⏱"},
    "processing": {"label": "Processing", "class": "badge-processing", "icon": "⚡"},
    "completed": {"label": "Completed", "class": "badge-completed", "icon": "✓"},
    "failed": {"label": "Failed", "class": "badge-failed", "icon": "✕"},
}

# The app owns its full theme (instead of following the OS setting) so text,
# cards, inputs, tabs and charts always have matching contrast.
THEMES = {
    "Light": {
        "page": "#F8FAFC",
        "surface": "#FFFFFF",
        "sidebar": "#FFFFFF",
        "border": "#E2E8F0",
        "ink": "#0F172A",
        "muted": "#64748B",
        "input": "#FFFFFF",
        "hover": "#93C5FD",
        "primary": "#2563EB",
        "tint": "rgba(37, 99, 235, 0.07)",
        "grid": "rgba(148, 163, 184, 0.20)",
        "shadow": "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
        "shadow_hover": "0 14px 30px -8px rgba(37, 99, 235, 0.20), 0 4px 6px -2px rgba(15, 23, 42, 0.05)",
    },
    "Dark": {
        "page": "#0B1120",
        "surface": "#111827",
        "sidebar": "#0F172A",
        "border": "#243044",
        "ink": "#F1F5F9",
        "muted": "#94A3B8",
        "input": "#1E293B",
        "hover": "#3B82F6",
        "primary": "#3B82F6",
        "tint": "rgba(59, 130, 246, 0.12)",
        "grid": "rgba(148, 163, 184, 0.14)",
        "shadow": "0 4px 14px rgba(0, 0, 0, 0.35)",
        "shadow_hover": "0 14px 32px -6px rgba(0, 0, 0, 0.55), 0 0 18px rgba(59, 130, 246, 0.22)",
    },
}


def get_theme_name() -> str:
    name = st.session_state.get("ui_theme", "Light")
    return name if name in THEMES else "Light"


def _p() -> dict:
    return THEMES[get_theme_name()]


# ==============================================================================
# Helpers
# ==============================================================================
def _minify(markup: str) -> str:
    """Strip indentation/blank lines so Markdown never treats HTML as a code block."""
    return "".join(line.strip() for line in markup.splitlines())


def _html(markup: str) -> None:
    st.markdown(_minify(markup), unsafe_allow_html=True)


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_num(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _esc(value)


def get_stretch_kwarg(func) -> dict:
    """Return the full-width kwarg supported by the installed Streamlit version."""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return {}
    if "width" in params:
        return {"width": "stretch"}
    if "use_container_width" in params:
        return {"use_container_width": True}
    return {}


# ==============================================================================
# Custom CSS Theme
# ==============================================================================
_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600"
    "&family=Inter:wght@400;500;600;700&display=swap');"
)

_BASE_CSS = """
/* ---------- App shell ---------- */
.stApp { background: var(--page-bg) !important; color: var(--text-main); font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stHeader"] * { color: var(--text-muted) !important; }
.block-container { padding-top: 2.6rem !important; padding-bottom: 3rem !important; max-width: 1380px !important; }

/* Keep icon fonts working (never override Material icons with Inter) */
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-icons"] { font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important; color: var(--text-muted) !important; }

/* ---------- Typography ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { color: var(--text-main) !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.015em; }
.stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp textarea { font-family: 'Inter', sans-serif !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, .stApp label { color: var(--text-main) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] [data-testid="stMarkdownContainer"] p { color: var(--text-muted) !important; }
.stApp code, .stApp pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }
.stApp :not(pre) > code { background: var(--tint) !important; color: var(--primary) !important; border-radius: 5px; padding: 0.1rem 0.4rem; }
.stApp hr { border-color: var(--card-border) !important; background: var(--card-border) !important; opacity: 1; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color: var(--text-main) !important; font-family: 'IBM Plex Mono', monospace !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: var(--text-muted) !important; }
[data-testid="stAlert"] * { color: var(--text-main) !important; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background: var(--sidebar-bg) !important; }
[data-testid="stSidebar"] { border-right: 1px solid var(--card-border); }
[data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"] { overflow-x: hidden !important; }

/* ---------- Inputs ---------- */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div { background: var(--input-bg) !important; border-color: var(--card-border) !important; border-radius: 8px !important; }
.stApp input, .stApp textarea { color: var(--text-main) !important; -webkit-text-fill-color: var(--text-main) !important; }
.stApp input::placeholder, .stApp textarea::placeholder { color: var(--text-muted) !important; -webkit-text-fill-color: var(--text-muted) !important; opacity: 0.8; }
.stApp [data-baseweb="select"] * { color: var(--text-main) !important; }
.stApp [data-baseweb="select"] svg { fill: var(--text-muted) !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul { background: var(--card-bg) !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: var(--text-main) !important; }
[data-baseweb="popover"] li:hover { background: var(--tint) !important; }
[data-testid="stFileUploaderDropzone"] { background: var(--input-bg) !important; border: 1.5px dashed var(--card-border) !important; border-radius: 12px !important; }
[data-testid="stFileUploaderDropzone"] * { color: var(--text-muted) !important; }
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploaderDropzone"] button * { color: var(--text-main) !important; }
[data-testid="stForm"] { background: var(--card-bg); border: 1px solid var(--card-border) !important; border-radius: 12px; box-shadow: var(--card-shadow); }
[data-testid="stExpander"] { background: var(--card-bg); border: 1px solid var(--card-border) !important; border-radius: 10px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--text-main) !important; }

/* ---------- Buttons ---------- */
.stApp button[kind="secondary"], .stApp button[kind="secondaryFormSubmit"], .stApp [data-testid="stBaseButton-secondary"], .stApp [data-testid="stBaseButton-secondaryFormSubmit"], .stApp [data-testid="stDownloadButton"] button { background: var(--card-bg) !important; color: var(--text-main) !important; border: 1px solid var(--card-border) !important; border-radius: 8px !important; font-weight: 600; transition: all 0.18s ease; }
.stApp button[kind="secondary"]:hover, .stApp [data-testid="stBaseButton-secondary"]:hover, .stApp [data-testid="stDownloadButton"] button:hover { border-color: var(--primary) !important; color: var(--primary) !important; transform: translateY(-1px); }
.stApp button[kind="primary"], .stApp button[kind="primaryFormSubmit"], .stApp [data-testid="stBaseButton-primary"], .stApp [data-testid="stBaseButton-primaryFormSubmit"] { background: var(--primary) !important; color: #FFFFFF !important; border: 1px solid var(--primary) !important; border-radius: 8px !important; font-weight: 600; box-shadow: 0 4px 12px -2px rgba(37, 99, 235, 0.45); }
.stApp button[kind="primary"]:hover, .stApp [data-testid="stBaseButton-primary"]:hover, .stApp [data-testid="stBaseButton-primaryFormSubmit"]:hover { filter: brightness(1.1); }
.stApp button [data-testid="stMarkdownContainer"] p { color: inherit !important; }

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 0.35rem; border-bottom: 1px solid var(--card-border); }
.stTabs [data-baseweb="tab"] { color: var(--text-muted) !important; background: transparent !important; font-weight: 600; padding: 0.65rem 1.05rem; border-radius: 8px 8px 0 0; }
.stTabs [data-baseweb="tab"] p { color: inherit !important; font-weight: 600; }
.stTabs [data-baseweb="tab"]:hover { color: var(--text-main) !important; background: var(--tint) !important; }
.stTabs [aria-selected="true"] { color: var(--primary) !important; background: var(--tint) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--primary) !important; height: 3px !important; }
.stTabs [data-baseweb="tab-border"] { background: transparent !important; }

/* ---------- Top bar ---------- */
.topbar-container { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; padding: 1rem 1.4rem; margin-bottom: 1.5rem; background: linear-gradient(135deg, var(--card-bg) 0%, var(--tint) 100%); border: 1px solid var(--card-border); border-radius: 14px; box-shadow: var(--card-shadow); }
.topbar-left { display: flex; align-items: center; gap: 0.95rem; }
.topbar-logo { width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.45rem; color: #FFFFFF; background: linear-gradient(135deg, #38BDF8, var(--primary)); box-shadow: 0 6px 16px -4px rgba(37, 99, 235, 0.55); }
.topbar-title { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2; color: var(--text-main); }
.topbar-subtitle { font-size: 0.84rem; color: var(--text-muted); margin-top: 0.2rem; }
.topbar-indicator { display: inline-flex; align-items: center; gap: 0.6rem; padding: 0.5rem 0.95rem; border-radius: 20px; font-size: 0.82rem; font-weight: 600; color: var(--text-main); border: 1px solid var(--card-border); background: var(--card-bg); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06); }

.indicator-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot-connected { background-color: #10B981; animation: radar-pulse-green 2s infinite ease-out; }
.dot-demo { background-color: #F59E0B; animation: radar-pulse-amber 2s infinite ease-out; }
.dot-unreachable { background-color: #EF4444; animation: radar-pulse-red 2s infinite ease-out; }
@keyframes radar-pulse-green { 0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); } 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
@keyframes radar-pulse-amber { 0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); } 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); } }
@keyframes radar-pulse-red { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }

/* ---------- KPI cards ---------- */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.1rem; margin-bottom: 1.5rem; }
@media (max-width: 960px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 540px) { .kpi-grid { grid-template-columns: 1fr; } }
.kpi-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.2rem 1.3rem; position: relative; box-shadow: var(--card-shadow); transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s ease, border-color 0.22s ease; overflow: hidden; }
.kpi-card:hover { transform: translateY(-3px); box-shadow: var(--card-hover-shadow); border-color: var(--card-hover-border); }
.kpi-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.kpi-total::before { background: linear-gradient(90deg, #38BDF8, var(--primary)); }
.kpi-warn::before { background: linear-gradient(90deg, #FCD34D, #F59E0B); }
.kpi-error::before { background: linear-gradient(90deg, #F87171, #EF4444); }
.kpi-critical::before { background: linear-gradient(90deg, #EF4444, #B91C1C); }
.kpi-header-row { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; margin-bottom: 0.55rem; }
.kpi-label { font-size: 0.76rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-badge { font-size: 0.68rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 12px; font-family: 'IBM Plex Mono', monospace; white-space: nowrap; }
.kpi-badge-total { background: rgba(37, 99, 235, 0.12); color: #3B82F6; }
.kpi-badge-warn { background: rgba(245, 158, 11, 0.14); color: #D97706; }
.kpi-badge-error { background: rgba(239, 68, 68, 0.14); color: #EF4444; }
.kpi-badge-critical { background: rgba(185, 28, 28, 0.16); color: #DC2626; }
.kpi-value { font-size: 2.1rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; line-height: 1.1; letter-spacing: -0.02em; color: var(--text-main); }
.kpi-subtext { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.5rem; display: flex; align-items: center; gap: 0.35rem; }

/* ---------- Service cards ---------- */
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 1.1rem; margin-bottom: 1.5rem; }
.service-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.15rem 1.3rem; box-shadow: var(--card-shadow); transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s ease, border-color 0.22s ease; }
.service-card:hover { transform: translateY(-3px); box-shadow: var(--card-hover-shadow); border-color: var(--card-hover-border); }
.service-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; gap: 0.5rem; }
.service-name { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; color: var(--text-main); }
.service-metric-row { display: flex; justify-content: space-between; font-size: 0.84rem; padding: 0.3rem 0; border-bottom: 1px solid rgba(148, 163, 184, 0.14); }
.service-metric-label { color: var(--text-muted); }
.service-metric-val { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: var(--text-main); }
.meter-container { margin-top: 0.7rem; margin-bottom: 0.4rem; }
.meter-track { width: 100%; height: 6px; background: rgba(148, 163, 184, 0.22); border-radius: 3px; overflow: hidden; }
.meter-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.service-top-error { margin-top: 0.7rem; font-size: 0.76rem; font-family: 'IBM Plex Mono', monospace; background: rgba(148, 163, 184, 0.09); border: 1px solid var(--card-border); border-radius: 6px; padding: 0.45rem 0.6rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---------- Badges & pills ---------- */
.badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.22rem 0.65rem; border-radius: 20px; font-size: 0.74rem; font-weight: 600; letter-spacing: 0.01em; white-space: nowrap; }
.badge-queued { background-color: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; }
.badge-processing { background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; animation: badge-pulse 2s infinite ease-in-out; }
.badge-completed { background-color: #D1FAE5; color: #047857; border: 1px solid #A7F3D0; }
.badge-failed { background-color: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; }
.badge-healthy { background-color: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
.badge-degraded { background-color: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
.badge-critical { background-color: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
@keyframes badge-pulse { 0% { opacity: 1; } 50% { opacity: 0.55; } 100% { opacity: 1; } }
.env-pill { display: inline-block; padding: 0.12rem 0.55rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace; background: rgba(148, 163, 184, 0.16); color: var(--text-muted); }
.env-prod { background: rgba(37, 99, 235, 0.14); color: #3B82F6; }
.env-staging { background: rgba(245, 158, 11, 0.16); color: #D97706; }
.env-dev { background: rgba(16, 185, 129, 0.15); color: #059669; }

/* ---------- Pipeline stepper ---------- */
.stepper-container { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.3rem 1.4rem 1.2rem 1.4rem; margin: 0.5rem 0 1rem 0; box-shadow: var(--card-shadow); }
.stepper-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; }
.stepper-title { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stepper-track { display: flex; align-items: flex-start; position: relative; }
.stepper-step { display: flex; flex-direction: column; align-items: center; position: relative; z-index: 2; width: 25%; text-align: center; }
.step-circle { width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.88rem; font-weight: 700; background: var(--card-bg); border: 2px solid var(--card-border); color: var(--text-muted); margin-bottom: 0.5rem; transition: all 0.3s ease; }
.step-done .step-circle { background: #10B981; border-color: #10B981; color: #FFFFFF; box-shadow: 0 0 12px rgba(16, 185, 129, 0.35); }
.step-active .step-circle { background: var(--primary); border-color: var(--primary); color: #FFFFFF; box-shadow: 0 0 12px rgba(37, 99, 235, 0.45); }
.step-pulsing .step-circle { background: #F59E0B; border-color: #F59E0B; color: #FFFFFF; animation: badge-pulse 1.6s infinite ease-in-out; box-shadow: 0 0 12px rgba(245, 158, 11, 0.45); }
.step-failed .step-circle { background: #EF4444; border-color: #EF4444; color: #FFFFFF; box-shadow: 0 0 12px rgba(239, 68, 68, 0.45); }
.step-label { font-size: 0.84rem; font-weight: 600; color: var(--text-main); }
.step-caption { font-size: 0.72rem; color: var(--text-muted); margin-top: 0.15rem; }
.stepper-line { position: absolute; top: 18px; left: 12.5%; right: 12.5%; height: 3px; background: var(--card-border); z-index: 1; border-radius: 2px; }
.stepper-line-fill { height: 100%; background: linear-gradient(90deg, #10B981, var(--primary)); border-radius: 2px; transition: width 0.4s ease; }

/* ---------- Tables ---------- */
.tbl-wrap { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; overflow-x: auto; box-shadow: var(--card-shadow); margin-bottom: 1.2rem; }
table.tbl { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
.tbl th { text-align: left; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); padding: 0.75rem 1rem; border-bottom: 1px solid var(--card-border); background: var(--tint); white-space: nowrap; }
.tbl td { padding: 0.7rem 1rem; border-bottom: 1px solid rgba(148, 163, 184, 0.14); color: var(--text-main); vertical-align: middle; }
.tbl tbody tr:last-child td { border-bottom: none; }
.tbl tbody tr:hover td { background: var(--tint); }
.tbl .num { font-family: 'IBM Plex Mono', monospace; text-align: right; white-space: nowrap; }
.tbl th.num { text-align: right; }
.tbl .mono-cell { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; }
.tbl .trunc { max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: var(--text-muted); }
.tbl .err-hot { color: #EF4444; font-weight: 600; }

/* ---------- Batch detail ---------- */
.detail-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.2rem 1.4rem; box-shadow: var(--card-shadow); margin-bottom: 1rem; }
.detail-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.6rem; margin-bottom: 0.9rem; }
.detail-id { font-family: 'IBM Plex Mono', monospace; font-size: 0.9rem; font-weight: 600; color: var(--text-main); word-break: break-all; }
.detail-meta { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem; }
.detail-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; }
@media (max-width: 700px) { .detail-stats { grid-template-columns: repeat(2, 1fr); } }
.detail-stat { background: var(--tint); border: 1px solid var(--card-border); border-radius: 10px; padding: 0.7rem 0.9rem; }
.detail-stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; }
.detail-stat-val { font-family: 'IBM Plex Mono', monospace; font-size: 1.25rem; font-weight: 700; color: var(--text-main); margin-top: 0.15rem; }
.detail-error { margin-top: 0.9rem; padding: 0.8rem 1rem; border-radius: 10px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.35); color: var(--text-main); font-size: 0.85rem; }
.detail-error b { color: #EF4444; }
.raw-pre { background: var(--input-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 0.9rem 1rem; font-family: 'IBM Plex Mono', monospace; font-size: 0.76rem; color: var(--text-main); overflow-x: auto; margin: 0; }

/* ---------- Architecture ---------- */
.flow { display: flex; flex-wrap: wrap; align-items: stretch; gap: 0.5rem; margin: 0.5rem 0 1rem 0; }
.flow-node { flex: 1 1 140px; min-width: 130px; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1rem 0.8rem; text-align: center; box-shadow: var(--card-shadow); transition: transform 0.2s ease, border-color 0.2s ease; }
.flow-node:hover { transform: translateY(-3px); border-color: var(--card-hover-border); }
.flow-icon { font-size: 1.5rem; margin-bottom: 0.3rem; }
.flow-title { font-size: 0.9rem; font-weight: 600; color: var(--text-main); }
.flow-tech { font-size: 0.72rem; font-family: 'IBM Plex Mono', monospace; color: var(--text-muted); margin-top: 0.2rem; }
.flow-arrow { display: flex; align-items: center; color: var(--primary); font-weight: 700; font-size: 1.2rem; }
.flow-note { border: 1.5px dashed var(--card-border); border-radius: 10px; padding: 0.75rem 1rem; font-size: 0.82rem; color: var(--text-muted); margin-bottom: 1rem; }
.flow-note b { color: var(--text-main); }
.arch-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1.1rem 1.3rem; margin-bottom: 0.85rem; box-shadow: var(--card-shadow); transition: transform 0.2s ease, border-color 0.2s ease; }
.arch-card:hover { transform: translateX(4px); border-color: var(--card-hover-border); }
.arch-stage-header { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.arch-stage-title { font-size: 0.96rem; font-weight: 600; color: var(--primary); }
.arch-stage-tech { font-size: 0.76rem; font-family: 'IBM Plex Mono', monospace; color: var(--text-muted); background: rgba(148, 163, 184, 0.14); padding: 0.15rem 0.5rem; border-radius: 4px; }
.arch-stage-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.45; }

/* ---------- Empty state ---------- */
.empty-state-box { background: var(--card-bg); border: 2px dashed var(--card-border); border-radius: 14px; padding: 2.8rem 1.8rem; text-align: center; margin: 1.5rem 0; }
.empty-state-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.empty-state-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text-main); }
.empty-state-text { font-size: 0.88rem; color: var(--text-muted); max-width: 520px; margin: 0 auto; }
.empty-state-action { display: inline-block; margin-top: 1rem; padding: 0.4rem 0.95rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; color: var(--primary); background: var(--tint); border: 1px solid var(--card-border); }

/* ---------- Sidebar brand ---------- */
.sidebar-brand-box { padding: 0.4rem 0.2rem 1.1rem 0.2rem; border-bottom: 1px solid var(--card-border); margin-bottom: 1.1rem; }
.sidebar-brand-title { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; display: flex; align-items: center; gap: 0.5rem; color: var(--text-main); }
.sidebar-badge { font-size: 0.68rem; font-weight: 600; background: var(--tint); color: var(--primary); padding: 0.15rem 0.5rem; border-radius: 10px; letter-spacing: 0.05em; }
.sidebar-sub { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
.cluster-status-card { background: var(--tint); border: 1px solid var(--card-border); border-radius: 10px; padding: 0.8rem 0.9rem; margin-bottom: 1rem; font-size: 0.78rem; color: var(--text-main); }
.cluster-status-head { font-weight: 600; margin-bottom: 0.4rem; color: var(--text-muted); text-transform: uppercase; font-size: 0.68rem; letter-spacing: 0.05em; }
.cluster-status-row { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; padding: 0.22rem 0; }
.cluster-ok { color: #10B981; font-weight: 600; white-space: nowrap; }
"""


def inject_custom_css(theme: str | None = None) -> None:
    """Inject fonts, theme variables and component styling for the active theme."""
    p = THEMES.get(theme or get_theme_name(), THEMES["Light"])
    root = (
        ":root{"
        f"--page-bg:{p['page']};--card-bg:{p['surface']};--sidebar-bg:{p['sidebar']};"
        f"--card-border:{p['border']};--text-main:{p['ink']};--text-muted:{p['muted']};"
        f"--input-bg:{p['input']};--card-hover-border:{p['hover']};--primary:{p['primary']};"
        f"--tint:{p['tint']};--card-shadow:{p['shadow']};--card-hover-shadow:{p['shadow_hover']};"
        "}"
    )
    st.markdown(f"<style>{_FONT_IMPORT}{root}{_minify(_BASE_CSS)}</style>", unsafe_allow_html=True)


# ==============================================================================
# Header & Navigation Components
# ==============================================================================
def render_header(status: str, api_url: str) -> None:
    """Render top bar with project title and pulsing connection indicator."""
    if status == "connected":
        dot, text = "dot-connected", "Cluster Online • Live Ingestion"
    elif status == "demo":
        dot, text = "dot-demo", "Demo Mode (Mock Worker)"
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
    """Render 4 elevated KPI cards with micro-badges."""
    err_rate = (errors / total_logs * 100) if total_logs > 0 else 0.0
    warn_rate = (warnings / total_logs * 100) if total_logs > 0 else 0.0
    crit_rate = (critical / total_logs * 100) if total_logs > 0 else 0.0

    _html(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card kpi-total">
                <div class="kpi-header-row"><span class="kpi-label">Total Ingested Logs</span><span class="kpi-badge kpi-badge-total">ALL SERVICES</span></div>
                <div class="kpi-value">{total_logs:,}</div>
                <div class="kpi-subtext"><span>⚡ Real-time ingestion stream</span></div>
            </div>
            <div class="kpi-card kpi-warn">
                <div class="kpi-header-row"><span class="kpi-label">Warnings</span><span class="kpi-badge kpi-badge-warn">{warn_rate:.1f}% RATIO</span></div>
                <div class="kpi-value">{warnings:,}</div>
                <div class="kpi-subtext"><span>⚠️ Transient exceptions reported</span></div>
            </div>
            <div class="kpi-card kpi-error">
                <div class="kpi-header-row"><span class="kpi-label">Application Errors</span><span class="kpi-badge kpi-badge-error">{err_rate:.2f}% ERROR RATE</span></div>
                <div class="kpi-value">{errors:,}</div>
                <div class="kpi-subtext"><span>🚨 Unhandled service exceptions</span></div>
            </div>
            <div class="kpi-card kpi-critical">
                <div class="kpi-header-row"><span class="kpi-label">Critical Incidents</span><span class="kpi-badge kpi-badge-critical">{crit_rate:.2f}% CRITICAL</span></div>
                <div class="kpi-value">{critical:,}</div>
                <div class="kpi-subtext"><span>🛑 Requires immediate intervention</span></div>
            </div>
        </div>
        """
    )


def _service_health(svc: dict) -> str:
    total = int(svc.get("total_logs", 0) or 0)
    errors = int(svc.get("error_count", 0) or 0)
    critical = int(svc.get("critical_count", 0) or 0)
    raw = str(svc.get("health", "")).lower()
    if raw in ("critical", "degraded", "healthy"):
        return raw
    if critical > 0 or (total > 0 and (errors / total) > 0.05):
        return "critical"
    if errors > 0:
        return "degraded"
    return "healthy"


def render_service_cards(services: list[dict]) -> None:
    """Render microservice health card grid with embedded error rate meters."""
    cards = ['<div class="service-grid">']
    for svc in services:
        name = svc.get("service_name", "unknown")
        total = int(svc.get("total_logs", 0) or 0)
        errors = int(svc.get("error_count", 0) or 0)
        critical = int(svc.get("critical_count", 0) or 0)
        health = _service_health(svc)

        error_rate = (errors / total * 100) if total > 0 else 0.0
        fill = min(error_rate * 5, 100)
        color = {"healthy": "#10B981", "degraded": "#F59E0B"}.get(health, "#EF4444")
        crit_color = "#EF4444" if critical > 0 else "inherit"
        top_err = svc.get("top_error") or "No operational errors recorded"

        cards.append(
            f"""
            <div class="service-card">
                <div class="service-card-header">
                    <span class="service-name">{_esc(name)}</span>
                    <span class="badge badge-{health}">● {health.capitalize()}</span>
                </div>
                <div class="service-metric-row"><span class="service-metric-label">Processed volume</span><span class="service-metric-val">{total:,}</span></div>
                <div class="service-metric-row"><span class="service-metric-label">Error frequency</span><span class="service-metric-val">{errors:,} ({error_rate:.2f}%)</span></div>
                <div class="service-metric-row"><span class="service-metric-label">Critical alerts</span><span class="service-metric-val" style="color:{crit_color};">{critical:,}</span></div>
                <div class="meter-container"><div class="meter-track"><div class="meter-fill" style="width:{fill:.1f}%;background:{color};"></div></div></div>
                <div class="service-top-error" title="{_esc(top_err)}">🔍 {_esc(top_err)}</div>
            </div>
            """
        )
    cards.append("</div>")
    _html("".join(cards))


def render_status_badge(status: str) -> str:
    """Return HTML markup for an operational status pill badge with icon."""
    key = str(status or "unknown").lower()
    cfg = STATUS_CONFIG.get(key, {"label": key.capitalize(), "class": "badge-queued", "icon": "•"})
    return f'<span class="badge {cfg["class"]}"><span>{cfg["icon"]}</span><span>{cfg["label"]}</span></span>'


# ==============================================================================
# Interactive Charts (Plotly)
# ==============================================================================
def _axis(p: dict, title: str = "", grid: bool = True) -> dict:
    return dict(
        title=title,
        tickfont=dict(family="IBM Plex Mono", size=11, color=p["muted"]),
        title_font=dict(color=p["muted"]),
        showgrid=grid,
        gridcolor=p["grid"],
        zeroline=False,
        linecolor=p["border"],
    )


def _base_layout(p: dict, height: int, top: int = 25) -> dict:
    return dict(
        height=height,
        margin=dict(l=15, r=15, t=top, b=25),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color=p["ink"]),
        hoverlabel=dict(bgcolor=p["surface"], bordercolor=p["border"], font=dict(color=p["ink"], family="Inter, sans-serif")),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1, title_text="", font=dict(color=p["ink"])),
    )


def create_severity_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar chart of severity per service."""
    p = _p()
    fig = go.Figure()
    services = df["service_name"].tolist() if "service_name" in df else []
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
                marker=dict(color=color, line=dict(color=p["surface"], width=0.8)),
                hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:,}}<extra></extra>",
            )
        )
    fig.update_layout(
        **_base_layout(p, 330),
        barmode="stack",
        xaxis=_axis(p, grid=False),
        yaxis=_axis(p, "Log volume"),
    )
    return fig


def create_severity_donut_chart(total_logs: int, errors: int, warnings: int, critical: int, info: int) -> go.Figure:
    """Donut chart of aggregate severity with fault-free percentage in the centre."""
    p = _p()
    labels = ["INFO", "WARN", "ERROR", "CRITICAL"]
    values = [info, warnings, errors, critical]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.7,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[SEVERITY_COLORS[k] for k in labels], line=dict(color=p["surface"], width=2)),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
        )
    )
    fault_free = 100.0 if total_logs <= 0 else max(0.0, 100.0 - (errors + critical) / total_logs * 100)
    layout = _base_layout(p, 330, top=10)
    layout["legend"] = dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, font=dict(color=p["ink"]))
    fig.update_layout(
        **layout,
        annotations=[
            dict(
                text=f"<b>{fault_free:.2f}%</b><br><span style='font-size:11px;color:{p['muted']}'>fault-free</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=24, family="IBM Plex Mono", color=p["ink"]),
            )
        ],
    )
    return fig


def create_error_timeline_chart(timeline_df: pd.DataFrame) -> go.Figure:
    """Area spline chart of severity breakdown over time."""
    p = _p()
    fig = go.Figure()
    if timeline_df.empty or "timestamp" not in timeline_df:
        return fig

    traces = [
        ("INFO", "info", SEVERITY_COLORS["INFO"], "rgba(2, 132, 199, 0.12)"),
        ("WARN", "warn", SEVERITY_COLORS["WARN"], "rgba(245, 158, 11, 0.16)"),
        ("ERROR", "error", SEVERITY_COLORS["ERROR"], "rgba(239, 68, 68, 0.24)"),
        ("CRITICAL", "critical", SEVERITY_COLORS["CRITICAL"], "rgba(185, 28, 28, 0.32)"),
    ]
    for label, col, line_color, fill_color in traces:
        if col in timeline_df:
            fig.add_trace(
                go.Scatter(
                    name=label,
                    x=timeline_df["timestamp"],
                    y=timeline_df[col],
                    mode="lines",
                    line=dict(shape="spline", width=2, color=line_color),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    hovertemplate=f"<b>{label}</b>: %{{y:,}}<extra></extra>",
                )
            )
    fig.update_layout(
        **_base_layout(p, 340, top=35),
        hovermode="x unified",
        xaxis=_axis(p, grid=False),
        yaxis=_axis(p, "Events / hour"),
    )
    return fig


def generate_demo_timeline_data(summary_data: list[dict] | None = None, hours: int = 24) -> pd.DataFrame:
    """Build a deterministic hourly severity timeline from aggregate counters."""
    summary_data = summary_data or []

    def _tot(key: str) -> int:
        total = 0
        for item in summary_data:
            try:
                total += int(float(item.get(key, 0) or 0))
            except (TypeError, ValueError):
                continue
        return total

    total, err, warn, crit = _tot("total_logs"), _tot("error_count"), _tot("warning_count"), _tot("critical_count")
    if total <= 0:
        total = 48000
        err, warn, crit = int(total * 0.02), int(total * 0.06), int(total * 0.004)

    rng = np.random.default_rng((total + err * 7 + warn * 13 + crit * 31) % (2**32))
    x = np.arange(hours)
    per_hour = (total / hours) * (1 + 0.35 * np.sin((x - 6) / hours * 2 * np.pi))

    r_err, r_warn, r_crit = err / total, warn / total, crit / total
    r_info = max(0.0, 1 - r_err - r_warn - r_crit)

    info = rng.poisson(per_hour * r_info)
    warn_s = rng.poisson(per_hour * r_warn)
    err_s = rng.poisson(per_hour * r_err).astype(float)
    crit_s = rng.poisson(per_hour * r_crit).astype(float)

    spike = int(rng.integers(hours // 2, hours - 2))
    err_s[spike] *= 3
    crit_s[spike] += max(1, int(crit_s.mean()))

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    stamps = [end - timedelta(hours=hours - 1 - i) for i in range(hours)]
    return pd.DataFrame(
        {
            "timestamp": stamps,
            "info": info.astype(int),
            "warn": warn_s.astype(int),
            "error": err_s.astype(int),
            "critical": crit_s.astype(int),
        }
    )


# ==============================================================================
# Pipeline stepper, empty state, tables
# ==============================================================================
_PIPELINE_STEPS = [
    ("Gateway", "Validated & archived"),
    ("Queue", "Buffered in broker"),
    ("Worker", "Parsing & aggregating"),
    ("Result", "Metrics persisted"),
]

_STEP_STATES = {
    "upcoming": ["idle", "idle", "idle", "idle"],
    "pending": ["done", "active", "idle", "idle"],
    "processing": ["done", "done", "pulsing", "idle"],
    "completed": ["done", "done", "done", "done"],
    "failed": ["done", "done", "failed", "idle"],
}


def render_pipeline_stepper(status: str) -> None:
    """Horizontal stepper showing gateway → queue → worker → result progression."""
    key = str(status or "upcoming").lower()
    states = _STEP_STATES.get(key, _STEP_STATES["upcoming"])

    last_lit = max((i for i, s in enumerate(states) if s != "idle"), default=-1)
    fill_pct = 0 if last_lit <= 0 else last_lit / (len(states) - 1) * 100

    steps_html = []
    for i, ((label, caption), state) in enumerate(zip(_PIPELINE_STEPS, states)):
        symbol = "✓" if state == "done" else "✕" if state == "failed" else str(i + 1)
        steps_html.append(
            f'<div class="stepper-step step-{state}"><div class="step-circle">{symbol}</div>'
            f'<div class="step-label">{label}</div><div class="step-caption">{caption}</div></div>'
        )

    badge = render_status_badge(key) if key in STATUS_CONFIG else ""
    _html(
        f"""
        <div class="stepper-container">
            <div class="stepper-head"><span class="stepper-title">Pipeline Progression</span>{badge}</div>
            <div class="stepper-track">
                <div class="stepper-line"><div class="stepper-line-fill" style="width:{fill_pct:.0f}%;"></div></div>
                {"".join(steps_html)}
            </div>
        </div>
        """
    )


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


def render_top_errors_table(services: list[dict]) -> None:
    """Top error signature per service."""
    ordered = sorted(services, key=lambda s: int(s.get("error_count", 0) or 0), reverse=True)
    body = []
    for svc in ordered:
        total = int(svc.get("total_logs", 0) or 0)
        errors = int(svc.get("error_count", 0) or 0)
        critical = int(svc.get("critical_count", 0) or 0)
        rate = (errors / total * 100) if total else 0.0
        top = svc.get("top_error") or "—"
        err_cls = "num err-hot" if errors > 0 else "num"
        body.append(
            "<tr>"
            f'<td><b>{_esc(svc.get("service_name", "unknown"))}</b></td>'
            f'<td><div class="trunc" title="{_esc(top)}">{_esc(top)}</div></td>'
            f'<td class="{err_cls}">{errors:,}</td>'
            f'<td class="num">{critical:,}</td>'
            f'<td class="num">{rate:.2f}%</td>'
            f"<td>{_health_badge(svc)}</td>"
            "</tr>"
        )
    _html(
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
        '<th>Service</th><th>Top error signature</th><th class="num">Errors</th>'
        '<th class="num">Critical</th><th class="num">Error rate</th><th>Health</th>'
        f"</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _health_badge(svc: dict) -> str:
    health = _service_health(svc)
    return f'<span class="badge badge-{health}">● {health.capitalize()}</span>'


def render_batch_detail(record: dict) -> None:
    """Comprehensive diagnostic inspector for an ingestion batch with line-by-line error breakdown."""
    if not record:
        st.warning("No record details provided.")
        return

    record = record or {}
    metrics = record.get("metrics") or {}
    status = str(record.get("status", "unknown")).lower()
    reason = record.get("error_reason")
    top_error = record.get("top_error")
    report = record.get("report") or {}

    health = report.get("health") or ("failed" if status == "failed" else "pending")
    service_name = record.get("service_name", "unknown")
    environment = record.get("environment", "prod")
    object_key = record.get("object_key", "—")
    created = record.get("created_at") or "—"
    started = record.get("processing_started_at") or "—"
    processed = record.get("processed_at") or "—"

    stats = [
        ("Total logs", metrics.get("total_logs")),
        ("Info", metrics.get("info_count")),
        ("Warnings", metrics.get("warning_count")),
        ("Errors", metrics.get("error_count")),
        ("Critical", metrics.get("critical_count")),
    ]
    stats_html = "".join(
        f'<div class="detail-stat"><div class="detail-stat-label">{label}</div><div class="detail-stat-val">{_fmt_num(val)}</div></div>'
        for label, val in stats
    )
    reason_html = f'<div class="detail-error"><b>Pipeline Failure Reason:</b> {_esc(reason)}</div>' if reason else ""

    h_badge = f'<span class="badge badge-{health.lower()}">● {health.capitalize()}</span>' if health else ""

    _html(
        f"""
        <div class="detail-card">
            <div class="detail-head">
                <div>
                    <div class="detail-id">{_esc(record.get("ingest_id", "—"))}</div>
                    <div class="detail-meta">{_esc(service_name)} · {_esc(environment)} · Storage: <code>{_esc(object_key)}</code></div>
                </div>
                <div style="display:flex; gap:0.5rem; align-items:center;">
                    {h_badge}
                    {render_status_badge(status)}
                </div>
            </div>
            <div class="detail-stats">{stats_html}</div>
            {reason_html}
        </div>
        """
    )

    st.caption(f"**Submitted:** `{created}` | **Started:** `{started}` | **Processed:** `{processed}`")

    if top_error:
        st.warning(f"**Top Frequent Error Signature:** {top_error}")

    # 1. Audit Rule Findings & Diagnostic Reasons
    findings = report.get("findings") or []
    if findings:
        st.markdown("#### 🔍 Audit Rule Findings & Diagnostic Reasons")
        for f in findings:
            f_title = f.get("title", f.get("id", "Finding"))
            f_sev = str(f.get("severity", "warning")).lower()
            f_count = f.get("count", 1)
            f_hint = f.get("hint", "")
            f_example = f.get("example", "")

            sev_badge_class = "badge-critical" if f_sev in ("error", "critical") else "badge-degraded" if f_sev == "warning" else "badge-completed"
            sev_badge = f'<span class="badge {sev_badge_class}">{f_sev.upper()}</span>'

            st.markdown(
                f"**{f_title}** &nbsp; ({f_count} occurrence{'s' if f_count != 1 else ''}) &nbsp; {sev_badge}",
                unsafe_allow_html=True,
            )
            if f_hint:
                st.info(f"💡 **Diagnostic Reason / Hint:** {f_hint}")
            if f_example:
                st.code(f_example, language="text")
            st.divider()

    # 2. Line-by-Line Error Samples & Stack Traces
    error_samples = report.get("error_samples") or []
    if error_samples:
        st.markdown("#### 🚨 Line-by-Line Error Samples & Stack Traces")
        st.caption("Detailed error statements captured from individual log lines with root-cause traces:")
        for idx, sample in enumerate(error_samples, start=1):
            ts = sample.get("timestamp", "—")
            logger_name = sample.get("logger", "unknown")
            msg = sample.get("message", "No message provided")
            stack_trace = sample.get("stack_trace_head") or sample.get("stack_trace")

            with st.expander(f"Line #{idx} · [{logger_name}] {msg[:85]}…", expanded=(idx == 1)):
                st.markdown(f"**Timestamp:** `{ts}` &nbsp;|&nbsp; **Logger:** `{logger_name}`")
                st.error(f"**Error Statement:** {msg}")
                if stack_trace:
                    st.markdown("**Root Cause / Stack Trace:**")
                    st.code(stack_trace, language="text")

    # 3. Top Errors & Top Warnings Frequency Breakdown
    top_errors = report.get("top_errors") or []
    top_warnings = report.get("top_warnings") or []
    top_sources = report.get("top_sources") or []

    if top_errors or top_warnings or top_sources:
        st.markdown("#### 📊 Error & Warning Breakdown by Frequency")
        tab_err, tab_warn, tab_src = st.tabs(["Top Errors", "Top Warnings", "Top Loggers"])

        with tab_err:
            if top_errors:
                err_df_data = [{"Occurrences": e.get("count", 0), "Error Statement": e.get("message", "")} for e in top_errors]
                st.dataframe(pd.DataFrame(err_df_data), **get_stretch_kwarg(st.dataframe))
            else:
                st.write("No errors recorded.")

        with tab_warn:
            if top_warnings:
                warn_df_data = [{"Occurrences": w.get("count", 0), "Warning Statement": w.get("message", "")} for w in top_warnings]
                st.dataframe(pd.DataFrame(warn_df_data), **get_stretch_kwarg(st.dataframe))
            else:
                st.write("No warnings recorded.")

        with tab_src:
            if top_sources:
                src_df_data = [{"Occurrences": s.get("count", 0), "Logger Source": s.get("logger", "")} for s in top_sources]
                st.dataframe(pd.DataFrame(src_df_data), **get_stretch_kwarg(st.dataframe))
            else:
                st.write("No logger sources recorded.")

    # 4. Ingestion Time Window
    time_range = report.get("time_range") or {}
    if time_range:
        st.caption(f"**Time Window:** First log event at `{time_range.get('first', '—')}` | Last log event at `{time_range.get('last', '—')}`")

    # 5. Full Ingestion Document
    with st.expander("📄 View Complete Raw Ingestion Document (JSON)", expanded=False):
        st.json(record)


# ==============================================================================
# Architecture page
# ==============================================================================
def render_architecture_diagram() -> None:
    nodes = [
        ("📡", "Log Producers", "Microservices"),
        ("🚪", "API Gateway", "FastAPI · HTTP 201"),
        ("🗄️", "Object Store", "S3 / MinIO"),
        ("📬", "Message Broker", "RabbitMQ / SQS"),
        ("⚙️", "Worker Pool", "Parallel consumers"),
        ("📊", "Metrics Store", "Document DB"),
    ]
    parts = []
    for i, (icon, title, tech) in enumerate(nodes):
        if i:
            parts.append('<div class="flow-arrow">→</div>')
        parts.append(
            f'<div class="flow-node"><div class="flow-icon">{icon}</div>'
            f'<div class="flow-title">{title}</div><div class="flow-tech">{tech}</div></div>'
        )
    _html(
        f"""
        <div class="flow">{"".join(parts)}</div>
        <div class="flow-note"><b>Failure path:</b> messages that fail 3 consecutive retries are routed to the
        <b>Dead Letter Queue</b> and the batch metadata is marked <b>status: failed</b> with a root-cause reason.</div>
        """
    )


def render_architecture_stages() -> None:
    stages = [
        ("1 · Ingest", "FastAPI", "Validates format and compression, archives the raw file to object storage and returns a UUID immediately."),
        ("2 · Buffer", "RabbitMQ / SQS", "Absorbs traffic spikes and decouples producers from parsing workers, with manual ACKs for at-least-once delivery."),
        ("3 · Process", "Python workers", "Parse line-level records, classify severity, and compute per-service aggregates and top error signatures."),
        ("4 · Store", "S3 + Document DB", "Pre-aggregated counters power sub-second dashboards while raw lines stay immutably archived."),
        ("5 · Visualize", "Streamlit + Plotly", "Auto-refreshing console for telemetry overview, timelines and per-batch diagnostics."),
    ]
    _html(
        "".join(
            f'<div class="arch-card"><div class="arch-stage-header">'
            f'<span class="arch-stage-title">{title}</span><span class="arch-stage-tech">{tech}</span></div>'
            f'<div class="arch-stage-desc">{desc}</div></div>'
            for title, tech, desc in stages
        )
    )