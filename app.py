import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import re
import io
import os
import math
from io import BytesIO
from PIL import Image
import sys

# 1. Ensure user site-packages is in sys.path
user_site_packages = os.path.expandvars(
    r"%USERPROFILE%\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages"
)
if os.path.exists(user_site_packages):
    if user_site_packages not in sys.path:
        sys.path.insert(0, user_site_packages)

# 2. Fix the google namespace path conflict
try:
    import google
    if hasattr(google, "__path__"):
        google_local = os.path.join(user_site_packages, "google")
        if os.path.exists(google_local) and google_local not in google.__path__:
            google.__path__ = [google_local] + list(google.__path__)
except Exception:
    pass

from google import genai
from google.genai import types
from streamlit_cropper import st_cropper

st.set_page_config(page_title="Cosmetics Formulation AI", page_icon="🧪", layout="wide")

# ------------------------------------------------------------------
# API 키 초기화 및 환경 변수 자동 인식
# ------------------------------------------------------------------
if "api_key" not in st.session_state:
    # 1. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "").strip().strip('\"\'')
    # 2. Streamlit secrets
    secrets_key = ""
    try:
        secrets_key = st.secrets.get("GEMINI_API_KEY", "").strip().strip('\"\'')
    except Exception:
        pass
    
    st.session_state.api_key = env_key or secrets_key
    st.session_state.step = 1 if st.session_state.api_key else 0

# ------------------------------------------------------------------
# 세션 상태 기본값 설정
# ------------------------------------------------------------------
DEFAULT_DB = [
    {"name": "정제수", "inci": "Water", "unit_cost": 2, "supplier": "삼성정밀"},
    {"name": "글리세린", "inci": "Glycerin", "unit_cost": 15, "supplier": "동화약품"},
    {"name": "부틸렌글라이콜", "inci": "Butylene Glycol", "unit_cost": 12, "supplier": "동화약품"},
    {"name": "나이아신아마이드", "inci": "Niacinamide", "unit_cost": 45, "supplier": "대봉엘에스"},
    {"name": "세테아릴알코올", "inci": "Cetearyl Alcohol", "unit_cost": 20, "supplier": "코스맥스"},
    {"name": "다이메티콘", "inci": "Dimethicone", "unit_cost": 18, "supplier": "다우코닝"},
    {"name": "잔탄검", "inci": "Xanthan Gum", "unit_cost": 60, "supplier": "대봉엘에스"},
    {"name": "페녹시에탄올", "inci": "Phenoxyethanol", "unit_cost": 25, "supplier": "동화약품"},
    {"name": "토코페롤", "inci": "Tocopherol", "unit_cost": 80, "supplier": "BASF"},
    {"name": "히알루론산", "inci": "Sodium Hyaluronate", "unit_cost": 250, "supplier": "대봉엘에스"},
    {"name": "세틸에틸헥사노에이트", "inci": "Cetyl Ethylhexanoate", "unit_cost": 22, "supplier": "코스맥스"},
    {"name": "폴리소르베이트60", "inci": "Polysorbate 60", "unit_cost": 30, "supplier": "크로다"},
    {"name": "소르비탄스테아레이트", "inci": "Sorbitan Stearate", "unit_cost": 28, "supplier": "크로다"},
    {"name": "스쿠알란", "inci": "Squalane", "unit_cost": 95, "supplier": "아모레퍼시픽"},
    {"name": "알란토인", "inci": "Allantoin", "unit_cost": 40, "supplier": "대봉엘에스"},
]

