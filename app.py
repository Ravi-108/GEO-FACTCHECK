"""
Fact-Check Agent - Main Streamlit application.

A web app that automates claim verification from PDF documents.
"""

from html import escape
from textwrap import dedent
from urllib.parse import urlparse
import time

from openai import OpenAI
import pandas as pd
import streamlit as st

from modules.claim_finder import extract_claims
from modules.pdf_extractor import extract_text
from modules.verdict_engine import get_verdict
from modules.web_verifier import search_claim


def html_block(markup: str) -> str:
    return "\n".join(line.strip() for line in dedent(markup).strip().splitlines())


SVG_HERO = html_block("""
<svg class="hero-mark-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <rect x="7" y="6" width="28" height="36" rx="4" fill="none" stroke="currentColor" stroke-width="2.5"/>
    <path d="M15 17h12M15 24h16M15 31h10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="34" cy="33" r="7" fill="#ffffff" stroke="currentColor" stroke-width="2.5"/>
    <path d="M39 38l5 5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
</svg>
""")

SVG_DOCUMENT = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M13 6h16l8 8v28H13z" fill="#fff8f5" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M29 6v9h8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M19 23h12M19 29h12M19 35h8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
</svg>
""")

SVG_CLAIMS = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <circle cx="21" cy="21" r="10" fill="#f7fbfa" stroke="currentColor" stroke-width="2.6"/>
    <path d="M29 29l9 9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    <path d="M16 21h10M21 16v10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
</svg>
""")

SVG_SEARCH = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <circle cx="24" cy="24" r="16" fill="#f7fbfa" stroke="currentColor" stroke-width="2.5"/>
    <path d="M8 24h32M24 8c4 4.4 6 9.7 6 16s-2 11.6-6 16M24 8c-4 4.4-6 9.7-6 16s2 11.6 6 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
</svg>
""")

SVG_VERDICT = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M24 7v7M14 14h20M17 14l-7 15h14zM31 14l-7 15h14z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M18 39h12M24 29v10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M18 30c1.5 2 3.5 3 6 3s4.5-1 6-3" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
</svg>
""")

SVG_CHECK = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M4.5 10.2l3.3 3.3 7.7-8.2" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""")

SVG_ALERT = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M10 3l7 13H3z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
    <path d="M10 7.3v4.4M10 14.6h.01" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/>
</svg>
""")

SVG_X = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M5.5 5.5l9 9M14.5 5.5l-9 9" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
</svg>
""")

SVG_HELP = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="1.9"/>
    <path d="M7.8 7.8a2.4 2.4 0 0 1 4.6 1c0 1.9-2.4 2-2.4 3.7M10 15h.01" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
