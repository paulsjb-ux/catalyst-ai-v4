import streamlit as st

def apply_theme() -> None:
    st.markdown("""
    <style>

    .compact-hero{padding:16px 20px;border-radius:20px;margin-bottom:12px}
    .brand-row{display:flex;align-items:center;gap:14px}
    .brand-mark{font-size:2.2rem;line-height:1}
    .compact-hero h1{font-size:clamp(1.8rem,3vw,2.7rem);letter-spacing:-.055em;margin:0}
    .compact-hero p{font-size:.9rem;margin:.25rem 0 0;color:#475569}
    .compact-hero p span{color:#64748b}
    .compact-hero .badge{margin-left:auto;white-space:nowrap;padding:6px 10px;font-size:.78rem}
    div[data-testid="column"] .stButton > button{min-height:42px!important;padding:.45rem .35rem!important;border-radius:12px!important;font-size:.88rem!important;box-shadow:0 7px 16px rgba(37,99,235,.14)!important}
    .stApp{
        background:linear-gradient(180deg,#f8fbff 0%,#eef7ff 70%,#fff 100%);
        color:#0f172a;
    }
    .block-container{max-width:1380px;padding-top:.45rem;padding-bottom:2.5rem}
    [data-testid="stHeader"]{background:rgba(248,251,255,.88);backdrop-filter:blur(14px)}
    #MainMenu,footer{visibility:hidden}
    .hero{background:linear-gradient(135deg,#fff,#eff6ff);border:1px solid #bfdbfe;border-radius:28px;padding:24px;box-shadow:0 18px 42px rgba(15,23,42,.08);margin-bottom:18px}
    .hero h1{font-size:clamp(2.4rem,5vw,4.5rem);letter-spacing:-.07em;margin:0;color:#0f172a}
    .hero p{color:#475569;font-size:1.05rem;line-height:1.55}
    .badge{display:inline-block;padding:8px 12px;border-radius:999px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;font-weight:800}
    div[data-testid="stRadio"]{position:sticky;top:0;z-index:999;background:rgba(255,255,255,.97);border:1px solid #dbeafe;border-radius:20px;padding:8px;margin-bottom:1rem;box-shadow:0 12px 28px rgba(15,23,42,.08);overflow-x:auto}
    div[data-testid="stRadio"] div[role="radiogroup"]{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:8px;scrollbar-width:none}
    div[data-testid="stRadio"] div[role="radiogroup"]::-webkit-scrollbar{display:none}
    div[data-testid="stRadio"] label{flex:0 0 auto;min-width:132px;padding:8px 14px;border:1px solid #bfdbfe;border-radius:14px;background:#fff;justify-content:center}
    div[data-testid="stRadio"] label p{color:#334155!important;font-weight:850;white-space:nowrap}
    div[data-testid="stRadio"] label:has(input:checked){background:linear-gradient(135deg,#2563eb,#06b6d4);border-color:#2563eb}
    div[data-testid="stRadio"] label:has(input:checked) p{color:#fff!important}
    label,[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p{color:#334155!important;font-weight:800!important}
    .stTextArea textarea,.stTextInput input,div[data-baseweb="select"]>div{background:#fff!important;color:#0f172a!important;border:1px solid #bfdbfe!important;border-radius:14px!important;box-shadow:0 8px 20px rgba(15,23,42,.05)}
    .stTextArea textarea{font-size:.95rem!important;line-height:1.45!important}
    div[data-baseweb="select"] span{color:#0f172a!important;font-weight:700}
    .stSlider div[data-testid="stThumbValue"]{color:#0f172a!important;font-weight:900!important}
    .stButton button,.stDownloadButton button{background:linear-gradient(135deg,#2563eb,#06b6d4)!important;color:#fff!important;border:0!important;border-radius:16px!important;min-height:48px;font-weight:900!important;box-shadow:0 12px 28px rgba(37,99,235,.20)}
    div[data-testid="stMetric"]{background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:14px 16px;box-shadow:0 10px 24px rgba(15,23,42,.05)}
    div[data-testid="stMetric"] label,div[data-testid="stMetric"] label p{color:#334155!important;font-weight:800!important}
    div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] div{color:#0f172a!important;font-weight:950!important;font-size:clamp(1.55rem,3vw,2.45rem)!important;white-space:normal!important;overflow-wrap:anywhere}
    .metric-card{background:#fff;border:1px solid #dbeafe;border-radius:20px;padding:18px;box-shadow:0 12px 28px rgba(15,23,42,.06);min-height:125px}
    .metric-label{font-size:.72rem;font-weight:900;letter-spacing:.14em;color:#64748b;text-transform:uppercase}
    .metric-value{font-size:2rem;font-weight:950;color:#0f172a;margin-top:8px;overflow-wrap:anywhere}
    .metric-note{font-size:.86rem;color:#64748b;margin-top:4px}
    .status-info,.status-positive,.status-warning{border-radius:16px;padding:14px 16px;margin-bottom:10px;font-weight:700}
    .status-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a}
    .status-positive{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534}
    .status-warning{background:#fffbeb;border:1px solid #f59e0b;color:#78350f}
    .decision-hero{border-radius:26px;padding:28px;margin:10px 0 22px;box-shadow:0 20px 45px rgba(15,23,42,.10);border:1px solid transparent}
    .decision-trade{background:linear-gradient(135deg,#ecfdf5,#dcfce7);border-color:#86efac}
    .decision-watch{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fbbf24}
    .decision-no-trade{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border-color:#fda4af}
    .decision-kicker{font-size:.75rem;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:#64748b}
    .decision-action{font-size:clamp(2.5rem,7vw,5rem);font-weight:950;letter-spacing:-.06em;color:#0f172a;margin-top:8px}
    .decision-headline{font-size:clamp(1.15rem,2.5vw,1.65rem);font-weight:900;color:#1e293b;margin-top:8px}
    .decision-guidance{font-size:1rem;color:#475569;margin-top:6px;max-width:850px}
    .opportunity-title{display:flex;justify-content:space-between;gap:16px;align-items:center;background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:16px 18px;margin-bottom:12px;font-weight:900;color:#0f172a;box-shadow:0 10px 24px rgba(15,23,42,.05)}
    [data-testid="stAlert"]{border-radius:16px!important}
    [data-testid="stAlert"] p,[data-testid="stAlert"] div{color:#422006!important;font-weight:750!important}
    .empty-state{background:rgba(255,255,255,.94);border:1px dashed #93c5fd;border-radius:20px;padding:28px;text-align:center;color:#475569}
    [data-testid="stDataFrame"]{background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:6px;box-shadow:0 12px 28px rgba(15,23,42,.06)}
    [data-testid="stDataFrame"] *{font-size:.9rem}
    h1,h2,h3{color:#0f172a!important;letter-spacing:-.03em}
    .stCaptionContainer,.stCaptionContainer p{color:#64748b!important}
    @media(max-width:900px){
        .hero{padding:18px;border-radius:22px}
        .hero h1{font-size:clamp(2.1rem,11vw,3.6rem)}
        .metric-card{min-height:108px;padding:14px}
        .metric-value{font-size:clamp(1.45rem,8vw,2rem)}
        div[data-testid="column"]{min-width:0!important}
        [data-testid="stDataFrame"]{overflow-x:auto}

        .block-container{padding-left:1rem;padding-right:1rem}
        div[data-testid="stRadio"]{
            position:static;
            top:auto;
            overflow:visible;
            padding:8px;
        }
        div[data-testid="stRadio"] div[role="radiogroup"]{
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:8px;
            overflow:visible;
            width:100%;
        }
        div[data-testid="stRadio"] label{
            min-width:0;
            width:100%;
            margin:0!important;
            padding:10px 8px;
            overflow:hidden;
        }
        div[data-testid="stRadio"] label p{
            white-space:normal;
            text-align:center;
            line-height:1.15;
            font-size:.92rem;
        }
    }
    @media(max-width:520px){
        .block-container{padding-left:.65rem;padding-right:.65rem}
        div[data-testid="stHorizontalBlock"]{gap:.55rem}
        div[data-testid="stMetric"]{padding:10px 12px}
        .metric-label{font-size:.66rem}
        .metric-note{font-size:.78rem}
    }
    @media(max-width:430px){
        div[data-testid="stRadio"] div[role="radiogroup"]{
            grid-template-columns:1fr;
        }
    }

    .routine-command{background:#ffffff;border:1px solid #dbeafe;border-radius:18px;padding:18px 20px;margin:2px 0 12px;box-shadow:0 10px 24px rgba(15,23,42,.05)}
    .routine-eyebrow{font-size:.72rem;font-weight:900;letter-spacing:.16em;color:#2563eb;margin-bottom:5px}
    .routine-title{font-size:1.75rem;font-weight:900;letter-spacing:-.04em;color:#0f172a;line-height:1.05}
    .routine-subtitle{margin-top:7px;color:#64748b;font-weight:600;max-width:850px}
    .stButton>button[kind="primary"]{min-height:3.35rem;font-size:1.05rem;font-weight:900;border-radius:14px}

    /* Catalyst AI v11 — workflow-first executive workspace */
    .block-container{max-width:1500px!important;padding-top:.35rem!important}
    .nav-label{font-size:.66rem;font-weight:950;letter-spacing:.16em;color:#64748b;margin:.15rem 0 .35rem .15rem}
    div[data-testid="stExpander"]{border:1px solid #dbeafe!important;border-radius:14px!important;background:rgba(255,255,255,.72)!important;margin:.45rem 0 .8rem!important;box-shadow:none!important}
    div[data-testid="stExpander"] summary{font-size:.84rem!important;font-weight:850!important;color:#334155!important;padding:.55rem .8rem!important}
    div[data-testid="column"] .stButton > button{min-height:38px!important;padding:.35rem .28rem!important;border-radius:10px!important;font-size:.8rem!important;box-shadow:0 5px 12px rgba(37,99,235,.11)!important}
    .workspace-header{display:flex;align-items:center;justify-content:space-between;gap:16px;background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:13px 17px;margin:8px 0 16px;box-shadow:0 8px 22px rgba(15,23,42,.05)}
    .workspace-brand{display:flex;align-items:center;gap:10px;min-width:0}
    .workspace-mark{font-size:1.45rem}
    .workspace-product{font-size:.7rem;font-weight:950;letter-spacing:.11em;text-transform:uppercase;color:#2563eb}
    .workspace-product span{color:#64748b;margin-left:5px}
    .workspace-header h1{font-size:clamp(1.35rem,2.5vw,2rem);letter-spacing:-.04em;margin:1px 0 0;color:#0f172a}
    .workspace-engine{font-size:.78rem;color:#64748b;font-weight:750;white-space:nowrap}
    .routine-command.v101-command{padding:18px 22px!important;border-radius:20px!important;margin-top:8px!important}
    .routine-title{font-size:clamp(1.8rem,4vw,3rem)!important}
    .routine-subtitle{font-size:.92rem!important}
    .desk-status-strip{margin-top:4px!important}
    @media(max-width:760px){
      .workspace-engine{display:none}
      .workspace-header{padding:11px 13px}
      .workspace-header h1{font-size:1.35rem}
      .nav-label{margin-top:.1rem}
      div[data-testid="column"] .stButton > button{font-size:.72rem!important;min-height:42px!important}
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .block-container{max-width:1500px!important;padding-top:.3rem!important}
    .desk-status-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:#dbeafe;border:1px solid #dbeafe;border-radius:14px;overflow:hidden;margin:4px 0 10px;box-shadow:0 8px 20px rgba(15,23,42,.05)}
    .desk-status-strip>div{background:rgba(255,255,255,.96);padding:9px 13px;display:flex;justify-content:space-between;gap:10px;align-items:center}
    .desk-status-strip span{font-size:.65rem;font-weight:900;letter-spacing:.11em;color:#64748b}
    .desk-status-strip strong{font-size:.78rem;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .v101-command{padding:14px 18px!important;margin-bottom:8px!important}
    .routine-brand-row{display:flex;align-items:center;justify-content:space-between;gap:20px}
    .routine-mark{font-size:2.25rem}
    .v101-command .routine-title{font-size:1.65rem}
    .v101-command .routine-subtitle{font-size:.9rem;margin-top:4px}
    .stButton>button[kind="primary"]{min-height:4rem!important;font-size:1.18rem!important;letter-spacing:.02em!important;border-radius:14px!important}
    .desk-awaiting{background:#fff;border:1px dashed #93c5fd;border-radius:16px;padding:16px;text-align:center;color:#475569;margin-top:12px}
    .daily-verdict{border-radius:16px;padding:14px 18px;margin:12px 0 14px;box-shadow:0 8px 20px rgba(15,23,42,.05)}
    .daily-verdict span{display:block;font-size:.68rem;font-weight:900;letter-spacing:.13em;margin-bottom:3px}
    .daily-verdict strong{display:block;font-size:1.2rem;letter-spacing:-.02em}
    .daily-verdict p{margin:3px 0 0;font-size:.88rem}
    .verdict-trade{background:#ecfdf5;border:1px solid #86efac;color:#14532d}
    .verdict-cash{background:#eff6ff;border:1px solid #93c5fd;color:#1e3a8a}
    .metric-card{min-height:98px!important;padding:13px 15px!important;border-radius:16px!important}
    .metric-value{font-size:1.45rem!important;margin-top:5px!important}
    .metric-note{font-size:.76rem!important}
    .action-card{background:#fff;border:1px solid #dbeafe;border-radius:16px;padding:15px;box-shadow:0 8px 20px rgba(15,23,42,.06);min-height:190px}
    .action-rank{font-size:.66rem;letter-spacing:.12em;font-weight:900;color:#64748b}
    .action-ticker{font-size:1.8rem;font-weight:950;letter-spacing:-.05em;margin-top:5px;color:#0f172a}
    .action-label{display:inline-block;margin-top:2px;padding:3px 8px;border-radius:999px;background:#dcfce7;color:#166534;font-size:.72rem;font-weight:900}
    .action-detail{margin-top:12px;color:#334155;font-size:.9rem}
    .action-levels{margin-top:8px;color:#64748b;font-size:.83rem;line-height:1.55}
    @media(max-width:900px){.desk-status-strip{grid-template-columns:repeat(2,minmax(0,1fr))}.desk-status-strip>div{padding:8px 10px}.routine-mark{display:none}}
    @media(max-width:520px){.desk-status-strip{grid-template-columns:1fr}.desk-status-strip>div{padding:8px 10px}.v101-command .routine-title{font-size:1.45rem}}

    /* Catalyst AI v11 — workflow-first executive workspace */
    .block-container{max-width:1500px!important;padding-top:.35rem!important}
    .nav-label{font-size:.66rem;font-weight:950;letter-spacing:.16em;color:#64748b;margin:.15rem 0 .35rem .15rem}
    div[data-testid="stExpander"]{border:1px solid #dbeafe!important;border-radius:14px!important;background:rgba(255,255,255,.72)!important;margin:.45rem 0 .8rem!important;box-shadow:none!important}
    div[data-testid="stExpander"] summary{font-size:.84rem!important;font-weight:850!important;color:#334155!important;padding:.55rem .8rem!important}
    div[data-testid="column"] .stButton > button{min-height:38px!important;padding:.35rem .28rem!important;border-radius:10px!important;font-size:.8rem!important;box-shadow:0 5px 12px rgba(37,99,235,.11)!important}
    .workspace-header{display:flex;align-items:center;justify-content:space-between;gap:16px;background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:13px 17px;margin:8px 0 16px;box-shadow:0 8px 22px rgba(15,23,42,.05)}
    .workspace-brand{display:flex;align-items:center;gap:10px;min-width:0}
    .workspace-mark{font-size:1.45rem}
    .workspace-product{font-size:.7rem;font-weight:950;letter-spacing:.11em;text-transform:uppercase;color:#2563eb}
    .workspace-product span{color:#64748b;margin-left:5px}
    .workspace-header h1{font-size:clamp(1.35rem,2.5vw,2rem);letter-spacing:-.04em;margin:1px 0 0;color:#0f172a}
    .workspace-engine{font-size:.78rem;color:#64748b;font-weight:750;white-space:nowrap}
    .routine-command.v101-command{padding:18px 22px!important;border-radius:20px!important;margin-top:8px!important}
    .routine-title{font-size:clamp(1.8rem,4vw,3rem)!important}
    .routine-subtitle{font-size:.92rem!important}
    .desk-status-strip{margin-top:4px!important}
    @media(max-width:760px){
      .workspace-engine{display:none}
      .workspace-header{padding:11px 13px}
      .workspace-header h1{font-size:1.35rem}
      .nav-label{margin-top:.1rem}
      div[data-testid="column"] .stButton > button{font-size:.72rem!important;min-height:42px!important}
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    /* Catalyst AI v11.1 — ultra-compact workspace */
    .block-container{max-width:1450px!important;padding-top:.15rem!important;padding-bottom:1.25rem!important}
    [data-testid="stVerticalBlock"]{gap:.45rem!important}
    .nav-label{display:none!important}
    div[data-testid="column"] .stButton > button{min-height:30px!important;height:30px!important;padding:.12rem .3rem!important;border-radius:8px!important;font-size:.72rem!important;font-weight:800!important;box-shadow:0 2px 7px rgba(37,99,235,.09)!important}
    div[data-testid="stExpander"]{margin:.2rem 0 .4rem!important;border-radius:10px!important}
    div[data-testid="stExpander"] summary{padding:.3rem .65rem!important;font-size:.74rem!important}
    .workspace-header{min-height:38px!important;padding:5px 10px!important;margin:4px 0 8px!important;border-radius:10px!important;box-shadow:none!important}
    .workspace-brand{gap:6px!important}.workspace-mark{font-size:1rem!important}
    .workspace-header h1{font-size:1.05rem!important;letter-spacing:-.02em!important;margin:0!important}
    .workspace-product{font-size:.62rem!important;letter-spacing:.05em!important;text-transform:none!important}
    .workspace-engine{display:none!important}
    .desk-status-strip{margin:2px 0 5px!important;border-radius:9px!important;box-shadow:none!important}
    .desk-status-strip>div{padding:5px 8px!important;min-height:29px!important}
    .desk-status-strip span{font-size:.55rem!important;letter-spacing:.08em!important}.desk-status-strip strong{font-size:.68rem!important}
    .routine-command.v101-command{padding:8px 12px!important;border-radius:11px!important;margin:3px 0 5px!important;box-shadow:none!important}
    .routine-brand-row{display:block!important}
    .v101-command .routine-title{font-size:1.2rem!important;line-height:1.1!important}
    .v101-command .routine-title span{font-size:.62rem!important;color:#2563eb!important;letter-spacing:.04em!important;white-space:nowrap!important}
    .v101-command .routine-subtitle{font-size:.75rem!important;margin-top:2px!important}
    .routine-mark,.routine-eyebrow{display:none!important}
    .stButton>button[kind="primary"]{min-height:42px!important;height:42px!important;font-size:.9rem!important;border-radius:10px!important}
    .metric-card{min-height:72px!important;padding:8px 10px!important;border-radius:11px!important;box-shadow:none!important}
    .metric-label{font-size:.58rem!important}.metric-value{font-size:1.08rem!important;margin-top:2px!important}.metric-note{font-size:.65rem!important;margin-top:1px!important}
    .daily-verdict{padding:8px 12px!important;margin:6px 0 8px!important;border-radius:11px!important;box-shadow:none!important}
    .daily-verdict strong{font-size:1rem!important}.daily-verdict p{font-size:.75rem!important;margin-top:1px!important}
    h1{font-size:1.45rem!important} h2{font-size:1.2rem!important} h3{font-size:1rem!important;margin-top:.5rem!important}
    @media(max-width:760px){div[data-testid="column"] .stButton > button{min-height:34px!important;height:auto!important;font-size:.68rem!important}.workspace-product{display:none!important}.desk-status-strip{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
    </style>
    """, unsafe_allow_html=True)

# v10.1 command-centre refinements are injected after the shared theme.

# v10.1 compact executive trading desk overrides.
def _v101_theme_marker() -> None:
    pass

# v11 workspace overrides are appended below by apply_theme source patch.
