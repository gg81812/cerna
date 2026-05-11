
"""
ui/styles.py — Cerna global CSS + Web Speech API voice input injection.
Call inject_global_css() once at app startup.

v2.1 palette: light lavender background, white chat panel, dark purple left panel.
"""

import streamlit as st

_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Sans:ital,wght@0,400;0,500;0,600;1,400&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ── Global reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    background: #F4F1FF !important;
    color: #1F2937 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
section[data-testid="stSidebar"] { display: none !important; }

/* ── Remove default container padding ── */
.block-container { padding: 0 !important; max-width: 100% !important; }
div[data-testid="column"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }

/* ── LEFT PANEL (dark — avatar hero) ── */
.left-panel {
    width: 100%;
    background: linear-gradient(175deg, #1C0D3F 0%, #2A1260 35%, #1A0935 70%, #0D0720 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2.5rem 1.5rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.left-panel-footer-only {
    padding: 0.5rem 1.5rem 1rem !important;
}
.left-panel::before {
    content: '';
    position: absolute;
    top: -60px; left: -60px;
    width: 280px; height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(123,63,228,0.18) 0%, transparent 70%);
    pointer-events: none;
}
.left-panel::after {
    content: '';
    position: absolute;
    bottom: 40px; right: -40px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(26,188,176,0.12) 0%, transparent 70%);
    pointer-events: none;
}

/* Avatar */
.avatar-wrap {
    position: relative;
    width: 160px; height: 160px;
    margin-bottom: 1.1rem;
    animation: avatar-float 4s ease-in-out infinite;
}
@keyframes avatar-float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-7px); }
}
.avatar-ring {
    width: 100%; height: 100%;
    border-radius: 50%;
    border: 2.5px solid rgba(199,70,52,0.8);
    padding: 6px;
    background: radial-gradient(circle at 35% 35%, #2E1560 0%, #0D0720 100%);
    box-shadow:
        0 0 0 1px rgba(123,63,228,0.3),
        0 0 25px rgba(199,70,52,0.18),
        0 0 55px rgba(123,63,228,0.14);
    animation: ring-breathe 3s ease-in-out infinite;
    transition: box-shadow 0.4s ease;
}
@keyframes ring-breathe {
    0%, 100% {
        box-shadow: 0 0 0 1px rgba(123,63,228,0.3), 0 0 25px rgba(199,70,52,0.18), 0 0 55px rgba(123,63,228,0.14);
    }
    50% {
        box-shadow: 0 0 0 1px rgba(123,63,228,0.5), 0 0 42px rgba(199,70,52,0.36), 0 0 80px rgba(123,63,228,0.26);
    }
}
.avatar-wrap.speaking .avatar-ring {
    border-color: rgba(199,70,52,1);
    animation: ring-speak 0.75s ease-in-out infinite;
}
@keyframes ring-speak {
    0%, 100% {
        box-shadow: 0 0 0 2px rgba(123,63,228,0.5), 0 0 40px rgba(199,70,52,0.55), 0 0 75px rgba(123,63,228,0.3);
    }
    50% {
        box-shadow: 0 0 0 3px rgba(123,63,228,0.7), 0 0 58px rgba(199,70,52,0.75), 0 0 100px rgba(123,63,228,0.45);
    }
}
.avatar-ring svg { width: 100%; height: 100%; border-radius: 50%; display: block; }
.avatar-pulse {
    position: absolute; inset: -8px;
    border-radius: 50%;
    border: 1px solid rgba(199,70,52,0.35);
    animation: ring-pulse 2.5s ease-out infinite;
}
.avatar-pulse-2 {
    position: absolute; inset: -8px;
    border-radius: 50%;
    border: 1px solid rgba(123,63,228,0.22);
    animation: ring-pulse 2.5s ease-out infinite 1.25s;
}
@keyframes ring-pulse {
    0%   { transform: scale(1);    opacity: 0.6; }
    100% { transform: scale(1.18); opacity: 0; }
}

/* Speaking bars */
.speaking-bars {
    display: flex; gap: 3px; align-items: flex-end;
    justify-content: center; height: 30px; margin-bottom: 0.8rem;
}
.speaking-bars .b {
    width: 4px; border-radius: 3px;
    background: linear-gradient(to top, #C74634, #FF8C7A);
    animation: wave 0.9s ease-in-out infinite;
}
.speaking-bars .b:nth-child(1) { animation-delay: 0.00s; animation-duration: 0.90s; }
.speaking-bars .b:nth-child(2) { animation-delay: 0.10s; animation-duration: 0.70s; }
.speaking-bars .b:nth-child(3) { animation-delay: 0.20s; animation-duration: 1.10s; }
.speaking-bars .b:nth-child(4) { animation-delay: 0.05s; animation-duration: 0.80s; }
.speaking-bars .b:nth-child(5) { animation-delay: 0.30s; animation-duration: 0.95s; }
.speaking-bars .b:nth-child(6) { animation-delay: 0.15s; animation-duration: 0.75s; }
.speaking-bars .b:nth-child(7) { animation-delay: 0.25s; animation-duration: 1.00s; }
@keyframes wave {
    0%, 100% { height: 5px;  opacity: 0.4; }
    50%       { height: 25px; opacity: 1.0; }
}
.idle-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: rgba(26,188,176,0.7);
    box-shadow: 0 0 8px rgba(26,188,176,0.5);
    animation: dot-pulse 2s ease-in-out infinite;
    margin-bottom: 0.8rem;
}
@keyframes dot-pulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50%       { opacity: 1.0; transform: scale(1.3); }
}

