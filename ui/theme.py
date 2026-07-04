import streamlit as st

def apply_theme() -> None:
    st.markdown("""
    <style>
    .stApp{background:linear-gradient(180deg,#f8fbff 0%,#eef7ff 70%,#fff 100%);color:#0f172a}
    .block-container{max-width:1180px;padding-top:1rem;padding-bottom:3rem}
    [data-testid="stHeader"]{background:rgba(248,251,255,.88);backdrop-filter:blur(14px)}
    #MainMenu,footer{visibility:hidden}
    .hero{background:linear-gradient(135deg,#fff,#eff6ff);border:1px solid #bfdbfe;border-radius:28px;padding:24px;box-shadow:0 18px 42px rgba(15,23,42,.08);margin-bottom:18px}
    .hero h1{font-size:clamp(2.4rem,5vw,4.5rem);letter-spacing:-.07em;margin:0;color:#0f172a}
    .hero p{color:#475569;font-size:1.05rem;line-height:1.55}
    .badge{display:inline-block;padding:8px 12px;border-radius:999px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;font-weight:800}
    div[data-testid="stRadio"]{position:sticky;top:0;z-index:999;background:rgba(255,255,255,.97);border:1px solid #dbeafe;border-radius:20px;padding:8px;margin-bottom:1rem;box-shadow:0 12px 28px rgba(15,23,42,.08)}
    div[data-testid="stRadio"] div[role="radiogroup"]{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:8px;scrollbar-width:none}
    div[data-testid="stRadio"] div[role="radiogroup"]::-webkit-scrollbar{display:none}
    div[data-testid="stRadio"] label{flex:0 0 auto;min-width:120px;padding:8px 12px;border:1px solid #bfdbfe;border-radius:14px;background:#fff;justify-content:center}
    div[data-testid="stRadio"] label p{color:#334155!important;font-weight:800;white-space:nowrap}
    div[data-testid="stRadio"] label:has(input:checked){background:linear-gradient(135deg,#2563eb,#06b6d4);border-color:#2563eb}
    div[data-testid="stRadio"] label:has(input:checked) p{color:#fff!important}
    .metric-card{background:#fff;border:1px solid #dbeafe;border-radius:20px;padding:18px;box-shadow:0 12px 28px rgba(15,23,42,.06);min-height:125px}
    .metric-label{font-size:.72rem;font-weight:900;letter-spacing:.14em;color:#64748b;text-transform:uppercase}
    .metric-value{font-size:2rem;font-weight:950;color:#0f172a;margin-top:8px}
    .metric-note{font-size:.86rem;color:#64748b;margin-top:4px}
    .status-info,.status-positive,.status-warning{border-radius:16px;padding:14px 16px;margin-bottom:10px;font-weight:700}
    .status-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a}
    .status-positive{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534}
    .status-warning{background:#fffbeb;border:1px solid #fde68a;color:#92400e}
    .empty-state{background:rgba(255,255,255,.94);border:1px dashed #93c5fd;border-radius:20px;padding:28px;text-align:center;color:#475569}
    </style>
    """, unsafe_allow_html=True)