</svg>
""")

SVG_LINK = html_block("""
<svg class="inline-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M8.2 11.8a3.2 3.2 0 0 1 0-4.5l1.7-1.7a3.2 3.2 0 0 1 4.5 4.5l-.9.9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M11.8 8.2a3.2 3.2 0 0 1 0 4.5l-1.7 1.7a3.2 3.2 0 0 1-4.5-4.5l.9-.9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>
""")

SVG_PIN = html_block("""
<svg class="inline-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M10 2.8l4.4 4.4-2.2 2.2 2.4 4.8-.8.8L9 12.6 6 15.6 4.4 14l3-3-2.4-4.8.8-.8 4.2 2z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
</svg>
""")


PROCESS_STEPS = [
    ("01", SVG_DOCUMENT, "Upload PDF", "The document is parsed into clean text for analysis."),
    ("02", SVG_CLAIMS, "Extract Claims", "AI isolates verifiable facts, statistics, dates, and figures."),
    ("03", SVG_SEARCH, "Search Evidence", "Each claim is checked against current web evidence."),
    ("04", SVG_VERDICT, "Generate Verdict", "The claim is scored with confidence, reasoning, and sources."),
]


def source_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    return host or url[:48]


def verdict_icon(verdict: str) -> str:
    return {
        "VERIFIED": SVG_CHECK,
        "INACCURATE": SVG_ALERT,
        "FALSE": SVG_X,
        "ERROR": SVG_HELP,
    }.get(verdict, SVG_HELP)


def verdict_classes(verdict: str) -> tuple[str, str]:
    return {
        "VERIFIED": ("verdict-verified", "badge-verified"),
        "INACCURATE": ("verdict-inaccurate", "badge-inaccurate"),
        "FALSE": ("verdict-false", "badge-false"),
        "ERROR": ("verdict-error", "badge-error"),
    }.get(verdict, ("verdict-error", "badge-error"))


def render_process_visual() -> str:
    cards = []
    for number, icon, title, body in PROCESS_STEPS:
        cards.append(
            html_block(f"""
            <div class="process-card">
                <div class="process-topline">
                    <span class="process-number">{number}</span>
                    {icon}
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
            </div>
            """)
        )

    return html_block(f"""
    <div class="workflow-section" role="region" aria-label="Verification workflow">
        <div class="section-kicker">Verification workflow</div>
        <h2 class="workflow-title">From document to evidence-backed verdict</h2>
        <div class="process-grid">
            {''.join(cards)}
        </div>
    </div>
    """)


def render_sources(sources) -> str:
    if not sources:
        return ""

    if isinstance(sources, str):
        source_list = [sources]
    else:
        source_list = list(sources)

    links = []
    for source in source_list[:2]:
        if not source:
            continue
        source_url = escape(str(source), quote=True)
        label = escape(source_label(str(source)))
        links.append(f'<a class="source-link" href="{source_url}" target="_blank" rel="noopener noreferrer">{label}</a>')

    if not links:
        return ""

    return html_block(f"""
    <div class="sources-row">
        {SVG_LINK}
        <span>Sources</span>
        {' '.join(links)}
    </div>
    """)


def render_correction(correct_fact) -> str:
    if not correct_fact or correct_fact == "null":
        return ""

    return html_block(f"""
    <div class="correction-text">
        {SVG_PIN}
        <span>Correct fact: {escape(str(correct_fact))}</span>
    </div>
    """)



STAGE_LABELS = ["Upload", "Extracting", "Finding claims", "Checking evidence", "Report ready"]


def init_session_state() -> None:
    defaults = {
        "upload_key": 0,
        "stage": "Upload",
        "results": [],
        "word_count": 0,
        "claim_count": 0,
        "active_file_name": None,
        "active_file_size": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_upload_state() -> None:
    st.session_state.upload_key += 1
    st.session_state.stage = "Upload"
    st.session_state.results = []
    st.session_state.word_count = 0
    st.session_state.claim_count = 0
    st.session_state.active_file_name = None
    st.session_state.active_file_size = 0


def set_stage(stage: str, placeholder=None) -> None:
    st.session_state.stage = stage
    if placeholder is not None:
        placeholder.markdown(render_stage_bar(stage), unsafe_allow_html=True)


def render_stage_bar(current_stage: str) -> str:
    try:
        current_index = STAGE_LABELS.index(current_stage)
    except ValueError:
        current_index = 0

    items = []
    for index, label in enumerate(STAGE_LABELS):
        if index < current_index:
            state_class = "is-done"
        elif index == current_index:
            state_class = "is-current"
        else:
            state_class = "is-next"

        items.append(
            html_block(f"""
            <div class="stage-item {state_class}">
                <span class="stage-dot">{index + 1}</span>
                <span>{label}</span>
            </div>
            """)
        )

    return html_block(f"""
    <div class="stage-shell">
        <div class="stage-label">Current stage</div>
        <div class="stage-row">{''.join(items)}</div>
    </div>
    """)


def render_stats(results: list[dict]) -> str:
    verified_count = sum(1 for result in results if result.get("verdict") == "VERIFIED")
    inaccurate_count = sum(1 for result in results if result.get("verdict") == "INACCURATE")
    false_count = sum(1 for result in results if result.get("verdict") == "FALSE")
    error_count = sum(1 for result in results if result.get("verdict") == "ERROR")

    return html_block(f"""
    <div class="stats-container">
        <div class="stat-card stat-total">
            <div class="stat-number">{len(results)}</div>
            <div class="stat-label">Claims</div>
        </div>
        <div class="stat-card stat-verified">
            <div class="stat-number">{verified_count}</div>
            <div class="stat-label">Verified</div>
        </div>
        <div class="stat-card stat-inaccurate">
            <div class="stat-number">{inaccurate_count}</div>
            <div class="stat-label">Inaccurate</div>
        </div>
        <div class="stat-card stat-false">
            <div class="stat-number">{false_count}</div>
            <div class="stat-label">False</div>
        </div>
        <div class="stat-card stat-error">
            <div class="stat-number">{error_count}</div>
            <div class="stat-label">Errors</div>
        </div>
    </div>
    """)


st.set_page_config(
    page_title="Fact-Check Agent | AI-Powered Claim Verification",
    page_icon="FC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()

st.markdown(
    html_block("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary: #c15f3c;
        --primary-dark: #98452f;
        --primary-soft: #fff0ea;
        --ink: #17202a;
        --muted: #667085;
        --line: #e5e7eb;
        --surface: #ffffff;
        --surface-alt: #f7faf9;
        --teal: #173b3f;
        --green: #157347;
        --amber: #a66b00;
        --red: #b42318;
        --slate: #475467;
        --shadow: 0 16px 40px rgba(23, 32, 42, 0.08);
    }

    .stApp {
        background: linear-gradient(180deg, #fbfaf8 0%, #f6f9f8 48%, #ffffff 100%);
        color: var(--ink);
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    #MainMenu,
    header,
    footer,
    .stDeployButton,
    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }

    .hero-container {
        text-align: center;
        padding: 1.75rem 1rem 0.5rem;
        margin-bottom: 0.75rem;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid rgba(193, 95, 60, 0.28);
        border-radius: 999px;
        padding: 7px 14px;
        color: var(--primary-dark);
        background: rgba(255, 240, 234, 0.82);
        font-size: 0.83rem;
        font-weight: 700;
        letter-spacing: 0;
        margin-bottom: 18px;
    }

    .hero-mark-icon {
        width: 20px;
        height: 20px;
    }

    .hero-title {
        margin: 0;
        color: var(--ink);
        font-size: 3rem;

        line-height: 1.08;
        font-weight: 800;
        letter-spacing: 0;
    }

    .hero-title span {
        color: var(--primary);
    }

    .hero-subtitle {
        max-width: 720px;
        margin: 16px auto 0;
        color: var(--muted);
        font-size: 1.04rem;
        line-height: 1.65;
        font-weight: 400;
    }

    .workflow-section {
        margin: 1.5rem 0 1.75rem;
        padding: 1.4rem 0 0.6rem;
        border-top: 1px solid rgba(23, 59, 63, 0.12);
    }

    .section-kicker {
        color: var(--primary-dark);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
        text-align: center;
    }

    .workflow-title {
        margin: 8px 0 22px;
        color: var(--teal);
        text-align: center;
        font-size: 1.35rem;
        line-height: 1.3;
        font-weight: 750;
        letter-spacing: 0;
    }

    .process-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 16px;
    }

    .process-card {
        position: relative;
        min-height: 190px;
        padding: 18px;
        border: 1px solid rgba(23, 59, 63, 0.12);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: 0 10px 28px rgba(23, 32, 42, 0.06);
        transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
    }

    .process-card:hover {
        transform: translateY(-3px);
        border-color: rgba(193, 95, 60, 0.42);
        box-shadow: var(--shadow);
    }

    .process-card:not(:last-child)::after {
        content: "";
        position: absolute;
        top: 48px;
        right: -16px;
        width: 16px;
        height: 2px;
        background: linear-gradient(90deg, rgba(193, 95, 60, 0.4), rgba(23, 59, 63, 0.18));
    }

    .process-topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 48px;
    }

    .process-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 30px;
        border-radius: 8px;
        color: var(--primary-dark);
        background: var(--primary-soft);
        font-size: 0.82rem;
        font-weight: 800;
        letter-spacing: 0;
    }

    .process-icon {
        width: 48px;
        height: 48px;
        color: var(--primary);
        flex: 0 0 auto;
    }

    .process-card h3 {
        margin: 18px 0 8px;
        color: var(--ink);
        font-size: 1rem;
        line-height: 1.25;
        font-weight: 750;
        letter-spacing: 0;
    }

    .process-card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.55;
    }

    div[data-testid="stFileUploader"] {
        margin: 1.15rem auto 1rem;
        max-width: 560px;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        position: relative;
        min-height: 210px;
        border: 1.5px dashed rgba(193, 95, 60, 0.42);
        border-radius: 8px;
        background: linear-gradient(180deg, rgba(255, 240, 234, 0.72), rgba(247, 250, 249, 0.92));
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 28px;
        transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        cursor: pointer;
        overflow: hidden;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover {
        transform: translateY(-2px);
        border-color: var(--primary);
        box-shadow: var(--shadow);
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::before {
        content: "";
        width: 80px;
        height: 80px;
        margin-bottom: 12px;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 96 96' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='18' y='14' width='46' height='62' rx='7' fill='%23fff8f5' stroke='%23c15f3c' stroke-width='4'/%3E%3Cpath d='M64 14l14 14v48a6 6 0 0 1-6 6H28' fill='none' stroke='%23c15f3c' stroke-width='4' stroke-linejoin='round'/%3E%3Cpath d='M64 14v16h14' fill='none' stroke='%23c15f3c' stroke-width='4' stroke-linejoin='round'/%3E%3Cpath d='M41 58V36M31 46l10-10 10 10' fill='none' stroke='%23c15f3c' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
        background-position: center;
        background-repeat: no-repeat;
        background-size: contain;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
        content: "Upload a PDF to start verification\\A The workflow extracts claims, searches evidence, and builds a report.";
        color: var(--ink);
        font-size: 0.9rem;
        font-weight: 700;
        line-height: 1.55;
        white-space: pre-line;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"],
    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button,
    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] small {
        opacity: 0;
        width: 0;
        height: 0;
        padding: 0;
        margin: 0;
        overflow: hidden;
        pointer-events: none;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] input[type="file"] {
        display: block !important;
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
        z-index: 4;
    }

    .uploaded-file {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin: 0 0 16px;
        padding: 12px 14px;
        border: 1px solid rgba(21, 115, 71, 0.18);
        border-radius: 8px;
        background: rgba(240, 253, 244, 0.84);
        color: var(--green);
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.4;
    }

    .uploaded-filename {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1 1 auto;
        min-width: 0;
    }

    .uploaded-size {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 600;
        flex: 0 0 auto;
        white-space: nowrap;
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 46px;
        border: 0;
        border-radius: 8px;
        background: var(--primary);
        color: #ffffff;
        font-weight: 800;
        letter-spacing: 0;
        box-shadow: 0 14px 26px rgba(193, 95, 60, 0.24);
        transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        background: var(--primary-dark);
        color: #ffffff;
        box-shadow: 0 18px 34px rgba(193, 95, 60, 0.3);
    }

    .stButton > button:focus,
    .stDownloadButton > button:focus {
        color: #ffffff;
        box-shadow: 0 0 0 4px rgba(193, 95, 60, 0.22);
    }

    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(23, 59, 63, 0.16), transparent);
        margin: 1.75rem 0;
    }

    .stats-container {
        display: grid;
        grid-template-columns: repeat(5, minmax(120px, 1fr));
        gap: 14px;
        margin: 1.5rem 0 1.2rem;
    }

    .stat-card {
        min-height: 108px;
        padding: 16px;
        border: 1px solid rgba(23, 59, 63, 0.1);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: 0 8px 24px rgba(23, 32, 42, 0.05);
    }

    .stat-number {
        font-size: 2rem;
        line-height: 1;
        font-weight: 800;
        letter-spacing: 0;
        color: var(--ink);
    }

    .stat-label {
        margin-top: 8px;
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .stat-total .stat-number { color: var(--primary); }
    .stat-verified .stat-number { color: var(--green); }
    .stat-inaccurate .stat-number { color: var(--amber); }
    .stat-false .stat-number { color: var(--red); }
    .stat-error .stat-number { color: var(--slate); }

    .section-heading {
        margin: 0 0 0.25rem;
        color: var(--ink);
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: 0;
    }

    .verdict-card {
        border: 1px solid var(--line);
        border-left: 5px solid;
        border-radius: 8px;
        background: var(--surface);
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 8px 24px rgba(23, 32, 42, 0.05);
        transition: transform 160ms ease, box-shadow 160ms ease;
    }

    .verdict-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow);
    }

    .verdict-verified { border-left-color: var(--green); background: linear-gradient(90deg, rgba(240, 253, 244, 0.88), #ffffff 44%); }
    .verdict-inaccurate { border-left-color: var(--amber); background: linear-gradient(90deg, rgba(255, 251, 235, 0.9), #ffffff 44%); }
    .verdict-false { border-left-color: var(--red); background: linear-gradient(90deg, rgba(254, 243, 242, 0.9), #ffffff 44%); }
    .verdict-error { border-left-color: var(--slate); background: linear-gradient(90deg, rgba(248, 250, 252, 0.96), #ffffff 44%); }

    .verdict-header {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }

    .verdict-badge,
    .confidence-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 28px;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .badge-icon {
        width: 16px;
        height: 16px;
    }

    .badge-verified { color: var(--green); background: rgba(21, 115, 71, 0.11); }
    .badge-inaccurate { color: var(--amber); background: rgba(166, 107, 0, 0.12); }
    .badge-false { color: var(--red); background: rgba(180, 35, 24, 0.1); }
    .badge-error { color: var(--slate); background: rgba(71, 84, 103, 0.1); }

    .confidence-badge {
        color: var(--teal);
        background: rgba(23, 59, 63, 0.08);
    }

    .claim-meta {
        margin-left: auto;
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 650;
    }

    .claim-text {
        margin: 13px 0 8px;
        color: var(--ink);
        font-size: 0.98rem;
        font-weight: 700;
        line-height: 1.55;
    }

    .explanation-text {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.65;
    }

    .correction-text,
    .sources-row {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-top: 10px;
        color: var(--primary-dark);
        font-size: 0.86rem;
        font-weight: 650;
        line-height: 1.5;
    }

    .correction-text {
        padding: 10px 12px;
        border: 1px solid rgba(193, 95, 60, 0.18);
        border-radius: 8px;
        background: rgba(255, 240, 234, 0.62);
    }

    .inline-icon {
        width: 18px;
        height: 18px;
        flex: 0 0 auto;
        margin-top: 1px;
    }

    .sources-row {
        color: var(--muted);
        align-items: center;
        flex-wrap: wrap;
    }

    .source-link {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        color: var(--primary-dark);
        text-decoration: none;
        border-bottom: 1px solid rgba(193, 95, 60, 0.28);
        word-break: break-word;
    }

    .source-link:hover {
        color: var(--primary);
        border-bottom-color: var(--primary);
    }

    div[data-baseweb="select"] > div {
        border-color: rgba(23, 59, 63, 0.16);
        border-radius: 8px;
    }

    div[data-testid="stProgressBar"] > div > div > div {
        background-color: var(--primary);
    }

    .footer-note {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #98a2b3;
        font-size: 0.8rem;
        line-height: 1.6;
    }

    @media (max-width: 920px) {
        .process-grid,
        .stats-container {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .process-card:not(:last-child)::after {
            display: none;
        }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 1.1rem;
        }

        .hero-container {
            padding-left: 0;
            padding-right: 0;
        }

        .hero-title {
            font-size: 2.25rem;
        }

        .hero-subtitle {
            font-size: 0.96rem;
        }

        .process-grid,
        .stats-container {
            grid-template-columns: 1fr;
        }

        .process-card {
            min-height: auto;
        }

        .claim-meta {
            width: 100%;
            margin-left: 0;
        }
    }

    .block-container {
        max-width: 1320px;
        padding-top: 4.5rem;
        padding-bottom: 1rem;
    }

    .app-kicker,
    .stage-label,
    .panel-label {
        color: var(--primary-dark);
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .control-title {
        margin: 0.3rem 0 0;
        color: var(--ink);
        font-size: 2.25rem;
        line-height: 1.02;
        font-weight: 850;
        letter-spacing: 0;
    }

    .control-title span {
        color: var(--primary);
    }

    .control-copy {
        margin: 0.75rem 0 1.15rem;
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.55;
    }

    .control-panel,
    .result-panel,
    .empty-panel {
        border: 1px solid rgba(23, 59, 63, 0.11);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: 0 14px 32px rgba(23, 32, 42, 0.06);
    }

    .control-panel {
        padding: 1.2rem;
        margin-bottom: 1rem;
    }

    .result-panel,
    .empty-panel {
        padding: 1rem;
        margin-top: 0.85rem;
    }

    .empty-panel {
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        color: var(--muted);
    }

    .empty-title {
        margin: 0 0 0.35rem;
        color: var(--ink);
        font-size: 1.15rem;
        font-weight: 800;
    }

    .empty-copy {
        margin: 0;
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .file-row {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
    }

    .file-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: rgba(21, 115, 71, 0.11);
        flex: 0 0 auto;
    }

    .meta-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-top: 1rem;
    }

    .mini-stat {
        padding: 0.75rem;
        border: 1px solid rgba(23, 59, 63, 0.1);
        border-radius: 8px;
        background: rgba(247, 250, 249, 0.72);
    }

    .mini-stat strong {
        display: block;
        color: var(--ink);
        font-size: 1.1rem;
        line-height: 1;
    }

    .mini-stat span {
        display: block;
        margin-top: 5px;
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 750;
        text-transform: uppercase;
    }

    .stage-shell {
        position: sticky;
        top: 0.75rem;
        z-index: 6;
        padding: 0.9rem 1rem;
        border: 1px solid rgba(23, 59, 63, 0.12);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(12px);
        box-shadow: 0 14px 30px rgba(23, 32, 42, 0.07);
    }

    .stage-row {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px;
        margin-top: 0.75rem;
    }

    .stage-item {
        display: flex;
        align-items: center;
        gap: 7px;
        min-width: 0;
        padding: 8px;
        border: 1px solid rgba(23, 59, 63, 0.1);
        border-radius: 8px;
        color: var(--muted);
        background: var(--surface-alt);
        font-size: 0.78rem;
        font-weight: 800;
        line-height: 1.15;
    }

    .stage-dot {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 999px;
        background: #ffffff;
        color: inherit;
        font-size: 0.72rem;
        flex: 0 0 auto;
    }

    .stage-item.is-current {
        color: #ffffff;
        border-color: var(--primary);
        background: linear-gradient(135deg, var(--primary), var(--teal));
    }

    .stage-item.is-done {
        color: var(--green);
        border-color: rgba(21, 115, 71, 0.16);
        background: rgba(240, 253, 244, 0.9);
    }

    .run-status {
        margin-top: 0.8rem;
        padding: 0.8rem 0.95rem;
        border: 1px solid rgba(23, 59, 63, 0.1);
        border-radius: 8px;
        background: rgba(247, 250, 249, 0.78);
        color: var(--teal);
        font-size: 0.9rem;
        font-weight: 750;
    }

    div[data-testid="stHorizontalBlock"]:has(.control-title) > div:first-child > div {
        position: sticky;
        top: 1.25rem;
        align-self: flex-start;
    }

    div[data-testid="stHorizontalBlock"]:has(.control-title) > div:nth-child(2) > div {
        max-height: calc(100vh - 2.5rem);
        overflow-y: auto;
        padding-right: 0.25rem;
    }

    div[data-testid="stFileUploader"] {
        margin: 0.9rem 0 0.85rem;
        max-width: none;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        min-height: 150px;
        padding: 20px;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::before {
        width: 56px;
        height: 56px;
        margin-bottom: 8px;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
        content: "Drop PDF here";
        font-size: 0.92rem;
    }

    .uploaded-file {
        margin-bottom: 0;
        background: rgba(240, 253, 244, 0.9);
        height: 54px;
    }

    /* Style the remove button column */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        min-height: 54px;
        padding: 0;
        font-size: 1.6rem;
        line-height: 1;
        background: #ffffff;
        color: var(--slate);
        border: 1px solid rgba(23, 59, 63, 0.18);
        border-radius: 8px;
    }

    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
        background: rgba(254, 243, 242, 0.95);
        color: var(--red);
        border-color: rgba(180, 35, 24, 0.3);
    }

    .stButton > button[kind="secondary"] {
        min-height: 44px;
        background: #ffffff;
        color: var(--red);
        border: 1px solid rgba(180, 35, 24, 0.18);
        box-shadow: none;
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(254, 243, 242, 0.95);
        color: var(--red);
        box-shadow: none;
    }

    .action-row {
        margin-top: 1.25rem;
    }

    .stats-container {
        grid-template-columns: repeat(5, minmax(86px, 1fr));
        gap: 10px;
        margin: 0.5rem 0 1rem;
    }

    .stat-card {
        min-height: 82px;
        padding: 12px;
    }

    .stat-number {
        font-size: 1.55rem;
    }

    .section-heading {
        font-size: 1.1rem;
        margin-bottom: 0.6rem;
    }

    .verdict-card {
        padding: 14px;
        margin-bottom: 10px;
    }

    .claim-text {
        font-size: 0.93rem;
        line-height: 1.45;
    }

    .explanation-text {
        font-size: 0.86rem;
        line-height: 1.5;
    }

    .footer-note {
        display: none;
    }

    @media (max-width: 920px) {
        div[data-testid="stHorizontalBlock"]:has(.control-title) > div:first-child > div,
        .stage-shell {
            position: static;
        }

        div[data-testid="stHorizontalBlock"]:has(.control-title) > div:nth-child(2) > div {
            max-height: none;
            overflow: visible;
            padding-right: 0;
        }

        .stage-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 640px) {
        .control-title {
            font-size: 1.9rem;
        }

        .stage-row,
        .stats-container,
        .meta-grid {
            grid-template-columns: 1fr;
        }
    }</style>
"""),
    unsafe_allow_html=True,
)