for key, default in [
    ("db", pd.DataFrame(DEFAULT_DB)),
    ("model_name", "gemini-2.5-flash"),
    ("ftype", None),
    ("label_ingredients", None),
    ("label_original", None),
    ("label_crop", None),
    ("raw_formulation", None),
    ("formulation", None),
    ("manufacturing_guide", ""),
    ("product_spec", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------------------------------------------------------
# 마우스 반응형 리퀴드 글라스 스포트라이트
# ------------------------------------------------------------------
components.html("""
<script>
(function() {
  const doc = window.parent.document;
  function ensureSpot() {
    let spot = doc.getElementById('cfa-spotlight');
    if (!spot) {
      spot = doc.createElement('div');
      spot.id = 'cfa-spotlight';
      spot.style.position = 'fixed';
      spot.style.inset = '0';
      spot.style.pointerEvents = 'none';
      spot.style.zIndex = '0';
      spot.style.transition = 'background 0.08s ease-out';
      doc.body.appendChild(spot);
    }
    return spot;
  }
  ensureSpot();
  doc.addEventListener('mousemove', function(e) {
    const s = ensureSpot();
    s.style.background =
      'radial-gradient(850px circle at ' + e.clientX + 'px ' + e.clientY + 'px, rgba(6,182,212,0.15), rgba(217,70,239,0.06) 30%, transparent 60%)';
  });
})();
</script>
""", height=0)

# ------------------------------------------------------------------
# CSS (디자인 고도화)
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
.stApp { background: #080415; color: #f8fafc; }
iframe { border: none !important; background: transparent !important; }

/* 컬럼 및 컨테이너 글라스모피즘 스타일링 (빈 박스 제거 기법) */
div[data-testid="column"]:has(.cfa-step0-marker),
div[class*="stColumn"]:has(.cfa-step0-marker),
.stColumn:has(.cfa-step0-marker),
div[data-testid="column"]:has(.cfa-step2-marker),
div[class*="stColumn"]:has(.cfa-step2-marker),
.stColumn:has(.cfa-step2-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(.cfa-step2-full-marker),
div[data-testid="vertical-block"]:has(.cfa-step2-full-marker) {
    position: relative;
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01)) !important;
    backdrop-filter: blur(30px) saturate(220%) !important;
    -webkit-backdrop-filter: blur(30px) saturate(220%) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    box-shadow: 0 25px 60px rgba(0,0,0,0.55), inset 0 1px 1px rgba(255,255,255,0.25), inset 0 -1px 8px rgba(255,255,255,0.05) !important;
    padding: 28px 24px !important;
    box-sizing: border-box !important;
    margin-bottom: 20px !important;
}
div[data-testid="column"]:has(.cfa-step0-marker)::before,
div[class*="stColumn"]:has(.cfa-step0-marker)::before,
.stColumn:has(.cfa-step0-marker)::before,
div[data-testid="column"]:has(.cfa-step2-marker)::before,
div[class*="stColumn"]:has(.cfa-step2-marker)::before,
.stColumn:has(.cfa-step2-marker)::before,
[data-testid="stVerticalBlockBorderWrapper"]:has(.cfa-step2-full-marker)::before,
div[data-testid="vertical-block"]:has(.cfa-step2-full-marker)::before {
    content: "";
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 1.5px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
}


/* 배경 장식 애니메이션 블롭 - Deep Space Anti-Gravity Chamber */
.cfa-blob { position: fixed; border-radius: 50%; filter: blur(140px); opacity: 0.28; z-index: -1; pointer-events:none; }
.cfa-blob1 { width: 550px; height: 550px; background: radial-gradient(circle, #d946ef, transparent 72%); top: -180px; left: -120px; animation: floatA 24s ease-in-out infinite; }
.cfa-blob2 { width: 500px; height: 500px; background: radial-gradient(circle, #06b6d4, transparent 72%); bottom: -200px; right: -100px; animation: floatB 28s ease-in-out infinite; }
.cfa-blob3 { width: 400px; height: 400px; background: radial-gradient(circle, #3b82f6, transparent 72%); top: 30%; left: 40%; animation: floatC 30s ease-in-out infinite; }
@keyframes floatA { 0%,100%{transform:translate(0,0) scale(1);} 50%{transform:translate(100px,80px) scale(1.08);} }
@keyframes floatB { 0%,100%{transform:translate(0,0) scale(1);} 50%{transform:translate(-90px,-70px) scale(1.1);} }
@keyframes floatC { 0%,100%{transform:translate(0,0);} 50%{transform:translate(-60px,90px);} }

/* 헤더 & 네비게이션 */
.cfa-header-row { display:flex; align-items:center; justify-content:space-between; padding: 16px 8px; position:relative; z-index:2; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.cfa-brand { display:flex; align-items:center; gap:16px; }
.cfa-brand .badge { width:48px; height:48px; border-radius:16px; background: linear-gradient(135deg, #d946ef, #3b82f6); display:flex; align-items:center; justify-content:center; font-size:24px; box-shadow: 0 0 20px rgba(6, 182, 212, 0.4); }
.cfa-brand h1 { font-family:'Space Grotesk',sans-serif; font-size:26px; font-weight:700; color:#ffffff; margin:0; line-height:1.1; text-shadow: 0 0 15px rgba(6, 182, 212, 0.3); }
.cfa-brand p { font-size:11px; color:#a78bfa; letter-spacing:1.8px; text-transform:uppercase; margin:2px 0 0 0; font-weight: 600; }

/* 단계 표시 인디케이터 (Stepper) - Floating Glass Capsules */
.cfa-stepper { display: flex; align-items: center; justify-content: center; gap: 16px; margin: 28px 0; font-family: 'Space Grotesk', sans-serif; }
.cfa-step { display: flex; align-items: center; gap: 8px; padding: 8px 20px; border-radius: 999px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); font-size: 13.5px; font-weight: 600; color: #94a3b8; transition: all 0.3s; }
.cfa-step.active { background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(217,70,239,0.08)); border-color: rgba(6,182,212,0.5); color: #06b6d4; box-shadow: 0 0 15px rgba(6,182,212,0.25); }
.cfa-step.done { background: rgba(255,255,255,0.06); border-color: #3b82f6; color: #38bdf8; }
.cfa-step-arrow { color: rgba(255,255,255,0.15); font-weight: bold; }

/* 리퀴드 글라스 프리미엄 카드 디자인 - Multi-layered Crystal Glass */
.liquid-glass {
    position: relative; border-radius: 24px;
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
    backdrop-filter: blur(30px) saturate(220%);
    -webkit-backdrop-filter: blur(30px) saturate(220%);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: 0 25px 60px rgba(0,0,0,0.55), inset 0 1px 1px rgba(255,255,255,0.25), inset 0 -1px 8px rgba(255,255,255,0.05);
    overflow: hidden; z-index:1; padding: 24px;
}
.liquid-glass::before { content: ""; position: absolute; top:0; left:10%; right:10%; height:1.5px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); }

/* 제형 선택 그리드 및 호버 효과 */
div[data-testid="column"]:has(.cfa-tile-marker),
div[class*="stColumn"]:has(.cfa-tile-marker),
.stColumn:has(.cfa-tile-marker) {
    position: relative;
}
.cfa-tile { padding: 24px 8px 16px 8px; text-align:center; margin-bottom: 14px; display:flex; flex-direction:column; align-items:center; }
.cfa-icon-wrap { width: 140px; height: 140px; margin: 0 auto; transition: transform .5s cubic-bezier(.175,.885,.32,1.275), filter .5s; }
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-icon-wrap,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-icon-wrap,
.stColumn:has(.cfa-tile-marker):hover .cfa-icon-wrap {
    transform: scale(1.18) rotate(-4deg) !important;
    filter: drop-shadow(0 0 25px rgba(6,182,212,0.45)) !important;
}
.cfa-name-pill {
    position: relative; overflow: hidden;
    display:inline-flex; align-items:center; justify-content:center;
    margin-top:14px; padding: 8px 26px; border-radius:999px;
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
    backdrop-filter: blur(16px);
    border:1px solid rgba(255,255,255,0.12);
    font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:15px; color:#ffffff;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,0.2);
    transition: all .35s cubic-bezier(.2,.8,.2,1);
    width: max-content; white-space: nowrap;
}
.cfa-name-pill::before {
    content: ""; position:absolute; top:-60%; left:-30%; width:60%; height:220%;
    background: linear-gradient(120deg, rgba(255,255,255,0.3), transparent 60%);
    transform: rotate(20deg); pointer-events:none; z-index:2;
}
.cfa-name-pill::after {
    content: ""; position:absolute; width:24px; height:24px; border-radius:50%;
    background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.4), rgba(6,182,212,0.1) 70%);
    top:50%; left:10%;
    animation: cfaDropletA 6s ease-in-out infinite;
    pointer-events:none; z-index:1;
}
.cfa-liquid-drop2 {
    content: ""; position:absolute; width:14px; height:14px; border-radius:50%;
    background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.4), rgba(217,70,239,0.1) 70%);
    top:60%; left:60%;
    animation: cfaDropletB 4s ease-in-out infinite;
    pointer-events:none; z-index:1;
}
@keyframes cfaDropletA {
    0%   { transform: translate(0,-50%) scale(0.8); opacity:0.3; }
    30%  { transform: translate(70px,-65%) scale(1.15); opacity:0.7; }
    60%  { transform: translate(140px,-35%) scale(0.75); opacity:0.4; }
    100% { transform: translate(0,-50%) scale(0.8); opacity:0.3; }
}
@keyframes cfaDropletB {
    0%   { transform: translate(0,0) scale(0.6); opacity:0.25; }
    40%  { transform: translate(-50px,-20px) scale(1.05); opacity:0.65; }
    100% { transform: translate(0,0) scale(0.6); opacity:0.25; }
}
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-name-pill,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-name-pill,
.stColumn:has(.cfa-tile-marker):hover .cfa-name-pill {
    background: linear-gradient(135deg, rgba(217,70,239,0.7), rgba(59,130,246,0.65)) !important;
    border-color: rgba(255,255,255,0.4) !important;
    color:#fff !important; transform: translateY(-4px) scale(1.05) !important;
    box-shadow: 0 16px 36px rgba(217,70,239,0.35), inset 0 1px 1px rgba(255,255,255,0.3) !important;
}
div[data-testid="column"],
div[class*="stColumn"],
.stColumn {
    position: relative !important;
}
div[data-testid="column"] .liquid-glass.cfa-tile,
div[class*="stColumn"] .liquid-glass.cfa-tile,
.stColumn .liquid-glass.cfa-tile {
    pointer-events: none !important;
}
div[data-testid="column"] > div,
div[data-testid="column"] [data-testid="stVerticalBlock"],
div[data-testid="column"] .stVerticalBlock,
div[class*="stColumn"] > div,
div[class*="stColumn"] [data-testid="stVerticalBlock"],
div[class*="stColumn"] .stVerticalBlock,
.stColumn > div,
.stColumn [data-testid="stVerticalBlock"],
.stColumn .stVerticalBlock {
    position: relative !important;
    height: 100% !important;
    width: 100% !important;
}
/* key-based direct target for overlaying buttons safely across all Streamlit versions */
div[class*="st-key-btn_"] {
    position: absolute !important;
    inset: 0 !important;
    z-index: 99999 !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 100% !important;
    width: 100% !important;
}
div[class*="st-key-btn_"] .stButton,
div[class*="st-key-btn_"] button {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    border-radius: 24px !important;
}

/* SVG 아이콘 내부 부품 호버 애니메이션 */
@keyframes cfaWobble { 0%{transform:rotate(0);} 25%{transform:rotate(-4deg);} 50%{transform:rotate(3deg);} 75%{transform:rotate(-1.5deg);} 100%{transform:rotate(0);} }
@keyframes cfaCapPop { 0%,100%{transform:translateY(0);} 45%{transform:translateY(-6px);} }
@keyframes cfaBubbleUp { 0%{transform:translateY(0) scale(0.5); opacity:0;} 25%{opacity:0.8; transform:translateY(-8px) scale(1);} 100%{transform:translateY(-36px) scale(0.4); opacity:0;} }
@keyframes cfaShineSweep { 0%{transform:translateX(-35px); opacity:0;} 35%{opacity:.7;} 100%{transform:translateX(35px); opacity:0;} }
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-body-anim,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-body-anim,
.stColumn:has(.cfa-tile-marker):hover .cfa-body-anim {
    animation: cfaWobble .8s ease-in-out;
    transform-box: fill-box;
    transform-origin: 50% 100%;
}
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-cap-anim,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-cap-anim,
.stColumn:has(.cfa-tile-marker):hover .cfa-cap-anim {
    animation: cfaCapPop .8s ease-in-out;
    transform-box: fill-box;
    transform-origin: 50% 100%;
}
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-bubble-anim,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-bubble-anim,
.stColumn:has(.cfa-tile-marker):hover .cfa-bubble-anim {
    animation: cfaBubbleUp 1.2s ease-in-out infinite;
    transform-box: fill-box;
    transform-origin: 50% 100%;
}
div[data-testid="column"]:has(.cfa-tile-marker):hover .cfa-shine-anim,
div[class*="stColumn"]:has(.cfa-tile-marker):hover .cfa-shine-anim,
.stColumn:has(.cfa-tile-marker):hover .cfa-shine-anim {
    animation: cfaShineSweep .95s ease-in-out infinite;
}

/* 로딩 애니메이션 - Glowing Beaker Liquid */
.cfa-loading-box { padding: 64px 20px; text-align:center; }
.cfa-ring-wrap { position:relative; width:120px; height:120px; margin:0 auto 28px auto; }
.cfa-ring { position:absolute; inset:0; border-radius:50%; border:2px solid rgba(6,182,212,0.4); animation: cfaPulse 2.1s ease-out infinite; }
.cfa-ring.d2 { animation-delay: 1.05s; }
@keyframes cfaPulse { 0%{transform:scale(0.8);opacity:0.8;} 80%{transform:scale(1.3);opacity:0;} 100%{opacity:0;} }
.cfa-core { position:absolute; inset:22px; border-radius:50%; background: conic-gradient(from 0deg,#d946ef,#06b6d4,#3b82f6,#d946ef); animation: cfaSpin 2.5s linear infinite; }
@keyframes cfaSpin { to { transform:rotate(360deg); } }
.cfa-core-inner { position:absolute; inset:10px; border-radius:50%; background: rgba(13,8,30,0.9); backdrop-filter: blur(10px); display:flex; align-items:center; justify-content:center; font-size:28px; border: 1px solid rgba(255,255,255,0.1); }
.cfa-loading-label { font-size:12px; letter-spacing:3px; text-transform:uppercase; color:#a78bfa; font-weight:600; margin-bottom:8px; }
.cfa-loading-msg { font-size:16px; color:#ffffff; font-weight:500; text-shadow: 0 0 10px rgba(6,182,212,0.3); }

/* 대시보드 요약 요소를 위한 카드 */
.cfa-summary { padding: 22px 24px; text-align:left; }
.cfa-summary .label { font-size:11px; letter-spacing:1.6px; text-transform:uppercase; color:#94a3b8; font-weight:600; }
.cfa-summary .value { font-family:'Space Grotesk',sans-serif; font-size:26px; font-weight:700; color:#ffffff; margin-top:6px; }
.cfa-summary.accent { background: linear-gradient(160deg, rgba(6,182,212,0.15), rgba(217,70,239,0.08)); border-color: rgba(6,182,212,0.3); }
.cfa-summary.accent .value { color:#06b6d4; text-shadow: 0 0 15px rgba(6, 182, 212, 0.4); }

/* 처방 테이블 - Dark Glass Design */
.cfa-table-wrap { padding: 4px; overflow-x: auto; }
.cfa-table { width:100%; border-collapse:collapse; font-size:14px; min-width: 600px; }
.cfa-table thead th { text-align:left; padding:14px 18px; font-size:11px; letter-spacing:1.2px; text-transform:uppercase; color:#94a3b8; font-weight:700; border-bottom:1px solid rgba(255,255,255,0.12); }
.cfa-table thead th.num { text-align:right; }
.cfa-table tbody td { padding:13px 18px; color:#cbd5e1; border-bottom:1px solid rgba(255,255,255,0.06); }
.cfa-table tbody td.num { text-align:right; font-variant-numeric: tabular-nums; }
.cfa-table tbody tr:hover td { background: rgba(6, 182, 212, 0.08); }
.cfa-table td.phase { color:#38bdf8; font-weight:700; font-size:12.5px; white-space:nowrap; }
.cfa-table td.name { color:#ffffff; font-weight:600; }
.cfa-table td.fn { color:#94a3b8; font-size:12.5px; }
.cfa-table td.dbtag { font-size:10px; color:#fbbf24; font-weight:600; margin-top:2px; }
.cfa-table tfoot td { padding:16px 18px; font-weight:700; color:#ffffff; border-top:2px solid rgba(6, 182, 212, 0.3); background: rgba(6, 182, 212, 0.05); }

/* 스트림릿 기본 컴포넌트 커스텀 오버라이드 (다크 크리스탈 스타일) */
[data-testid="stExpander"] { background: rgba(13,8,30,0.65)!important; backdrop-filter: blur(25px) saturate(180%); border-radius: 20px!important; border: 1px solid rgba(255,255,255,0.12)!important; }
.stButton>button, [data-testid="stDownloadButton"] button {
    border-radius: 999px!important; background: rgba(255,255,255,0.06)!important;
    backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.12)!important;
    color:#ffffff!important; font-weight:600!important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1); transition: all .25s ease-out;
}
.stButton>button:hover, [data-testid="stDownloadButton"] button:hover { background: rgba(6,182,212,0.15)!important; border-color: rgba(6,182,212,0.5)!important; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(6,182,212,0.25); }
button[kind="primary"] { background: linear-gradient(135deg, #d946ef, #3b82f6)!important; border: 1px solid rgba(255,255,255,0.25)!important; color:#fff!important; box-shadow: 0 0 15px rgba(6,182,212,0.5)!important; }
button[kind="primary"]:hover { filter: brightness(1.15); transform: translateY(-2px); box-shadow: 0 0 22px rgba(6,182,212,0.7)!important; }
div[data-baseweb="input"], div[data-baseweb="base-input"] { background: rgba(13,8,30,0.85)!important; backdrop-filter: blur(12px); border-radius: 14px!important; border: 1px solid rgba(255,255,255,0.12)!important; color:#ffffff!important; }
[data-testid="stFileUploaderDropzone"] { background: rgba(255,255,255,0.03)!important; backdrop-filter: blur(18px) saturate(180%); border-radius: 20px!important; border: 1px dashed rgba(255,255,255,0.2)!important; }
div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li { color: #cbd5e1; }
div[data-testid="stMarkdownContainer"] h1, div[data-testid="stMarkdownContainer"] h2, div[data-testid="stMarkdownContainer"] h3, div[data-testid="stMarkdownContainer"] h4 { color: #ffffff; }

/* 텍스트 렌더링 카드 */
.report-card { background: rgba(13,8,30,0.5); border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); padding: 20px; line-height: 1.6; color:#cbd5e1; }
.report-card h4 { font-family:'Space Grotesk',sans-serif; color: #ffffff; margin-top: 0; }
</style>
""", unsafe_allow_html=True)



# 백그라운드 버블
st.markdown('<div class="cfa-blob cfa-blob1"></div><div class="cfa-blob cfa-blob2"></div><div class="cfa-blob cfa-blob3"></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# 포토리얼리스틱 벡터 아이콘 정의
# ------------------------------------------------------------------
def svg_wrap(inner, gid, c1, c2, cap1="#334155", cap2="#0b0f19"):
    inner_clean = inner.replace("url(#g)", f"url(#g_{gid})") \
                       .replace("url(#bg)", f"url(#bg_{gid})") \
                       .replace("url(#cap)", f"url(#cap_{gid})") \
                       .replace("url(#shine)", f"url(#shine_{gid})") \
                       .replace("url(#floorshadow)", f"url(#floorshadow_{gid})") \
                       .replace("filter=\"url(#soft)\"", f"filter=\"url(#soft_{gid})\"") \
                       .replace("filter: url(#soft)", f"filter: url(#soft_{gid})")
    
    return f'''<svg width="140" height="140" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="bg_{gid}" cx="35%" cy="22%" r="80%">
          <stop offset="0%" stop-color="{c1}" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="{c1}" stop-opacity="0.0"/>
        </radialGradient>
        <linearGradient id="g_{gid}" x1="0.15" y1="0" x2="0.9" y2="1">
          <stop offset="0%" stop-color="{c1}"/><stop offset="55%" stop-color="{c2}"/><stop offset="100%" stop-color="{c2}"/>
        </linearGradient>
        <linearGradient id="cap_{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{cap1}"/><stop offset="100%" stop-color="{cap2}"/>
        </linearGradient>
        <linearGradient id="shine_{gid}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="white" stop-opacity="0.8"/>
          <stop offset="100%" stop-color="white" stop-opacity="0"/>
        </linearGradient>
        <radialGradient id="floorshadow_{gid}" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#05020c" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="#05020c" stop-opacity="0"/>
        </radialGradient>
        <filter id="soft_{gid}" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.4"/>
        </filter>
      </defs>
      <circle cx="70" cy="66" r="64" fill="url(#bg_{gid})"/>
      {inner_clean}
      <ellipse cx="70" cy="126" rx="34" ry="8" fill="url(#floorshadow_{gid})"/>
    </svg>'''

def icon_serum():
    inner = '''
    <path class="cfa-body-anim" d="M52 58 Q52 48 62 48 L78 48 Q88 48 88 58 L88 106 Q88 120 70 120 Q52 120 52 106 Z" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="59" y="16" width="22" height="38" rx="10" fill="url(#cap)"/>
    <ellipse class="cfa-cap-anim" cx="70" cy="16" rx="11" ry="5.5" fill="#a78bfa"/>
    <path class="cfa-shine-anim" d="M56 60 Q54 68 56 106 Q58 116 70 118" stroke="url(#shine)" stroke-width="7" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    <circle class="cfa-bubble-anim" cx="70" cy="90" r="3" fill="rgba(255,255,255,0.6)" style="animation-delay:0s"/>
    <circle class="cfa-bubble-anim" cx="64" cy="98" r="2" fill="rgba(255,255,255,0.5)" style="animation-delay:.2s"/>
    <circle class="cfa-bubble-anim" cx="76" cy="82" r="2.4" fill="rgba(255,255,255,0.5)" style="animation-delay:.4s"/>
    '''
    return svg_wrap(inner, "serum", "#d946ef", "#3b82f6")

def icon_lotion():
    inner = '''
    <rect class="cfa-body-anim" x="44" y="60" width="52" height="60" rx="22" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="55" y="26" width="30" height="38" rx="10" fill="url(#cap)"/>
    <rect class="cfa-cap-anim" x="63" y="10" width="34" height="14" rx="7" fill="#a78bfa"/>
    <circle class="cfa-cap-anim" cx="90" cy="6" r="3.8" fill="#06b6d4"/>
    <path class="cfa-shine-anim" d="M50 64 Q48 74 50 114" stroke="url(#shine)" stroke-width="8" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    <circle class="cfa-bubble-anim" cx="80" cy="98" r="3.8" fill="rgba(255,255,255,0.55)" style="animation-delay:0s"/>
    <circle class="cfa-bubble-anim" cx="86" cy="86" r="2.4" fill="rgba(255,255,255,0.4)" style="animation-delay:.25s"/>
    <circle class="cfa-bubble-anim" cx="72" cy="108" r="2" fill="rgba(255,255,255,0.4)" style="animation-delay:.5s"/>
    '''
    return svg_wrap(inner, "lotion", "#06b6d4", "#3b82f6")

def icon_cream():
    inner = '''
    <rect class="cfa-body-anim" x="30" y="54" width="80" height="64" rx="26" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="24" y="36" width="92" height="24" rx="12" fill="url(#cap)"/>
    <path class="cfa-shine-anim" d="M42 54 Q52 42 62 54 Q72 42 82 54 Q92 42 102 54" stroke="rgba(255,255,255,0.65)" stroke-width="3.8" fill="none" stroke-linecap="round"/>
    <path class="cfa-shine-anim" d="M38 62 Q36 72 38 110" stroke="url(#shine)" stroke-width="9" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    <circle class="cfa-bubble-anim" cx="60" cy="88" r="3" fill="rgba(255,255,255,0.5)" style="animation-delay:.1s"/>
    <circle class="cfa-bubble-anim" cx="90" cy="94" r="2.4" fill="rgba(255,255,255,0.45)" style="animation-delay:.35s"/>
    '''
    return svg_wrap(inner, "cream", "#d946ef", "#06b6d4")

def icon_toner():
    inner = '''
    <rect class="cfa-body-anim" x="55" y="62" width="30" height="56" rx="13" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="61" y="30" width="18" height="34" rx="5" fill="url(#cap)"/>
    <rect class="cfa-cap-anim" x="70" y="18" width="30" height="14" rx="7" fill="#a78bfa"/>
    <rect class="cfa-cap-anim" x="87" y="8" width="9" height="16" rx="3.4" fill="#a78bfa"/>
    <circle class="cfa-bubble-anim" cx="107" cy="8" r="2" fill="#06b6d4" opacity="0.9" style="animation-delay:0s"/>
    <circle class="cfa-bubble-anim" cx="114" cy="16" r="1.5" fill="#06b6d4" opacity="0.7" style="animation-delay:.2s"/>
    <circle class="cfa-bubble-anim" cx="103" cy="22" r="1.2" fill="#06b6d4" opacity="0.6" style="animation-delay:.4s"/>
    <path class="cfa-shine-anim" d="M60 66 Q58 76 60 108" stroke="url(#shine)" stroke-width="5.5" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    '''
    return svg_wrap(inner, "toner", "#06b6d4", "#d946ef")

def icon_ampoule():
    inner = '''
    <path class="cfa-body-anim" d="M57 46 L83 46 L83 63 L91 112 Q91 118 70 118 Q49 118 49 112 L57 63 Z" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="57" y="18" width="26" height="30" rx="5" fill="url(#cap)"/>
    <circle class="cfa-cap-anim" cx="70" cy="30" r="3.8" fill="#c7d2fe"/>
    <line x1="54" y1="80" x2="60" y2="80" stroke="rgba(255,255,255,0.65)" stroke-width="2"/>
    <line x1="53" y1="93" x2="60" y2="93" stroke="rgba(255,255,255,0.65)" stroke-width="2"/>
    <line x1="52" y1="106" x2="60" y2="106" stroke="rgba(255,255,255,0.65)" stroke-width="2"/>
    <path class="cfa-shine-anim" d="M61 50 Q59 60 61 108" stroke="url(#shine)" stroke-width="6.5" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    <circle class="cfa-bubble-anim" cx="75" cy="72" r="2.6" fill="rgba(255,255,255,0.5)" style="animation-delay:.15s"/>
    '''
    return svg_wrap(inner, "ampoule", "#3b82f6", "#06b6d4")

def icon_cleanser():
    inner = '''
    <rect class="cfa-body-anim" x="44" y="62" width="52" height="56" rx="20" fill="url(#g)"/>
    <rect class="cfa-cap-anim" x="55" y="30" width="30" height="34" rx="10" fill="url(#cap)"/>
    <rect class="cfa-cap-anim" x="63" y="14" width="34" height="14" rx="7" fill="#a78bfa"/>
    <circle class="cfa-bubble-anim" cx="56" cy="96" r="5.6" fill="rgba(255,255,255,0.6)" style="animation-delay:0s"/>
    <circle class="cfa-bubble-anim" cx="72" cy="104" r="3.8" fill="rgba(255,255,255,0.5)" style="animation-delay:.25s"/>
    <circle class="cfa-bubble-anim" cx="80" cy="92" r="2.9" fill="rgba(255,255,255,0.45)" style="animation-delay:.5s"/>
    <path class="cfa-shine-anim" d="M50 66 Q48 76 50 112" stroke="url(#shine)" stroke-width="7.5" fill="none" stroke-linecap="round" filter="url(#soft)"/>
    '''
    return svg_wrap(inner, "cleanser", "#d946ef", "#3b82f6")

FORMULATION_TYPES = [
    {"id": "serum", "label": "세럼", "svg": icon_serum()},
    {"id": "lotion", "label": "로션", "svg": icon_lotion()},
    {"id": "cream", "label": "크림", "svg": icon_cream()},
    {"id": "toner", "label": "토너", "svg": icon_toner()},
    {"id": "ampoule", "label": "앰플", "svg": icon_ampoule()},
    {"id": "cleanser", "label": "클렌저", "svg": icon_cleanser()},
]

PHASE_PALETTE = ["#2563EB", "#6366F1", "#0EA5E9", "#818CF8", "#38BDF8", "#93C5FD"]



# ------------------------------------------------------------------
# 핵심 AI 유틸 함수
# ------------------------------------------------------------------
def call_gemini_with_retry(api_func, *args, max_attempts=5, initial_delay=2.0, **kwargs):
    import time
    delay = initial_delay
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            err_msg = str(e)
            
            # Check if it's an API Key or client configuration issue (these should fail immediately)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "400" in err_msg:
                raise e
            
            # If it's a transient server issue, retry
            is_transient = (
                "503" in err_msg or 
                "unavailable" in err_msg.lower() or 
                "timeout" in err_msg.lower() or 
                "connection" in err_msg.lower() or 
                "500" in err_msg or
                "429" in err_msg or
                "quota" in err_msg.lower() or
                "limit" in err_msg.lower()
            )
            
            if is_transient and attempt < max_attempts:
                # Show a warning in streamlit
                st.warning(f"⚠️ Gemini API 서버가 혼잡하여 {delay:.1f}초 후 재시도합니다... (시도 {attempt}/{max_attempts})")
                time.sleep(delay)
                delay *= 1.5  # moderate backoff
            else:
                raise e
    if last_exception:
        raise last_exception

def validate_api_key(api_key: str, model_name: str = "gemini-2.5-flash") -> tuple[bool, str]:
    """Gemini API 키의 유효성을 검사합니다."""
    if not api_key:
        return False, "API 키가 비어 있습니다."
    try:
        client = genai.Client(api_key=api_key)
        call_gemini_with_retry(
            client.models.generate_content,
            model=model_name,
            contents="Hello",
            config=types.GenerateContentConfig(max_output_tokens=1),
            max_attempts=3
        )
        return True, ""
    except Exception as e:
        err_msg = str(e)
        if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "400" in err_msg:
            return False, "올바르지 않은 API 키입니다. Google AI Studio에서 발급받은 키인지 확인해 주세요."
        elif "quota" in err_msg.lower() or "limit" in err_msg.lower() or "429" in err_msg:
            return False, "API 호출 할당량이 초과되었습니다."
        elif "503" in err_msg or "unavailable" in err_msg.lower() or "timeout" in err_msg.lower() or "connection" in err_msg.lower() or "500" in err_msg:
            return True, "warning:Gemini API 서버가 일시적으로 불안정합니다 (503 Unavailable 등). 키는 올바른 것으로 추정되므로 일단 진행합니다."
        else:
            return False, f"API 키 검증 중 오류가 발생했습니다: {err_msg}"

def get_client():
    return genai.Client(api_key=st.session_state.api_key)

def compress_image_bytes(image_bytes, max_size=1000):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=82)
    return out.getvalue()

def vision_extract_ingredients_from_crop(crop_img):
    buf = io.BytesIO()
    crop_img.convert("RGB").save(buf, format="JPEG", quality=88)
    image_bytes = compress_image_bytes(buf.getvalue())
    client = get_client()
    prompt = (
        "이 이미지는 화장품 라벨에서 성분표 부분만 사람이 직접 잘라낸 것임. "
        "여기 보이는 전성분(INCI 포함)을 빠짐없이 한국어 원료명으로 추출해서 쉼표로 구분된 목록으로만 출력해. "
        "다른 설명은 넣지 마."
    )
    resp = call_gemini_with_retry(
        client.models.generate_content,
        model=st.session_state.model_name,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
    )
    return resp.text.strip()

def merge_extracted_into_db(ingredient_text):
    """라벨에서 추출된 성분 중 DB에 없는 원료를 자동으로 원료 단가 DB에 추가함"""
    if not ingredient_text:
        return 0
    raw_names = re.split(r"[,\n·、]", ingredient_text)
    existing_names = set(st.session_state.db["name"].tolist())
    new_rows = []
    for raw in raw_names:
        name = re.sub(r"\(.*?\)", "", raw).strip()
        name = name.strip("·-• ").strip()
        if not name or len(name) < 2:
            continue
        if name not in existing_names:
            new_rows.append({
                "name": name, "inci": "", "unit_cost": 15,
                "supplier": "라벨추출 - 근거 없음(추정단가)",
            })
            existing_names.add(name)
    if new_rows:
        st.session_state.db = pd.concat(
            [st.session_state.db, pd.DataFrame(new_rows)], ignore_index=True
        )
        if "db_editor" in st.session_state:
            del st.session_state["db_editor"]
    return len(new_rows)

from pydantic import BaseModel, Field

class IngredientItem(BaseModel):
    phase: str = Field(description="배합 상. A상 (수상), B상 (유상), C상 (첨가) 등")
    name: str = Field(description="원료명 (한글)")
    function: str = Field(description="원료의 효능 및 기능")
    ratio: float = Field(description="배합비 상대적 비율 수치 (양수)")

def generate_formulation(ftype, db_df, existing_ingredients=None):
    client = get_client()
    db_names = db_df["name"].tolist()

    if existing_ingredients:
        base_instruction = f"""아래는 사용자가 직접 입력하거나 라벨에서 추출한 기존 제품의 전성분 목록입니다. 이 성분들을 처방의 기본 뼈대로 삼아 100% 반영하여 최적화해야 합니다:
검출 성분: {existing_ingredients}

★ [필수 요구사항] ★
1. 위 '검출 성분' 목록에 나열된 모든 성분들을 100% 빠짐없이 최종 배합 처방(Formulation)에 포함해야 합니다. 임의로 제외하거나 무시해서는 안 됩니다.
2. 검출 성분 중 보유 원료 DB에 있는 성분과 이름이 유사하거나 동의어인 경우(예: 'Water' -> '정제수', 'Sodium Hyaluronate' -> '히알루론산'), 단가 매칭을 위해 반드시 보유 원료 DB의 이름으로 매칭하여 배합 처방에 사용해 주세요.
3. 검출 성분 중 보유 원료 DB에 전혀 등록되어 있지 않은 성분이라도, 절대 누락하지 말고 배합 처방에 새 원료명 그대로 추가하고 그 기능을 한국어로 성질에 맞게 유추하여 작성하세요.
4. 배합 비율(ratio)은 제형 특성에 맞추어 자유롭게 배분하되, 전체 원료 목록 자체는 검출된 성분을 전원 유지해야 합니다."""
    else:
        base_instruction = "기존 라벨 정보 없음. 아래 보유 원료 DB를 참고해서 신규 배합으로 설계해라."

    prompt = f"""너는 화장품 처방 개발 전문가임. 아래 조건으로 화장품 배합(Formulation)을 설계해줘.

제형 종류: {ftype['label']}

{base_instruction}

보유 원료 DB 목록(단가 매칭용, 참고):
{', '.join(db_names)}
"""
    resp = call_gemini_with_retry(
        client.models.generate_content,
        model=st.session_state.model_name,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[IngredientItem]
        )
    )
    return json.loads(resp.text)

def refine_formulation(ftype, db_df, current_raw_formulation, feedback_text):
    """기존 배합표와 사용자의 피드백을 기반으로 배합 비율을 재조정"""
    client = get_client()
    db_names = db_df["name"].tolist()
    
    prompt = f"""너는 화장품 처방 개발 전문가임. 기존에 설계된 배합표에 사용자의 피드백을 반영하여 성분 및 배합 비율을 커스텀 수정해줘.

제형 종류: {ftype['label']}

기존 배합표 데이터 (JSON):
{json.dumps(current_raw_formulation, ensure_ascii=False, indent=2)}

사용자 피드백 (요구사항):
"{feedback_text}"

보유 원료 DB 목록(참고):
{', '.join(db_names)}
"""
    resp = call_gemini_with_retry(
        client.models.generate_content,
        model=st.session_state.model_name,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[IngredientItem]
        )
    )
    return json.loads(resp.text)

# 제조 공정 및 분석 리포트 생성기 함수 제거됨 (요구사항 반영)

def normalize_and_cost(raw_items, db_df):
    total = sum(float(i["ratio"]) for i in raw_items)
    db_map = {row["name"]: row["unit_cost"] for _, row in db_df.iterrows()}
    rows = []
    for i in raw_items:
        pct = round(float(i["ratio"]) / total * 100, 2)
        weight = round(pct / 100 * 1000, 2)
        matched = db_map.get(i["name"])
        estimated = matched is None
        unit_cost = matched if matched is not None else 15
        total_cost = round(weight * unit_cost)
        
        # Phase normalization
        p_raw = i["phase"]
        if "수상" in p_raw or "A" in p_raw or "a" in p_raw:
            phase_clean = "수상"
        elif "유상" in p_raw or "B" in p_raw or "b" in p_raw:
            phase_clean = "유상"
        elif "첨가" in p_raw or "C" in p_raw or "c" in p_raw:
            phase_clean = "첨가"
        else:
            phase_clean = p_raw

        rows.append({
            "상": phase_clean, "원료명": i["name"], "기능": i["function"],
            "배합비(%)": pct, "중량(g)": weight,
            "단가(원/g)": unit_cost, "총원가(원)": total_cost,
            "DB매칭": "DB 미등록(추정단가)" if estimated else "",
        })
    diff = round(100 - sum(r["배합비(%)"] for r in rows), 2)
    if abs(diff) >= 0.01:
        max_idx = max(range(len(rows)), key=lambda k: rows[k]["배합비(%)"])
        rows[max_idx]["배합비(%)"] = round(rows[max_idx]["배합비(%)"] + diff, 2)
        rows[max_idx]["중량(g)"] = round(rows[max_idx]["배합비(%)"] / 100 * 1000, 2)
        rows[max_idx]["총원가(원)"] = round(rows[max_idx]["중량(g)"] * rows[max_idx]["단가(원/g)"])
    return pd.DataFrame(rows)

# ------------------------------------------------------------------
# HTML 기반 시각화 렌더링
# ------------------------------------------------------------------
def render_table_html(df):
    rows_html = ""
    prev_phase = None
    for _, r in df.iterrows():
        phase_cell = r["상"] if r["상"] != prev_phase else ""
        prev_phase = r["상"]
        db_tag = f'<div class="dbtag">⚠️ {r["DB매칭"]}</div>' if r["DB매칭"] else ""
        rows_html += f'''<tr>
            <td class="phase">{phase_cell}</td>
            <td class="name">{r["원료명"]}{db_tag}</td>
            <td class="fn">{r["기능"]}</td>
            <td class="num">{r["배합비(%)"]:.2f}%</td>
            <td class="num">{r["중량(g)"]:.2f}g</td>
            <td class="num">{r["단가(원/g)"]:,.0f}</td>
            <td class="num">{r["총원가(원)"]:,.0f}</td>
        </tr>'''
    total_cost = df["총원가(원)"].sum()
    return f'''
    <div class="cfa-table-wrap">
    <table class="cfa-table">
      <thead><tr>
        <th>상</th><th>원료명</th><th>기능</th>
        <th class="num">배합비(%)</th><th class="num">중량(g)</th><th class="num">단가(원/g)</th><th class="num">총원가(원)</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
      <tfoot><tr>
        <td colspan="3">합계</td>
        <td class="num">100.00%</td><td class="num">1,000.00g</td><td></td>
        <td class="num">{total_cost:,.0f}원</td>
      </tr></tfoot>
    </table>
    </div>'''

def polar(cx, cy, r, angle_deg):
    a = math.radians(angle_deg)
    return cx + r*math.sin(a), cy - r*math.cos(a)

def get_phase_color(phase_name):
    # 수상-red, 유상-green, 첨가-blue
    phase_colors_map = {
        "수상": "#EF4444",
        "유상": "#22C55E",
        "첨가": "#3B82F6",
        "A상": "#EF4444",
        "B상": "#22C55E",
        "C상": "#3B82F6",
        "A": "#EF4444",
        "B": "#22C55E",
        "C": "#3B82F6"
    }
    for key, val in phase_colors_map.items():
        if key in phase_name:
            return val
    return "#94A3B8" # fallback grey

def render_donut_html(df):
    cx, cy, r_outer, r_inner = 220, 220, 190, 105
    phases = df["상"].unique().tolist()
    phase_color = {p: get_phase_color(p) for p in phases}

    segs = ""
    labels = ""
    start_angle = 0
    for _, r in df.iterrows():
        sweep = r["배합비(%)"] / 100 * 360
        end_angle = start_angle + sweep
        large = 1 if sweep > 180 else 0
        x1, y1 = polar(cx, cy, r_outer, start_angle)
        x2, y2 = polar(cx, cy, r_outer, end_angle)
        xi1, yi1 = polar(cx, cy, r_inner, end_angle)
        xi2, yi2 = polar(cx, cy, r_inner, start_angle)
        color = phase_color[r["상"]]
        tip = f"{r['원료명']} | 배합비 {r['배합비(%)']:.2f}% | 중량 {r['중량(g)']:.2f}g | 단가 {r['단가(원/g)']:,.0f}원/g | 총원가 {r['총원가(원)']:,.0f}원"
        d = f"M{x1:.2f},{y1:.2f} A{r_outer},{r_outer} 0 {large} 1 {x2:.2f},{y2:.2f} L{xi1:.2f},{yi1:.2f} A{r_inner},{r_inner} 0 {large} 0 {xi2:.2f},{yi2:.2f} Z"
        segs += f'<path d="{d}" fill="{color}" opacity="0.88" stroke="white" stroke-width="1.5" class="cfa-seg" onmousemove="showTip(event, \'{tip}\')" onmouseleave="hideTip()"></path>'
        if sweep > 12:
            mid = (start_angle + end_angle) / 2
            lx, ly = polar(cx, cy, (r_outer+r_inner)/2, mid)
            labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="white" pointer-events="none" font-family="Inter,sans-serif">{r["원료명"]}</text>'
        start_angle = end_angle

    total_cost = df["총원가(원)"].sum()
    legend_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-right:16px;margin-bottom:6px;">'
        f'<span style="width:10px;height:10px;border-radius:3px;background:{phase_color[p]};display:inline-block;"></span>'
        f'<span style="font-size:11.5px;color:#cbd5e1;font-weight:600;">{p}</span></div>'
        for p in phases
    )

    return f'''
    <div id="donut-viewport" style="width:100%; height:520px; overflow:hidden; position:relative; touch-action:none; cursor:grab; border-radius:16px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);">
      <div id="donut-zoomable" style="position:absolute; left:0; top:0; width:100%; height:100%;
           display:flex; align-items:center; justify-content:center; gap:24px; flex-wrap:wrap;
           transform-origin:0 0; will-change:transform; font-family:Inter,sans-serif;">
        <svg viewBox="0 0 440 440" width="410" height="410">
          {segs}
          {labels}
          <text x="220" y="210" text-anchor="middle" font-size="11" fill="#a78bfa" font-family="Inter,sans-serif" font-weight="600">TOTAL COST</text>
          <text x="220" y="238" text-anchor="middle" font-size="20" font-weight="700" fill="#ffffff" font-family="Space Grotesk,sans-serif">{total_cost:,.0f}원</text>
        </svg>
        <div style="display:flex; flex-wrap:wrap; max-width:200px;">{legend_items}</div>
      </div>
      <div id="donut-tooltip" style="position:absolute; display:none; pointer-events:none;
        background:rgba(15,23,42,0.95); color:#fff; padding:10px 14px; border-radius:12px;
        font-size:12px; white-space:nowrap; z-index:10; box-shadow:0 10px 25px rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.15);"></div>
    </div>
    <div style="text-align:center; font-size:11px; color:#94a3b8; margin-top:8px; font-weight:500;">
      🔍 마우스 휠 = 마우스 위치 기준 확대/축소 · 드래그 = 위치 이동 · 더블클릭 = 뷰 리셋
    </div>
    <style>
      .cfa-seg {{ transition: opacity .18s, filter .18s; cursor:pointer; }}
      .cfa-seg:hover {{ opacity:1 !important; filter: drop-shadow(0 0 10px rgba(6,182,212,0.65)); }}
    </style>
    <script>
      function showTip(evt, text) {{
        const viewport = document.getElementById('donut-viewport');
        const tip = document.getElementById('donut-tooltip');
        const rect = viewport.getBoundingClientRect();
        tip.innerText = text;
        tip.style.left = (evt.clientX - rect.left + 15) + 'px';
        tip.style.top = (evt.clientY - rect.top + 10) + 'px';
        tip.style.display = 'block';
      }}
      function hideTip() {{ document.getElementById('donut-tooltip').style.display = 'none'; }}

      (function() {{
        let scale = 1, tx = 0, ty = 0;
        let dragging = false, lastX = 0, lastY = 0;
        const viewport = document.getElementById('donut-viewport');
        const el = document.getElementById('donut-zoomable');

        function apply() {{ el.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')'; }}

        viewport.addEventListener('wheel', function(e) {{
          e.preventDefault();
          const rect = viewport.getBoundingClientRect();
          const mx = e.clientX - rect.left;
          const my = e.clientY - rect.top;
          const factor = e.deltaY < 0 ? 1.15 : (1/1.15);
          const newScale = Math.min(Math.max(scale * factor, 1), 5);
          tx = mx - (mx - tx) * (newScale / scale);
          ty = my - (my - ty) * (newScale / scale);
          scale = newScale;
          apply();
        }}, {{ passive: false }});

        viewport.addEventListener('mousedown', function(e) {{
          if (e.target.id === 'donut-viewport' || e.target.tagName === 'svg' || e.target.tagName === 'path') {{
            dragging = true; lastX = e.clientX; lastY = e.clientY;
            viewport.style.cursor = 'grabbing';
          }}
        }});
        window.addEventListener('mousemove', function(e) {{
          if (!dragging) return;
          tx += (e.clientX - lastX); ty += (e.clientY - lastY);
          lastX = e.clientX; lastY = e.clientY;
          apply();
        }});
        window.addEventListener('mouseup', function() {{
          dragging = false; viewport.style.cursor = 'grab';
        }});
        viewport.addEventListener('dblclick', function() {{
          scale = 1; tx = 0; ty = 0; apply();
        }});
      }})();
    </script>
    '''

# ------------------------------------------------------------------
# 모달 다이알로그
# ------------------------------------------------------------------
@st.dialog("이미지 확대보기", width="large")
def zoom_dialog(img, caption):
    st.image(img, use_container_width=True, caption=caption)

# ------------------------------------------------------------------
# 헤더 및 레이아웃
# ------------------------------------------------------------------
hcol1, hcol2 = st.columns([4, 2])
with hcol1:
    st.markdown('''
    <div class="cfa-header-row">
      <div class="cfa-brand">
        <div class="badge">🧪</div>
        <div>
          <h1>Cosmetics Formulation AI</h1>
          <p>AI-Driven Formulation & Cost Engineering</p>
        </div>
      </div>
    </div>
    ''', unsafe_allow_html=True)
with hcol2:
    if st.session_state.step >= 1:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🏠 처음으로", use_container_width=True, key="header_reset_button"):
                st.session_state.step = 1
                st.session_state.ftype = None
                st.session_state.label_ingredients = None
                st.session_state.label_original = None
                st.session_state.label_crop = None
                st.session_state.raw_formulation = None
                st.session_state.formulation = None
                
                # Deleting widget state keys
                for k in ["ingredients_text_editor", "db_editor", "label_file_uploader"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        with btn_col2:
            if st.button("🔑 Key 변경", use_container_width=True, key="header_change_api_button"):
                st.session_state.api_key = ""
                st.session_state.step = 0
                st.session_state.ftype = None
                st.session_state.label_ingredients = None
                st.session_state.label_original = None
                st.session_state.label_crop = None
                st.session_state.raw_formulation = None
                st.session_state.formulation = None
                
                # Deleting widget state keys
                for k in ["ingredients_text_editor", "db_editor", "label_file_uploader"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 상단 진행 단계 인디케이터 (Stepper)
# ------------------------------------------------------------------
if st.session_state.step > 0:
    s1_class = "active" if st.session_state.step == 1 else "done"
    s2_class = "active" if st.session_state.step == 2 else ("done" if st.session_state.step > 2 else "")
    s3_class = "active" if st.session_state.step == 3 else ""
    
    st.markdown(f'''
    <div class="cfa-stepper">
      <div class="cfa-step {s1_class}">1. 제형 종류 선택</div>
      <div class="cfa-step-arrow">→</div>
      <div class="cfa-step {s2_class}">2. 라벨 영역 지정 & 설계</div>
      <div class="cfa-step-arrow">→</div>
      <div class="cfa-step {s3_class}">3. 최적 처방 리포트</div>
    </div>
    ''', unsafe_allow_html=True)

# ------------------------------------------------------------------
# DB 관리 섹션 (CSV Import/Export 추가로 기능 고도화)
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# 설정 및 DB 관리 섹션 (종합 컨트롤 패널)
# ------------------------------------------------------------------
if st.session_state.step >= 1:
    with st.expander("⚙️ 시스템 설정 및 원료 데이터베이스 관리"):
        st.markdown("### 🔑 Gemini API 설정")
        col_api1, col_api2 = st.columns(2)
        with col_api1:
            settings_key = st.text_input(
                "Gemini API Key", 
                value=st.session_state.api_key, 
                type="password", 
                placeholder="AIzaSy... 입력",
                help="설정된 API 키입니다. 다른 키로 변경하려면 입력해 주세요."
            )
            if settings_key != st.session_state.api_key:
                cleaned_settings_key = settings_key.strip().strip('\"\'')
                if cleaned_settings_key:
                    with st.spinner("Gemini API 키 검증 중..."):
                        is_valid, err_msg = validate_api_key(cleaned_settings_key, st.session_state.model_name)
                    if is_valid:
                        st.session_state.api_key = cleaned_settings_key
                        if err_msg.startswith("warning:"):
                            st.session_state.api_key_warning = err_msg.replace("warning:", "")
                        else:
                            st.success("API 키가 변경되었습니다!")
                        st.rerun()
                    else:
                        st.error(f"❌ API 키 검증 실패: {err_msg}")
                else:
                    st.error("API 키를 입력해 주세요.")
        with col_api2:
            model_options = ["gemini-2.5-flash", "gemini-2.5-pro"]
            model_index = 0
            if st.session_state.model_name in model_options:
                model_index = model_options.index(st.session_state.model_name)
            settings_model = st.selectbox(
                "사용할 Gemini AI 모델", 
                model_options, 
                index=model_index
            )
            if settings_model != st.session_state.model_name:
                st.session_state.model_name = settings_model
                st.rerun()
                
        st.markdown("---")
        st.markdown("### 📁 원료 단가 데이터베이스 관리 (Raw Material DB)")
        st.caption("라벨에서 추출된 원료 중 신규 원료는 단가 15원/g의 임시 원료로 자동 추가됩니다.")
        
        # CSV 내보내기 및 가져오기 UI
        db_cols = st.columns([1, 1, 2])
        with db_cols[0]:
            csv_buf = io.StringIO()
            st.session_state.db.to_csv(csv_buf, index=False)
            st.download_button(
                "📥 DB를 CSV로 내보내기",
                data=csv_buf.getvalue(),
                file_name="cosmetics_raw_db.csv",
                mime="text/csv",
                use_container_width=True
            )
        with db_cols[1]:
            uploaded_db = st.file_uploader("📤 CSV 가져오기 (컬럼: name, inci, unit_cost, supplier)", type=["csv"], label_visibility="collapsed")
            if uploaded_db is not None:
                try:
                    imported_df = pd.read_csv(uploaded_db)
                    required_cols = {"name", "inci", "unit_cost", "supplier"}
                    if required_cols.issubset(imported_df.columns):
                        st.session_state.db = imported_df
                        st.success("데이터베이스를 성공적으로 업데이트했습니다!")
                        st.rerun()
                    else:
                        st.error("CSV 형식이 일치하지 않습니다. name, inci, unit_cost, supplier 컬럼이 필요합니다.")
                except Exception as e:
                    st.error(f"CSV 파싱 중 에러 발생: {e}")
                    
        edited = st.data_editor(
            st.session_state.db, num_rows="dynamic", use_container_width=True, key="db_editor",
            column_config={
                "name": "원료명", "inci": "INCI명",
                "unit_cost": st.column_config.NumberColumn("단가(원/g)", min_value=0),
                "supplier": "공급사",
            },
        )
        if not edited.equals(st.session_state.db):
            st.session_state.db = edited
            if st.session_state.raw_formulation is not None:
                st.session_state.formulation = normalize_and_cost(st.session_state.raw_formulation, edited)
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# STEP 0: API Key 설정
# ------------------------------------------------------------------
if st.session_state.step == 0:
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown('<div class="cfa-step0-marker"></div>', unsafe_allow_html=True)
        st.markdown("### 🔑 Gemini API 키 설정")
        st.caption("이 웹앱은 배합 설계 및 이미지 분석에 Google Gemini API를 사용합니다.")
        st.markdown("[👉 Google AI Studio에서 무료 API 키 발급받기](https://aistudio.google.com/apikey)")
        
        # 이전 실행 시 오류가 발생하여 되돌아온 경우 메시지 표시
        if "api_key_error_msg" in st.session_state and st.session_state.api_key_error_msg:
            st.error(st.session_state.api_key_error_msg)
            # 한 번 표시한 후 세션 상태에서 삭제하여 중복 방지
            del st.session_state.api_key_error_msg
            
        key_input = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy... 로 시작하는 키를 입력해 주세요")
        model_input = st.text_input("사용할 Gemini 모델명", value=st.session_state.model_name)
        
        st.caption("※ 로컬 환경 변수 `GEMINI_API_KEY`를 설정하거나 Streamlit Secrets를 구성하면 이 화면을 건너뛸 수 있습니다.")
        if st.button("시작하기 →", use_container_width=True, type="primary"):
            cleaned_key = key_input.strip().strip('\"\'')
            if cleaned_key:
                selected_model = model_input.strip() or "gemini-2.5-flash"
                with st.spinner("Gemini API 키 검증 중..."):
                    is_valid, err_msg = validate_api_key(cleaned_key, selected_model)
                if is_valid:
                    st.session_state.api_key = cleaned_key
                    st.session_state.model_name = selected_model
                    st.session_state.step = 1
                    if err_msg.startswith("warning:"):
                        st.session_state.api_key_warning = err_msg.replace("warning:", "")
                    st.rerun()
                else:
                    st.error(f"❌ API 키 검증 실패: {err_msg}")
            else:
                st.error("올바른 API 키를 입력해 주세요")

# ------------------------------------------------------------------
# STEP 1: 제형 선택
# ------------------------------------------------------------------
elif st.session_state.step == 1:
    st.caption("STEP 1")
    st.subheader("설계하고자 하는 화장품 제형을 선택해 주세요")
    
    if "api_key_warning" in st.session_state and st.session_state.api_key_warning:
        st.warning(st.session_state.api_key_warning)
        del st.session_state.api_key_warning
    
    # 2 rows of 3 columns
    for row_idx, chunk in enumerate([FORMULATION_TYPES[:3], FORMULATION_TYPES[3:]]):
        cols = st.columns(3)
        for i, t in enumerate(chunk):
            with cols[i]:
                st.markdown(f'''
                <div class="liquid-glass cfa-tile cfa-tile-marker">
                  <div class="cfa-icon-wrap">{t["svg"]}</div>
                  <div class="cfa-name-pill">{t["label"]}<span class="cfa-liquid-drop2"></span></div>
                </div>
                ''', unsafe_allow_html=True)
                if st.button(t["label"], key=f"btn_{t['id']}", use_container_width=True):
                    st.session_state.ftype = t
                    st.session_state.step = 2
                    st.rerun()

# ------------------------------------------------------------------
# STEP 2: 라벨 크롭 및 AI 처방 설계
# ------------------------------------------------------------------
elif st.session_state.step == 2:
    ftype = st.session_state.ftype
    st.caption("STEP 2")
    st.subheader(f"✨ {ftype['label']} 설계 조건 설정")
    
    col_l, col_r = st.columns([1.2, 1])
    
    with col_l:
        st.markdown('<div class="cfa-step2-marker"></div>', unsafe_allow_html=True)
        st.markdown("#### 1. 기존 제품 라벨 이미지 업로드 (선택)")
        st.write("이미지의 성분표 부분만 드래그하여 정확하게 지정하면, AI가 성분을 완벽히 파악해 맞춤 배합에 반영합니다.")
        uploaded = st.file_uploader("라벨 이미지 업로드 (10MB 이하)", type=["png", "jpg", "jpeg"], key="label_file_uploader")
        cropped_img = None

        if uploaded is not None:
            if uploaded.size > 10 * 1024 * 1024:
                st.error("파일이 너무 큽니다. 10MB 이하의 이미지를 업로드해 주세요.")
            else:
                orig_img = Image.open(uploaded).convert("RGB")
                st.caption("아래 박스의 모서리를 끌어 성분표 텍스트 영역만 알맞게 지정해 주세요.")
                cropped_img = st_cropper(
                    orig_img, realtime_update=True, box_color="#2563EB",
                    aspect_ratio=None, return_type="image"
                )
                st.session_state.label_original = orig_img
        
    with col_r:
        st.markdown('<div class="cfa-step2-marker"></div>', unsafe_allow_html=True)
        st.markdown("#### 2. 배합 설계 시작")
        if cropped_img is not None:
            st.write("선택된 성분표 크롭 영역:")
            st.image(cropped_img, width=240)
            st.session_state.label_crop = cropped_img
            
            # Button to trigger OCR
            if st.button("🔍 지정 영역에서 성분 텍스트 추출", use_container_width=True):
                with st.spinner("성분표 텍스트 분석 중..."):
                    try:
                        extracted = vision_extract_ingredients_from_crop(cropped_img)
                        st.session_state.label_ingredients = extracted
                        st.session_state.ingredients_text_editor = extracted  # Update text_area widget state value directly
                        
                        # 즉시 원료 단가 데이터베이스에도 누락된 원료 병합
                        merge_extracted_into_db(extracted)
                        
                        st.success("성분이 추출되어 아래 텍스트 상자 및 원료 DB에 반영되었습니다!")
                        st.rerun()
                    except Exception as e:
                        import traceback
                        err_str = str(e)
                        if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "400" in err_str:
                            st.session_state.api_key = ""
                            st.session_state.step = 0
                            st.session_state.api_key_error_msg = "❌ 입력된 Gemini API 키가 올바르지 않거나 만료되었습니다. API 키를 재설정해 주세요."
                            st.rerun()
                        else:
                            st.error(f"성분 추출에 실패했습니다: {e}")
                            with st.expander("🛠️ 상세 에러 로그 (디버깅용)"):
                                st.code(traceback.format_exc())
        else:
            st.write("업로드된 라벨이 없습니다. 원료 DB에 있는 성분들을 활용하여 **인공지능의 신규 배합 설계**를 바로 시작합니다.")
            
        st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 테스트용 샘플 라벨 이미지 및 텍스트 제공 (확인 유틸리티)
    # ------------------------------------------------------------------
    with st.expander("🧪 테스트용 샘플 라벨 정보 (이미지가 없는 경우 활용)"):
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            sample_path = "sample_label.png"
            if os.path.exists(sample_path):
                st.image(sample_path, caption="샘플 라벨 이미지 (마우스 우클릭 다운로드 가능)", width=180)
            else:
                st.info("sample_label.png 파일이 프로젝트 폴더 내에 존재하지 않습니다.")
        with col_s2:
            st.write("📋 **추출 테스트용 성분 텍스트 (복사 가능):**")
            st.code("정제수, 글리세린, 부틸렌글라이콜, 나이아신아마이드, 다이메티콘, 잔탄검, 히알루론산, 스쿠알란, 페녹시에탄올", language="text")
            st.caption("위 성분 텍스트를 복사하여 아래의 '반영할 전성분 리스트'에 직접 붙여넣거나, 라벨 이미지를 업로드하고 크롭하여 텍스트를 추출해 보세요.")

    # ------------------------------------------------------------------
    # 라벨 이미지 영역 지정 시 text 보여주고 수정 가능하게 (수정 가능 성분 텍스트 영역)
    # ------------------------------------------------------------------
    with st.container():
        st.markdown('<div class="cfa-step2-full-marker"></div>', unsafe_allow_html=True)
        st.markdown("#### 📝 반영할 전성분 리스트 (직접 수정 · 추가 · 삭제 가능)")
        st.write("라벨 이미지에서 성분을 추출하거나 직접 입력하면 여기에 표시되며, 자유롭게 성분을 추가하거나 삭제하실 수 있습니다.")
        
        ingredients_txt = st.text_area(
            "배합의 기본 뼈대가 될 성분 리스트 (쉼표로 구분)",
            value=st.session_state.label_ingredients or "",
            placeholder="예: 정제수, 글리세린, 부틸렌글라이콜, 나이아신아마이드 (또는 라벨 이미지를 올려 추출해 주세요)",
            height=120,
            label_visibility="collapsed",
            key="ingredients_text_editor"
        )
        st.session_state.label_ingredients = ingredients_txt  # Sync back to state
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # "AI 배합 실행" 버튼 (번개 표시 대신 AI 관련 🤖 아이콘, 화장품 관련 로딩 🧴 애니메이션)
        if st.button("🤖 AI 배합 실행", type="primary", use_container_width=True):
            placeholder = st.empty()
            placeholder.markdown('''
            <div class="liquid-glass cfa-loading-box">
              <div class="cfa-ring-wrap">
                <div class="cfa-ring"></div><div class="cfa-ring d2"></div>
                <div class="cfa-core"></div><div class="cfa-core-inner">🧴</div>
              </div>
              <div class="cfa-loading-label">Gemini AI · SKINCARE FORMULATION</div>
              <div class="cfa-loading-msg">원료 상용성 분석 및 맞춤형 스킨케어 배합 구성 중...</div>
            </div>
            ''', unsafe_allow_html=True)
            try:
                # 최종 수동 편집된 원료가 있으면 DB에 다시 병합
                if ingredients_txt.strip():
                    merge_extracted_into_db(ingredients_txt)

                # 배합 생성
                raw = generate_formulation(ftype, st.session_state.db, ingredients_txt.strip() or None)
                st.session_state.raw_formulation = raw
                
                df = normalize_and_cost(raw, st.session_state.db)
                st.session_state.formulation = df
                
                st.session_state.step = 3
                placeholder.empty()
                st.rerun()
            except Exception as e:
                placeholder.empty()
                import traceback
                err_str = str(e)
                if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "400" in err_str:
                    st.session_state.api_key = ""
                    st.session_state.step = 0
                    st.session_state.api_key_error_msg = "❌ 입력된 Gemini API 키가 올바르지 않거나 만료되었습니다. API 키를 재설정해 주세요."
                    st.rerun()
                else:
                    st.error(f"처방 설계에 실패했습니다: {e}")
                    with st.expander("🛠️ 상세 에러 로그 (디버깅용)"):
                        st.code(traceback.format_exc())
                    st.caption("Gemini API 키 상태와 쿼리 한도를 다시 한번 점검해 주세요.")

# ------------------------------------------------------------------
# STEP 3: 설계 결과 대시보드
# ------------------------------------------------------------------
elif st.session_state.step == 3:
    ftype = st.session_state.ftype
    df = st.session_state.formulation

    # 상단 요약 카드 및 엑셀 다운로드
    top = st.columns([3, 1])
    with top[0]:
        st.caption("STEP 3")
        st.subheader(f"📊 {ftype['label']} 최적 배합 설계 리포트")
    with top[1]:
        # 엑셀 시트 정밀 가공
        export_df = df.drop(columns=["DB매칭"]).copy()
        total_cost = export_df["총원가(원)"].sum()
        n_data = len(export_df)
        total_row = pd.DataFrame([{
            "상": "", "원료명": "합계", "기능": "",
            "배합비(%)": export_df["배합비(%)"].sum(),
            "중량(g)": export_df["중량(g)"].sum(),
            "단가(원/g)": "", "총원가(원)" : total_cost
        }])
        per100_row = pd.DataFrame([{
            "상": "", "원료명": "100g당 환산원가", "기능": "",
            "배합비(%)": "", "중량(g)": "", "단가(원/g)": "",
            "총원가(원)" : round(total_cost / 10)
        }])
        export_df = pd.concat([export_df, total_row, per100_row], ignore_index=True)

        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            sheet_name = "배합처방전"
            export_df.to_excel(writer, index=False, sheet_name=sheet_name)
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column("A:G", 18)
            bold_format = workbook.add_format({"bold": True})
            worksheet.set_row(n_data + 1, None, bold_format)
            worksheet.set_row(n_data + 2, None, bold_format)

            phases_order = df["상"].tolist()
            points = [{"fill": {"color": get_phase_color(p)}} for p in phases_order]

            chart = workbook.add_chart({"type": "pie"})
            chart.add_series({
                "name": "배합비 구성",
                "categories": [sheet_name, 1, 1, n_data, 1],
                "values":     [sheet_name, 1, 3, n_data, 3],
                "points": points,
                "data_labels": {"percentage": True, "category": False, "position": "outside_end",
                                 "font": {"size": 8}},
            })
            chart.set_title({"name": f"{ftype['label']} 배합 구성비 (%)"})
            chart.set_size({"width": 550, "height": 480})
            worksheet.insert_chart("I2", chart)

        st.download_button(
            "📥 네이티브 차트 포함 Excel 다운로드", data=buf.getvalue(),
            file_name=f"{ftype['label']}_배합처방리포트.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 100g당 단가 계산
    cost_100g = total_cost / 10
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="liquid-glass cfa-summary"><div class="label">기본 조제 기준 중량</div><div class="value">1,000 g</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="liquid-glass cfa-summary"><div class="label">1,000g 기준 배합 총원가</div><div class="value">{total_cost:,.0f}원</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="liquid-glass cfa-summary accent"><div class="label">100g당 제품 단가</div><div class="value">{cost_100g:,.0f}원</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Formulation 테이블과 성분 다이어그램을 한 페이지에 side-by-side 컬럼으로 배치
    st.markdown('<div class="liquid-glass">', unsafe_allow_html=True)
    col_table, col_chart = st.columns([1, 1.45])
    with col_table:
        st.markdown("#### 📊 Formulation")
        st.markdown(render_table_html(df), unsafe_allow_html=True)
    with col_chart:
        st.markdown("#### 🔵 성분 다이어그램")
        components.html(render_donut_html(df), height=570, scrolling=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ------------------------------------------------------------------
    # 대화식 배합 피드백 및 조정 기능 (고도화 핵심 요구사항)
    # ------------------------------------------------------------------
    st.markdown('<div class="liquid-glass">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 배합 커스텀 수정 피드백 루프")
    st.write("처방된 배합이 마음에 들지 않거나, 특정 요구사항이 있으면 피드백을 전달해 주세요. AI가 배합 비율과 원료를 정교하게 다시 조정합니다.")
    
    feedback_text = st.text_input(
        "피드백 입력",
        placeholder="예: '단가를 20% 낮추고 병풀 추출물을 2% 추가해줘', '사용감을 촉촉하게 개선하기 위해 보습제를 더 넣어줘'"
    )
    
    if st.button("🔧 피드백 반영하여 처방 재설계", type="primary"):
        if not feedback_text.strip():
            st.warning("피드백 내용을 입력해 주세요.")
        else:
            placeholder = st.empty()
            placeholder.markdown('''
            <div class="liquid-glass cfa-loading-box">
              <div class="cfa-ring-wrap">
                <div class="cfa-ring"></div><div class="cfa-ring d2"></div>
                <div class="cfa-core"></div><div class="cfa-core-inner">🛠️</div>
              </div>
              <div class="cfa-loading-label">Gemini AI · Adjusting</div>
              <div class="cfa-loading-msg">피드백을 반영하여 처방 수정 및 공정 재구성 중...</div>
            </div>
            ''', unsafe_allow_html=True)
            
            try:
                # 피드백 수정 실행
                raw = refine_formulation(ftype, st.session_state.db, st.session_state.raw_formulation, feedback_text)
                st.session_state.raw_formulation = raw
                
                df = normalize_and_cost(raw, st.session_state.db)
                st.session_state.formulation = df
                
                # 제조 공정 및 분석 리포트 업데이트 생략 (요구사항 반영)
                
                placeholder.empty()
                st.success("피드백이 성공적으로 반영되었습니다!")
                st.rerun()
            except Exception as e:
                placeholder.empty()
                err_str = str(e)
                if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "400" in err_str:
                    st.session_state.api_key = ""
                    st.session_state.step = 0
                    st.session_state.api_key_error_msg = "❌ 입력된 Gemini API 키가 올바르지 않거나 만료되었습니다. API 키를 재설정해 주세요."
                    st.rerun()
                else:
                    st.error(f"피드백 반영 수정에 실패했습니다: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 라벨 크롭 분석 데이터 원본 복원 및 표시
    # ------------------------------------------------------------------
    if st.session_state.label_ingredients:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🔍 라벨 분석 정보 및 원본 대조"):
            col_crop_l, col_crop_r = st.columns([1, 2])
            with col_crop_l:
                if st.session_state.label_crop:
                    st.write("지정했던 전성분 크롭 이미지:")
                    st.image(st.session_state.label_crop, use_container_width=True)
                    if st.button("🔍 전체 원본 이미지 보기"):
                        zoom_dialog(st.session_state.label_original, "업로드 원본 라벨 이미지")
            with col_crop_r:
                st.write("라벨에서 추출된 원본 성분 텍스트:")
                st.info(st.session_state.label_ingredients)
                st.caption("이 성분들 중 원료 데이터베이스에 없었던 원료는 자동으로 DB에 등록되었으며 단가 15원/g으로 가설정되었습니다.")
