"""
Fact-Check Agent — Main Streamlit Application
A web app that automates claim verification from PDF documents.
"""

import streamlit as st
from openai import OpenAI
import pandas as pd
import time

from modules.pdf_extractor import extract_text
from modules.claim_finder import extract_claims
from modules.web_verifier import search_claim
from modules.verdict_engine import get_verdict

# ─── Page Configuration ───
st.set_page_config(
    page_title="Fact-Check Agent | AI-Powered Claim Verification",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS for Premium Look ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hero header */
    .hero-container {
        text-align: center;
        padding: 2rem 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 500;
        color: #667eea;
        margin-bottom: 16px;
    }
    
    .hero-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 12px;
        line-height: 1.2;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: #6b7280;
        font-weight: 400;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Pipeline steps */
    .pipeline-container {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 1.5rem auto;
        flex-wrap: wrap;
        max-width: 700px;
    }
    
    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 500;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        color: #495057;
        transition: all 0.2s;
    }
    
    .pipeline-step.active {
        background: linear-gradient(135deg, #667eea11, #764ba211);
        border-color: #667eea44;
        color: #667eea;
    }
    
    .pipeline-arrow {
        color: #dee2e6;
        font-size: 16px;
        display: flex;
        align-items: center;
    }
    
    /* Result cards */
    .verdict-card {
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        border-left: 4px solid;
        transition: all 0.2s ease;
    }
    
    .verdict-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .verdict-verified {
        background: linear-gradient(135deg, #d4edda, #f0fff4);
        border-left-color: #28a745;
    }
    
    .verdict-inaccurate {
        background: linear-gradient(135deg, #fff3cd, #fffbea);
        border-left-color: #ffc107;
    }
    
    .verdict-false {
        background: linear-gradient(135deg, #f8d7da, #fff5f5);
        border-left-color: #dc3545;
    }
    
    .verdict-error {
        background: linear-gradient(135deg, #e2e3e5, #f8f9fa);
        border-left-color: #6c757d;
    }
    
    .verdict-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-verified { background: #28a74522; color: #28a745; }
    .badge-inaccurate { background: #ffc10722; color: #d4a017; }
    .badge-false { background: #dc354522; color: #dc3545; }
    .badge-error { background: #6c757d22; color: #6c757d; }
    
    .confidence-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        background: #f0f0f0;
        color: #555;
    }
    
    .claim-text {
        font-size: 15px;
        font-weight: 500;
        color: #1a1a2e;
        margin: 10px 0 6px;
        line-height: 1.5;
    }
    
    .explanation-text {
        font-size: 13px;
        color: #555;
        line-height: 1.6;
        margin: 4px 0;
    }
    
    .correction-text {
        font-size: 13px;
        color: #c0392b;
        font-weight: 500;
        margin-top: 6px;
        padding: 8px 12px;
        background: #fff5f5;
        border-radius: 6px;
        border: 1px solid #dc354522;
    }
    
    .source-link {
        font-size: 11px;
        color: #667eea;
        text-decoration: none;
        word-break: break-all;
    }
    
    /* Stats bar */
    .stats-container {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin: 1.5rem 0;
        flex-wrap: wrap;
    }
    
    .stat-card {
        text-align: center;
        padding: 16px 24px;
        border-radius: 12px;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        min-width: 120px;
    }
    
    .stat-number {
        font-size: 28px;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 4px;
    }
    
    .stat-label {
        font-size: 11px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    /* Upload area */
    .upload-zone {
        border: 2px dashed #667eea44;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, #667eea08, #764ba208);
        margin: 1rem auto;
        max-width: 500px;
        transition: all 0.3s;
    }
    
    .upload-zone:hover {
        border-color: #667eea88;
        background: linear-gradient(135deg, #667eea12, #764ba212);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    div[data-testid="stFileUploader"] > div:first-child {
        padding: 0;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 32px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.35);
    }
    
    /* Divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #e9ecef, transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Hero Section ───
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">⚡ AI-Powered Verification Engine</div>
    <h1 class="hero-title">Fact-Check Agent</h1>
    <p class="hero-subtitle">
        Upload any PDF document and let AI cross-reference every claim 
        against live web data. Catch outdated stats, hallucinated figures, 
        and false claims instantly.
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Pipeline Visualization ───
st.markdown("""
<div class="pipeline-container">
    <div class="pipeline-step">📄 Upload PDF</div>
    <div class="pipeline-arrow">→</div>
    <div class="pipeline-step">🔎 Extract Claims</div>
    <div class="pipeline-arrow">→</div>
    <div class="pipeline-step">🌐 Web Search</div>
    <div class="pipeline-arrow">→</div>
    <div class="pipeline-step">⚖️ AI Verdict</div>
</div>
<div class="custom-divider"></div>
""", unsafe_allow_html=True)


# ─── File Upload Section ───
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    uploaded = st.file_uploader(
        "Drop your PDF here",
        type="pdf",
        help="Upload a PDF document containing claims you want to verify.",
        label_visibility="collapsed"
    )
    
    if uploaded:
        st.markdown(f"""
        <div style="text-align:center; padding: 8px; background: #f0fff4; border-radius: 8px; border: 1px solid #28a74522; margin-bottom: 16px;">
            <span style="color: #28a745; font-weight: 500;">✓ {uploaded.name}</span>
            <span style="color: #6b7280; font-size: 12px; margin-left: 8px;">({round(uploaded.size / 1024, 1)} KB)</span>
        </div>
        """, unsafe_allow_html=True)
        
        run_check = st.button("🔍  Run Fact-Check", use_container_width=True)
    else:
        st.markdown("""
        <div class="upload-zone">
            <div style="font-size: 40px; margin-bottom: 8px;">📄</div>
            <div style="color: #667eea; font-weight: 500; margin-bottom: 4px;">Upload a PDF to get started</div>
            <div style="color: #9ca3af; font-size: 12px;">Supports any PDF with text content</div>
        </div>
        """, unsafe_allow_html=True)
        run_check = False

# ─── Main Processing Logic ───
if uploaded and run_check:
    # Load API keys from secrets
    try:
        OPENROUTER_KEY = st.secrets["OPENROUTER_API_KEY"]
        TAVILY_KEY = st.secrets["TAVILY_API_KEY"]
    except Exception:
        st.error("⚠️ API keys not found. Please configure them in `.streamlit/secrets.toml` or Streamlit Cloud secrets.")
        st.code('# .streamlit/secrets.toml\nOPENROUTER_API_KEY = "sk-or-..."\nTAVILY_API_KEY = "tvly-..."', language="toml")
        st.stop()
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_KEY,
    )
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Step 1: Extract text
    with st.status("🔄 Processing your document...", expanded=True) as status:
        st.write("📄 **Step 1/4** — Extracting text from PDF...")
        text = extract_text(uploaded)
        
        if not text.strip():
            st.error("Could not extract text from this PDF. It may be scanned/image-based.")
            st.stop()
        
        word_count = len(text.split())
        st.write(f"✅ Extracted **{word_count:,} words** from the document")
        
        # Step 2: Find claims
        st.write("🔎 **Step 2/4** — Identifying verifiable claims with AI...")
        try:
            claims = extract_claims(text, OPENROUTER_KEY)
        except Exception as e:
            st.error(f"Error extracting claims: {str(e)}")
            st.stop()
        
        st.write(f"✅ Found **{len(claims)} verifiable claims**")
        
        if not claims:
            st.warning("No verifiable claims found in this document.")
            st.stop()
        
        # Step 3 & 4: Verify each claim
        st.write(f"🌐 **Step 3-4/4** — Verifying claims against live web data...")
        
        results = []
        progress_bar = st.progress(0)
        
        for i, c in enumerate(claims):
            claim_text = c.get("claim", str(c))
            
            # Search web for evidence
            evidence = search_claim(claim_text, TAVILY_KEY)
            
            # Get AI verdict
            verdict = get_verdict(claim_text, evidence, client)
            
            results.append({
                "claim": claim_text,
                "type": c.get("type", "unknown"),
                **verdict
            })
            
            progress_bar.progress((i + 1) / len(claims))
            time.sleep(0.3)  # Brief pause for API rate limits
        
        status.update(label="✅ Fact-check complete!", state="complete", expanded=False)
    
    # ─── Results Summary Stats ───
    verified_count = sum(1 for r in results if r.get("verdict") == "VERIFIED")
    inaccurate_count = sum(1 for r in results if r.get("verdict") == "INACCURATE")
    false_count = sum(1 for r in results if r.get("verdict") == "FALSE")
    error_count = sum(1 for r in results if r.get("verdict") == "ERROR")
    
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number" style="color: #1a1a2e;">{len(results)}</div>
            <div class="stat-label">Total Claims</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #28a745;">{ verified_count }</div>
            <div class="stat-label">Verified</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #d4a017;">{ inaccurate_count }</div>
            <div class="stat-label">Inaccurate</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #dc3545;">{ false_count }</div>
            <div class="stat-label">False</div>
        </div>
    </div>
    <div class="custom-divider"></div>
    """, unsafe_allow_html=True)
    
    # ─── Detailed Results as Cards ───
    st.markdown("### 📋 Detailed Results")
    
    # Filter controls
    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col2:
        verdict_filter = st.selectbox(
            "Filter by verdict",
            ["All", "VERIFIED", "INACCURATE", "FALSE"],
            label_visibility="collapsed"
        )
    
    filtered_results = results if verdict_filter == "All" else [r for r in results if r.get("verdict") == verdict_filter]
    
    for i, r in enumerate(filtered_results):
        verdict = r.get("verdict", "ERROR").upper()
        confidence = r.get("confidence", "LOW")
        
        # Determine card styling
        if verdict == "VERIFIED":
            card_class = "verdict-verified"
            badge_class = "badge-verified"
            icon = "✅"
        elif verdict == "INACCURATE":
            card_class = "verdict-inaccurate"
            badge_class = "badge-inaccurate"
            icon = "⚠️"
        elif verdict == "FALSE":
            card_class = "verdict-false"
            badge_class = "badge-false"
            icon = "❌"
        else:
            card_class = "verdict-error"
            badge_class = "badge-error"
            icon = "❓"
        
        # Source links
        sources_html = ""
        if r.get("sources"):
            source_links = " · ".join([f'<a class="source-link" href="{s}" target="_blank">{s[:60]}...</a>' for s in r["sources"][:2] if s])
            if source_links:
                sources_html = f'<div style="margin-top: 8px; font-size: 11px; color: #888;">📎 Sources: {source_links}</div>'
        
        # Correction section
        correction_html = ""
        if r.get("correct_fact") and r["correct_fact"] != "null" and r["correct_fact"] is not None:
            correction_html = f'<div class="correction-text">📌 Correct fact: {r["correct_fact"]}</div>'
        
        st.markdown(f"""
        <div class="verdict-card {card_class}">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span class="verdict-badge {badge_class}">{icon} {verdict}</span>
                <span class="confidence-badge">Confidence: {confidence}</span>
                <span style="font-size: 11px; color: #888; margin-left: auto;">#{i+1} · {r.get('type', 'unknown')}</span>
            </div>
            <div class="claim-text">"{r.get('claim', 'N/A')}"</div>
            <div class="explanation-text">{r.get('explanation', 'No explanation available.')}</div>
            {correction_html}
            {sources_html}
        </div>
        """, unsafe_allow_html=True)
    
    # ─── Export Section ───
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    df = pd.DataFrame(results)
    
    # Clean up DataFrame for display/download
    display_cols = ["claim", "type", "verdict", "confidence", "explanation", "correct_fact"]
    available_cols = [c for c in display_cols if c in df.columns]
    df_export = df[available_cols]
    
    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        st.download_button(
            "📥  Download Full Report (CSV)",
            df_export.to_csv(index=False),
            file_name="factcheck_report.csv",
            mime="text/csv",
            use_container_width=True
        )

# ─── Footer ───
st.markdown("""
<div style="text-align: center; padding: 2rem 0 1rem; color: #9ca3af; font-size: 12px;">
    <div style="margin-bottom: 4px;">Built with Streamlit · OpenRouter AI · Tavily Search</div>
    <div>Fact-Check Agent © 2025 — AI-powered claim verification</div>
</div>
""", unsafe_allow_html=True)