/* Brand text (left panel) */
.avatar-name {
    font-family: 'Sora', sans-serif;
    font-size: 2rem; font-weight: 700;
    color: #FFFFFF; letter-spacing: 0.03em;
    margin-bottom: 0.15rem;
}
.avatar-role {
    font-size: 0.7rem; color: rgba(200,180,255,0.65);
    letter-spacing: 0.12em; text-transform: uppercase;
    margin-bottom: 1.3rem; text-align: center;
}

/* Description bubble (left panel) */
.intro-bubble {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(123,63,228,0.3);
    border-radius: 16px;
    padding: 0.95rem 1.1rem;
    font-size: 0.82rem; color: rgba(200,200,230,0.85);
    line-height: 1.65; text-align: center;
    margin-bottom: 1.4rem;
    backdrop-filter: blur(8px);
    width: 100%;
}
.intro-bubble strong { color: #1ABCB0; font-weight: 600; }

/* Module pills (left panel) */
.mod-pills { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; width: 100%; margin-bottom: 1.4rem; }
.mod-pill {
    padding: 3px 9px; border-radius: 16px;
    font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.04em; border: 1px solid transparent;
    cursor: default; opacity: 0.85;
    white-space: nowrap;
}
.mod-pill.active {
    opacity: 1 !important;
    box-shadow: 0 0 10px rgba(255,255,255,0.15);
}

/* Left panel footer */
.left-footer {
    margin-top: auto; width: 100%;
    padding-top: 1rem;
    border-top: 1px solid rgba(123,63,228,0.2);
    font-size: 0.68rem; color: rgba(160,140,200,0.6);
    text-align: center; line-height: 1.9;
}

/* Starter-prompts toggle button — styled via Streamlit's st-key-* class
   selector which is reliably injected onto the element-container wrapping
   any widget with a `key=` parameter. Same gradient family as .left-panel. */
.st-key-starter_toggle button,
.st-key-starter_toggle button p {
    background: linear-gradient(135deg, #2A1260 0%, #1C0D3F 100%) !important;
    border: 1px solid rgba(123, 63, 228, 0.5) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    text-align: left !important;
    padding: 0.6rem 0.95rem !important;
    font-size: 0.82rem !important;
    border-radius: 10px !important;
    letter-spacing: 0.01em !important;
}
.st-key-starter_toggle button:hover,
.st-key-starter_toggle button:hover p {
    background: linear-gradient(135deg, #3A1A78 0%, #25115A 100%) !important;
    border-color: rgba(160, 100, 255, 0.9) !important;
    color: #FFFFFF !important;
}

/* Chip buttons — match the toggle palette so the whole LHS feels unified.
   Streamlit attaches `st-key-chip_0` ... `st-key-chip_7` to each chip container. */
[class*="st-key-chip_"] button,
[class*="st-key-chip_"] button p {
    background: linear-gradient(135deg, #2A1260 0%, #1C0D3F 100%) !important;
    border: 1px solid rgba(123, 63, 228, 0.45) !important;
    color: #FFFFFF !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 0.6rem !important;
    min-height: auto !important;
    white-space: normal !important;
    line-height: 1.3 !important;
    border-radius: 8px !important;
}
[class*="st-key-chip_"] button:hover,
[class*="st-key-chip_"] button:hover p {
    background: linear-gradient(135deg, #3A1A78 0%, #25115A 100%) !important;
    border-color: rgba(160, 100, 255, 0.9) !important;
    color: #FFFFFF !important;
}
.left-footer strong { color: rgba(200,180,255,0.8); }

/* ── CHAT PANEL (light) ── */
.chat-panel-bg {
    background: #FFFFFF;
    min-height: 100vh;
    border-left: 1px solid rgba(123,63,228,0.08);
    border-right: 1px solid rgba(123,63,228,0.08);
}

/* Chat header */
.chat-header {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.85rem 1.4rem;
    background: #FFFFFF;
    border-bottom: 1px solid rgba(123,63,228,0.1);
}
.hdr-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: #7B3FE4; box-shadow: 0 0 8px rgba(123,63,228,0.5);
    flex-shrink: 0;
    animation: dot-pulse 2s ease-in-out infinite;
}
.hdr-title {
    font-family: 'Sora', sans-serif;
    font-size: 0.92rem; font-weight: 600; color: #1F2937;
    display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
}
.hdr-badge {
    padding: 2px 9px; border-radius: 8px;
    font-size: 0.66rem; font-weight: 600; letter-spacing: 0.03em;
}

/* User bubble */
.msg-user-wrap { display: flex; justify-content: flex-end; padding: 0 0 0.75rem 3rem; }
.msg-user {
    background: #7B3FE4;
    color: #FFFFFF;
    padding: 0.7rem 1rem;
    border-radius: 14px 14px 3px 14px;
    max-width: 72%;
    font-size: 0.875rem; line-height: 1.6;
    box-shadow: 0 2px 8px rgba(123,63,228,0.25);
}

/* Response card */
.resp-card {
    background: #FFFFFF;
    border: 1px solid rgba(123,63,228,0.12);
    border-radius: 12px;
    overflow: hidden;
    margin: 0 0 0.75rem 0;
    box-shadow: 0 1px 12px rgba(123,63,228,0.07);
}
.resp-sec {
    border-bottom: 1px solid rgba(123,63,228,0.06);
    padding-top: 0.1rem;
}
.resp-sec:last-of-type { border-bottom: none; }
.resp-sec-label {
    font-size: 0.6rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase;
    color: rgba(123,63,228,0.55);
    padding: 0.7rem 1.1rem 0.15rem;
}
.resp-sec-body {
    padding: 0.1rem 1.1rem 0.85rem;
    font-size: 0.875rem; line-height: 1.72; color: #374151;
}
.resp-sec-body code {
    font-family: 'DM Mono', monospace;
    background: #F3EEFF; padding: 2px 6px;
    border-radius: 4px; font-size: 0.82em; color: #6D28D9;
}
.resp-sec-body pre {
    background: #F3EEFF; padding: 0.7rem;
    border-radius: 8px; overflow-x: auto;
    font-family: 'DM Mono', monospace;
    font-size: 0.8em; color: #5B21B6; margin: 0.4rem 0;
}

/* Sources row */
.src-row {
    display: flex; flex-wrap: wrap; gap: 5px;
    padding: 0.6rem 1rem;
    border-top: 1px solid rgba(123,63,228,0.06);
    background: #FAF8FF;
}
.src-pill {
    padding: 2px 9px;
    background: #EDE9FF;
    border: 1px solid rgba(123,63,228,0.15);
    border-radius: 6px; font-size: 0.66rem;
    color: #6D28D9; font-family: 'DM Mono', monospace;
}
.src-pill-primary {
    background: #D1FAE5; border-color: rgba(16,185,129,0.25); color: #065F46;
}
.src-pill-archival {
    background: #FEF3C7; border-color: rgba(245,158,11,0.30); color: #92400E;
    cursor: help;
}
.module-banner {
    margin-top: 0.5rem;
    padding: 0.45rem 0.8rem;
    border-radius: 6px;
    font-size: 0.67rem;
    line-height: 1.45;
    color: #78350F;
    background: #FFFBEB;
    border: 1px solid rgba(245,158,11,0.25);
    display: flex; align-items: flex-start; gap: 0.4rem;
}
.module-banner-icon { flex-shrink: 0; font-size: 0.8rem; margin-top: 1px; }

/* Typing / stream indicator */
.stream-status {
    font-size: 0.82rem; color: #7B3FE4;
    padding: 0.5rem 1.1rem;
    display: flex; align-items: center; gap: 0.4rem;
    animation: fade-in 0.3s ease;
}
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

.typing-card {
    background: #FFFFFF;
    border: 1px solid rgba(123,63,228,0.12);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 8px rgba(123,63,228,0.07);
}
.typing-card span {
    width: 7px; height: 7px; border-radius: 50%;
    background: #7B3FE4;
    animation: tbounce 1.2s ease-in-out infinite;
    display: inline-block;
}
.typing-card span:nth-child(2) { animation-delay: 0.2s; }
.typing-card span:nth-child(3) { animation-delay: 0.4s; }
@keyframes tbounce {
    0%, 100% { transform: translateY(0); opacity: 0.35; }
    50%       { transform: translateY(-5px); opacity: 1; }
}

/* Follow-up section */
.fu-section { margin-top: 1.1rem; }
.fu-label {
    font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: rgba(123,63,228,0.4);
    margin: 0 0 0.5rem;
    border-top: 1px solid rgba(123,63,228,0.08);
    padding-top: 0.75rem;
}
/* Follow-up buttons — compact, non-wrapping, max readable width */
.fu-section ~ div div.stButton > button,
div[data-testid="stVerticalBlock"] > div:has(.fu-label) ~ div div.stButton > button {
    font-size: 0.79rem !important;
    padding: 0.4rem 0.9rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
    display: block !important;
    text-align: left !important;
}

/* Prompt chip section label */
.chip-section-label {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: rgba(123,63,228,0.4);
    padding: 0.3rem 1.4rem 0.1rem;
}

/* ── FEATURES PANEL (right column) ── */
.features-panel-title {
    font-family: 'Sora', sans-serif;
    font-size: 0.68rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase;
    color: #7B3FE4;
    margin: 1.1rem 0 0.8rem;
    padding-bottom: 0.45rem;
    border-bottom: 1px solid rgba(123,63,228,0.12);
}
.feature-cat-title {
    font-size: 0.62rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: #9CA3AF;
    margin: 0.9rem 0 0.3rem;
    padding: 0 0.15rem;
}
/* Tighten feature panel buttons */
div[data-testid="column"] div.stButton > button {
    font-size: 0.76rem !important;
    padding: 0.3rem 0.6rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
}

/* ── Streamlit widget overrides (light mode) ── */

/* All buttons */
div.stButton > button {
    background: #FFFFFF !important;
    border: 1px solid rgba(123,63,228,0.2) !important;
    color: #6D28D9 !important;
    border-radius: 8px !important;
    font-size: 0.81rem !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.38rem 0.85rem !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}
div.stButton > button:hover {
    background: rgba(123,63,228,0.06) !important;
    border-color: rgba(123,63,228,0.4) !important;
    color: #5B21B6 !important;
}
div.stButton > button[kind="primary"] {
    background: rgba(123,63,228,0.1) !important;
    border-color: rgba(123,63,228,0.35) !important;
    color: #7B3FE4 !important;
}

/* Selectbox */
div[data-testid="stSelectbox"] > div > div {
    background: #FFFFFF !important;
    border: 1px solid rgba(123,63,228,0.2) !important;
    border-radius: 8px !important;
    color: #374151 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    box-shadow: none !important;
}

/* Chat message spacing */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.2rem 0 !important;
}

/* st.chat_input overrides */
[data-testid="stChatInputContainer"] {
    background: #FFFFFF !important;
    border-top: 1px solid rgba(123,63,228,0.1) !important;
    padding: 0.75rem 1.4rem 1rem !important;
}
[data-testid="stChatInputContainer"] textarea {
    background: #F9F7FF !important;
    border: 1px solid rgba(123,63,228,0.18) !important;
    border-radius: 10px !important;
    color: #1F2937 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    caret-color: #7B3FE4 !important;
}
[data-testid="stChatInputContainer"] textarea:focus {
    border-color: #7B3FE4 !important;
    box-shadow: 0 0 0 3px rgba(123,63,228,0.1) !important;
    outline: none !important;
}
[data-testid="stChatInputContainer"] textarea::placeholder { color: #9CA3AF !important; }
[data-testid="stChatInputContainer"] button {
    background: linear-gradient(135deg, #7B3FE4, #5A2DB8) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
}

/* Expander overrides */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(123,63,228,0.12) !important;
    border-radius: 8px !important;
    margin: 0.3rem 0 !important;
}
[data-testid="stExpander"] summary {
    color: #6D28D9 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: 0.04em !important;
}
[data-testid="stExpander"] > div > div {
    background: #FDFCFF !important;
    padding: 0.4rem 0.5rem !important;
}

/* Selectbox label hide */
div[data-testid="stSelectbox"] > label { display: none !important; }
div[data-testid="stSelectbox"] > div > div {
    background: #FFFFFF !important;
    border: 1px solid rgba(123,63,228,0.2) !important;
    color: #374151 !important;
    min-height: 2rem !important;
}
/* Dropdown list */
div[data-baseweb="popover"] ul {
    background: #FFFFFF !important;
    border: 1px solid rgba(123,63,228,0.2) !important;
    border-radius: 8px !important;
}
div[data-baseweb="popover"] li {
    color: #374151 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] li[aria-selected="true"] {
    background: rgba(123,63,228,0.08) !important;
    color: #5B21B6 !important;
}

/* Gap tweak */
[data-testid="stHorizontalBlock"] { gap: 4px !important; }

/* Equal-height suggestion buttons */
[data-testid="stExpander"] div.stButton > button {
    min-height: 3.8rem !important;
    height: auto !important;
    white-space: normal !important;
    text-align: center !important;
    line-height: 1.4 !important;
}
</style>
"""

_VOICE_JS = """
<script>
(function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    function waitForInput(cb, retries = 40) {
        const container = document.querySelector('[data-testid="stChatInputContainer"]');
        if (container) { cb(container); return; }
        if (retries > 0) setTimeout(() => waitForInput(cb, retries - 1), 200);
    }

    waitForInput(function(container) {
        if (document.getElementById('cerna-mic-btn')) return;

        const btn = document.createElement('button');
        btn.id = 'cerna-mic-btn';
        btn.title = 'Voice input';
        btn.innerHTML = '🎤';
        btn.style.cssText = (
            'position:absolute;right:52px;bottom:18px;z-index:9999;' +
            'width:34px;height:34px;border-radius:50%;border:none;' +
            'background:rgba(123,63,228,0.1);color:#7B3FE4;' +
            'font-size:16px;cursor:pointer;display:flex;align-items:center;' +
            'justify-content:center;transition:background 0.2s;'
        );
        container.style.position = 'relative';
        container.appendChild(btn);

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        let listening = false;

        btn.addEventListener('click', function() {
            if (listening) { recognition.stop(); return; }
            recognition.start();
        });

        recognition.onstart = function() {
            listening = true;
            btn.style.background = 'rgba(199,70,52,0.15)';
            btn.style.color = '#C74634';
            btn.title = 'Listening… click to stop';
        };
        recognition.onend = function() {
            listening = false;
            btn.style.background = 'rgba(123,63,228,0.1)';
            btn.style.color = '#7B3FE4';
            btn.title = 'Voice input';
        };
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            const textarea = container.querySelector('textarea');
            if (!textarea) return;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(textarea, transcript);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.focus();
        };
        recognition.onerror = function(e) {
            console.warn('SpeechRecognition error:', e.error);
            listening = false;
            btn.style.background = 'rgba(123,63,228,0.1)';
            btn.style.color = '#7B3FE4';
        };
    });
})();
</script>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(_VOICE_JS, unsafe_allow_html=True)


def inject_admin_panel(cache_stats: dict, recent_logs: list[dict]) -> None:
    """Render admin dashboard (only shown when ?admin=1 in URL)."""
    st.markdown("---")
    st.markdown("### Admin View")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cache backend", cache_stats.get("backend", "unknown"))
        st.metric("In-memory entries", cache_stats.get("in_memory_entries", 0))
    with col2:
        st.metric("Recent log entries", len(recent_logs))
        if recent_logs:
            avg_lat = sum(r.get("latency_ms", 0) for r in recent_logs) / len(recent_logs)
            st.metric("Avg latency (ms)", f"{avg_lat:.0f}")

    if recent_logs:
        st.markdown("**Recent queries**")
        for log in recent_logs[-5:]:
            st.markdown(
                f"- `{log.get('classified_vertical','?')}` "
                f"| conf={log.get('confidence','?')} "
                f"| {log.get('latency_ms','?')}ms "
                f"| {log.get('query','')[:60]}"
            )