st.markdown(
    html_block(f"""
    <div class="control-panel">
        <div class="app-kicker">{SVG_HERO} AI verification</div>
        <h1 class="control-title">Fact-Check <span>Agent</span></h1>
        <p class="control-copy">Upload one PDF, run verification, and review evidence-backed verdicts without leaving the workspace.</p>
    </div>
    """),
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([0.35, 0.65], gap="large")

with left_col:
    st.markdown('<div class="panel-label">Document</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload PDF",
        type="pdf",
        help="Upload a PDF document containing claims you want to verify.",
        label_visibility="collapsed",
        key=f"pdf_upload_{st.session_state.upload_key}",
    )

    if uploaded:
        is_new_file = (
            st.session_state.active_file_name != uploaded.name
            or st.session_state.active_file_size != uploaded.size
        )
        if is_new_file:
            st.session_state.active_file_name = uploaded.name
            st.session_state.active_file_size = uploaded.size
            st.session_state.stage = "Upload"
            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0

        uploaded_name = escape(uploaded.name)
        uploaded_size = round(uploaded.size / 1024, 1)
        file_info_col, remove_col = st.columns([0.82, 0.18], gap="small")

        with file_info_col:
            st.markdown(
                html_block(f"""
                <div class="uploaded-file">
                    <div class="file-row">
                        <span class="file-icon">{SVG_CHECK}</span>
                        <span class="uploaded-filename">{uploaded_name}</span>
                    </div>
                    <span class="uploaded-size">{uploaded_size} KB</span>
                </div>
                """),
                unsafe_allow_html=True,
            )

        with remove_col:
            remove_pdf = st.button("×", key="remove_pdf", help="Remove PDF", use_container_width=True)

        if remove_pdf:
            reset_upload_state()
            st.rerun()

        st.markdown('<div class="action-row"></div>', unsafe_allow_html=True)
        run_check = st.button("Run fact-check", type="primary", use_container_width=True)
    else:
        if st.session_state.active_file_name is not None:
            st.session_state.stage = "Upload"
            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0
            st.session_state.active_file_name = None
            st.session_state.active_file_size = 0
        run_check = False

    st.markdown(
        html_block(f"""
        <div class="meta-grid">
            <div class="mini-stat">
                <strong>{st.session_state.word_count:,}</strong>
                <span>Words</span>
            </div>
            <div class="mini-stat">
                <strong>{st.session_state.claim_count}</strong>
                <span>Claims</span>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

with right_col:
    stage_placeholder = st.empty()
    set_stage(st.session_state.stage, stage_placeholder)
    status_placeholder = st.empty()

    if uploaded and run_check:
        try:
            OPENROUTER_KEY = st.secrets["OPENROUTER_API_KEY"]
            TAVILY_KEY = st.secrets["TAVILY_API_KEY"]
        except Exception:
            st.session_state.results = []
            status_placeholder.error("API keys missing. Add OpenRouter and Tavily keys in Streamlit secrets.")
        else:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_KEY,
                timeout=15.0,
            )

            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0

            set_stage("Extracting", stage_placeholder)
            status_placeholder.markdown(
                '<div class="run-status">Extracting text from the PDF...</div>',
                unsafe_allow_html=True,
            )
            text = extract_text(uploaded)

            if not text.strip():
                set_stage("Upload", stage_placeholder)
                status_placeholder.error("Could not read text from this PDF. It may be scanned or image-based.")
            else:
                st.session_state.word_count = len(text.split())

                set_stage("Finding claims", stage_placeholder)
                status_placeholder.markdown(
                    '<div class="run-status">Finding verifiable claims...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    claims = extract_claims(text, OPENROUTER_KEY)
                except Exception as exc:
                    status_placeholder.error(f"Claim extraction failed: {str(exc)}")
                else:
                    st.session_state.claim_count = len(claims)

                    if not claims:
                        set_stage("Upload", stage_placeholder)
                        status_placeholder.warning("No verifiable claims found in this PDF.")
                    else:
                        max_claims_to_check = min(len(claims), 10)
                        results = []

                        set_stage("Checking evidence", stage_placeholder)
                        progress_bar = st.progress(0)
                        progress_text = st.empty()

                        for index, claim in enumerate(claims[:max_claims_to_check]):
                            claim_text = claim.get("claim", str(claim))
                            progress_text.markdown(
                                f'<div class="run-status">Checking claim {index + 1} of {max_claims_to_check}</div>',
                                unsafe_allow_html=True,
                            )

                            evidence = search_claim(claim_text, TAVILY_KEY)
                            verdict = get_verdict(claim_text, evidence, client)

                            results.append(
                                {
                                    "claim": claim_text,
                                    "type": claim.get("type", "unknown"),
                                    **verdict,
                                }
                            )

                            progress_bar.progress((index + 1) / max_claims_to_check)
                            time.sleep(0.2)

                        progress_text.empty()
                        progress_bar.empty()
                        st.session_state.results = results
                        set_stage("Report ready", stage_placeholder)
                        status_placeholder.markdown(
                            '<div class="run-status">Report ready.</div>',
                            unsafe_allow_html=True,
                        )

    results = st.session_state.results

    if results:
        st.markdown('<div class="result-panel"><div class="panel-label">Results</div>', unsafe_allow_html=True)
        st.markdown(render_stats(results), unsafe_allow_html=True)

        filter_col, download_col = st.columns([0.58, 0.42], gap="small")
        with filter_col:
            verdict_filter = st.selectbox(
                "Filter by verdict",
                ["All", "VERIFIED", "INACCURATE", "FALSE", "ERROR"],
                label_visibility="collapsed",
            )

        df = pd.DataFrame(results)
        display_cols = ["claim", "type", "verdict", "confidence", "explanation", "correct_fact"]
        available_cols = [column for column in display_cols if column in df.columns]
        df_export = df[available_cols]

        with download_col:
            st.download_button(
                "Download CSV",
                df_export.to_csv(index=False),
                file_name="factcheck_report.csv",
                mime="text/csv",
                use_container_width=True,
            )

        filtered_results = (
            results
            if verdict_filter == "All"
            else [result for result in results if result.get("verdict") == verdict_filter]
        )

        for index, result in enumerate(filtered_results):
            verdict = result.get("verdict", "ERROR").upper()
            confidence = escape(str(result.get("confidence", "LOW")))
            card_class, badge_class = verdict_classes(verdict)
            claim_type = escape(str(result.get("type", "unknown")))
            claim_text = escape(str(result.get("claim", "N/A")))
            explanation = escape(str(result.get("explanation", "No explanation available.")))
            correction_html = render_correction(result.get("correct_fact"))
            sources_html = render_sources(result.get("sources"))

            st.markdown(
                html_block(f"""
                <div class="verdict-card {card_class}">
                    <div class="verdict-header">
                        <span class="verdict-badge {badge_class}">{verdict_icon(verdict)} {escape(verdict)}</span>
                        <span class="confidence-badge">{confidence}</span>
                        <span class="claim-meta">#{index + 1} - {claim_type}</span>
                    </div>
                    <div class="claim-text">{claim_text}</div>
                    <div class="explanation-text">{explanation}</div>
                    {correction_html}
                    {sources_html}
                </div>
                """),
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
    elif uploaded:
        st.markdown(
            html_block("""
            <div class="empty-panel">
                <div class="empty-title">Ready to check</div>
                <p class="empty-copy">Run the fact-check to extract claims and generate verdicts here.</p>
            </div>
            """),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            html_block("""
            <div class="empty-panel">
                <div class="empty-title">Upload a PDF to begin</div>
                <p class="empty-copy">Results, progress, and the final CSV report will appear on this side.</p>
            </div>
            """),
            unsafe_allow_html=True,
        )
