import streamlit as st

def apply_theme() -> None:
    st.markdown("""
    <style>
    .stApp{
        background:linear-gradient(180deg,#f8fbff 0%,#eef7ff 70%,#fff 100%);
        color:#0f172a;
    }
    .block-container{max-width:1240px;padding-top:1rem;padding-bottom:3rem}
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
    div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] div{color:#0f172a!important;font-weight:950!important}
    .metric-card{background:#fff;border:1px solid #dbeafe;border-radius:20px;padding:18px;box-shadow:0 12px 28px rgba(15,23,42,.06);min-height:125px}
    .metric-label{font-size:.72rem;font-weight:900;letter-spacing:.14em;color:#64748b;text-transform:uppercase}
    .metric-value{font-size:2rem;font-weight:950;color:#0f172a;margin-top:8px;overflow-wrap:anywhere}
    .metric-note{font-size:.86rem;color:#64748b;margin-top:4px}
    .status-info,.status-positive,.status-warning{border-radius:16px;padding:14px 16px;margin-bottom:10px;font-weight:700}
    .status-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a}
    .status-positive{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534}
    .status-warning{background:#fffbeb;border:1px solid #fde68a;color:#92400e}
    .empty-state{background:rgba(255,255,255,.94);border:1px dashed #93c5fd;border-radius:20px;padding:28px;text-align:center;color:#475569}
    [data-testid="stDataFrame"]{background:#fff;border:1px solid #dbeafe;border-radius:18px;padding:6px;box-shadow:0 12px 28px rgba(15,23,42,.06)}
    [data-testid="stDataFrame"] *{font-size:.9rem}
    h1,h2,h3{color:#0f172a!important;letter-spacing:-.03em}
    .stCaptionContainer,.stCaptionContainer p{color:#64748b!important}
    @media(max-width:900px){
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
    @media(max-width:430px){
        div[data-testid="stRadio"] div[role="radiogroup"]{
            grid-template-columns:1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)
