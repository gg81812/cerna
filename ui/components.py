"""
ui/components.py — Cerna UI components.

Public functions:
    render_left_panel(is_speaking, active_module, kb_counts)
    render_top_bar()
    render_starter_grid()
    render_chat(messages)
    render_structured_response(plain, sections, sources)
    render_followups(follow_ups, msg_index)

All functions read / write st.session_state directly where needed.
"""

from __future__ import annotations

import json
import os
import re
import streamlit as st

try:
    from streamlit_lottie import st_lottie
    _LOTTIE_OK = True
except ImportError:
    _LOTTIE_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

FEATURES: dict[str, list[tuple[str, str]]] = {
    "🔵 FHIR & APIs": [
        ("SMART on FHIR auth", "What is the Cerner FHIR R4 authorization flow?"),
        ("Patient search params", "What are the FHIR R4 patient search parameters in Cerner?"),
        ("CDS Hooks setup", "How do I integrate CDS Hooks with Cerner?"),
    ],
    "🟣 Revenue Cycle": [
        ("Charge capture", "How does charge capture work in Cerner Revenue Cycle?"),
        ("RevElate overview", "What is RevElate and how does it differ from legacy Cerner Revenue Cycle?"),
        ("Charge review workflow", "What are the main charge review workflows for a Revenue Cycle analyst?"),
    ],
    "🔴 Millennium Platform": [
        ("Domain architecture", "Explain the Millennium domain architecture"),
        ("CCL scripting", "What are best practices for CCL scripting in Millennium?"),
        ("Module navigation", "How do I navigate between Cerner Millennium modules?"),
    ],
    "🔧 Troubleshooting": [
        ("FHIR 403 errors", "Why am I getting 403 errors on the Cerner FHIR endpoint?"),
        ("Charge capture errors", "How do I resolve charge capture errors in Revenue Cycle?"),
        ("eMAR won't load", "What should I do when eMAR medication records won't load?"),
    ],
    "🆕 What's New": [
        ("FHIR Communication resource", "What are the Cerner FHIR R4 Communication resource capabilities?"),
        ("RevElate platform", "What is RevElate and how does it differ from legacy Cerner Revenue Cycle?"),
        ("Oracle Health direction", "What is Oracle Health's roadmap for Cerner Millennium?"),
    ],
}

MODULES: dict[str | None, tuple[str, str]] = {
    None:            ("Auto",          "#6B7280"),
    "millennium":    ("Millennium",    "#C74634"),
    "powerchart":    ("PowerChart",    "#1ABCB0"),
    "revenue_cycle": ("Revenue Cycle", "#7B5EA7"),
    "fhir":          ("FHIR & APIs",   "#3B82F6"),
    "clinical":      ("Clinical",      "#EC4899"),
}

# Modules with limited primary-source coverage — shown with coverage banner
_LIMITED_MODULES = {"powerchart", "clinical"}

# Per-module banner copy shown below the response card
_MODULE_BANNERS: dict[str, str] = {
    "powerchart": (
        "PowerChart answers are drawn from archival community documentation "
        "(wiki.cerner.com, pre-Oracle migration). Navigation paths and configuration "
        "options may differ in your Oracle Health environment. Verify with the Oracle Help Center."
    ),
    "clinical": (
        "Clinical workflow answers are drawn from archival community documentation "
        "(wiki.cerner.com, pre-Oracle migration). Clinical configuration steps may "
        "differ by site and product version. Verify with the Oracle Help Center before implementing."
    ),
    "millennium": (
        "Millennium answers may cite CCL and Discern documentation from the pre-Oracle wiki archive. "
        "Validate CCL code and domain configuration against your current Oracle Help Center reference."
    ),
}

SUGGESTIONS: list[tuple[str, str]] = [
    ("🔵", "What is the Cerner FHIR R4 authorization flow?"),
    ("🟣", "How does charge capture work in Revenue Cycle?"),
    ("🔴", "Explain the Millennium domain architecture"),
    ("🔵", "How do I search for a patient using the FHIR R4 API?"),
    ("🟣", "What is RevElate and how does it differ from legacy RCM?"),
    ("🔴", "What are best practices for CCL scripting in Millennium?"),
]

PROMPT_CHIPS: list[str] = [
    "FHIR R4 patient search params",
    "SMART on FHIR authorization",
    "Revenue Cycle charge routing",
    "RevElate platform overview",
    "Millennium domain architecture",
    "CCL scripting best practices",
    "CDS Hooks integration guide",
    "FHIR Communication resource",
]

RESPONSE_SECTIONS: list[str] = [
    "DIRECT ANSWER",
    "CONTEXT & EXPLANATION",
    "STEP-BY-STEP GUIDE",
    "BEST PRACTICES",
    "RECOMMENDATIONS",
]

SECTION_ICONS: dict[str, str] = {
    "DIRECT ANSWER":         "💡",
    "CONTEXT & EXPLANATION": "📖",
    "STEP-BY-STEP GUIDE":    "🔢",
    "BEST PRACTICES":        "✅",
    "RECOMMENDATIONS":       "🎯",
}

# ─────────────────────────────────────────────────────────────────────────────
# Avatar SVG (CSS placeholder — Week 1–2 approved)
# ─────────────────────────────────────────────────────────────────────────────

AVATAR_SVG = """<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="abg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2A1260"/><stop offset="100%" stop-color="#0D0720"/>
    </radialGradient>
    <radialGradient id="ask" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#F5C9A8"/><stop offset="100%" stop-color="#D4956A"/>
    </radialGradient>
  </defs>
  <circle cx="100" cy="100" r="100" fill="url(#abg)"/>
  <ellipse cx="100" cy="178" rx="56" ry="36" fill="#1C0D3F"/>
  <ellipse cx="100" cy="168" rx="43" ry="28" fill="#150A30"/>
  <rect x="88" y="130" width="24" height="22" rx="8" fill="url(#ask)"/>
  <ellipse cx="100" cy="106" rx="38" ry="42" fill="url(#ask)"/>
  <ellipse cx="100" cy="69" rx="38" ry="18" fill="#1A0A2E"/>
  <ellipse cx="62" cy="93" rx="10" ry="22" fill="#1A0A2E"/>
  <ellipse cx="138" cy="93" rx="10" ry="22" fill="#1A0A2E"/>
  <ellipse cx="85" cy="101" rx="6" ry="7" fill="#fff"/>
  <ellipse cx="115" cy="101" rx="6" ry="7" fill="#fff"/>
  <circle cx="86" cy="102" r="4" fill="#2D1560"/>
  <circle cx="116" cy="102" r="4" fill="#2D1560"/>
  <circle cx="87" cy="100" r="1.5" fill="#fff"/>
  <circle cx="117" cy="100" r="1.5" fill="#fff"/>
  <path d="M78 92 Q85 88 92 92" stroke="#1A0A2E" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M108 92 Q115 88 122 92" stroke="#1A0A2E" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M97 108 Q95 116 97 119 Q100 121 103 119 Q105 116 103 108" fill="#C4855A" opacity="0.35"/>
  <path d="M88 126 Q100 135 112 126" stroke="#C4855A" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <ellipse cx="76" cy="118" rx="8" ry="5" fill="#E8908A" opacity="0.3"/>
  <ellipse cx="124" cy="118" rx="8" ry="5" fill="#E8908A" opacity="0.3"/>
  <path d="M72 158 L100 150 L128 158" stroke="#7B3FE4" stroke-width="2" fill="none"/>
  <rect x="80" y="168" width="40" height="14" rx="4" fill="#7B3FE4" opacity="0.9"/>
  <text x="100" y="178" text-anchor="middle" font-size="6.5"
        font-family="Sora,sans-serif" fill="#fff" font-weight="700">ORACLE</text>
</svg>"""

# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

_LOTTIE_URL: str | None = None


def _load_lottie() -> dict | None:
    if _LOTTIE_URL:
        try:
            import requests
            r = requests.get(_LOTTIE_URL, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "avatar.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _parse_response(raw: str) -> tuple[str, dict[str, str]]:
    sec_re = re.compile(
        r"\*\*(" + "|".join(re.escape(s) for s in RESPONSE_SECTIONS) + r")\*\*",
        re.IGNORECASE,
    )
    split = sec_re.split(raw.strip())
    plain_intro = split[0].strip()

    sections: dict[str, str] = {}
    i = 1
    while i < len(split) - 1:
        sections[split[i].upper()] = split[i + 1].strip()
        i += 2

    return plain_intro, sections


def _md_to_html(text: str) -> str:
    text = re.sub(r"^\s*\*{1,2}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(
        r"```[\w]*\n?(.*?)```", r"<pre>\1</pre>",
        text, flags=re.DOTALL,
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong style="color:#D8E4F0;">\1</strong>', text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(
        r"^\s*(\d+)[.)]\s+(.+)$",
        r'<div style="margin:0.25rem 0 0.25rem 0.5rem;">'
        r'<span style="color:#8B9DB0;font-weight:600;">\1.</span> \2</div>',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r"^\s*[-•]\s+(.+)$",
        r'<div style="margin:0.2rem 0 0.2rem 0.5rem;color:#96B0C8;">◦ \1</div>',
        text, flags=re.MULTILINE,
    )
    text = (
        text
        .replace("\n\n", '<div style="height:0.4rem;"></div>')
        .replace("\n", "<br>")
    )
    return text


def _kb_footer_html(kb_counts: dict) -> str:
    try:
        total = kb_counts.get("total", 0) if kb_counts else 0
        if not total:
            return ""
        return (
            f"<span style='font-size:0.72rem;font-weight:600;color:rgba(200,180,255,0.7);'>"
            f"{total:,} knowledge articles</span>"
        )
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Public components
# ─────────────────────────────────────────────────────────────────────────────

def render_left_panel(
    is_speaking: bool,
    active_module: str | None,
    kb_counts: dict,
) -> None:
    lottie_data = _load_lottie()

    speaking_html = (
        '<div class="speaking-bars">'
        + "".join('<div class="b"></div>' for _ in range(7))
        + "</div>"
        if is_speaking
        else '<div class="idle-dot"></div>'
    )

    if lottie_data and _LOTTIE_OK:
        _, mid, _ = st.columns([0.3, 2.4, 0.3])
        with mid:
            st_lottie(
                lottie_data,
                height=170,
                key="avatar_lottie",
                speed=1.5 if is_speaking else 1.0,
                loop=True,
            )
        st.markdown(f"""
<div class="left-panel">
  {speaking_html}
  <div class="avatar-name">Cerna</div>
  <div class="avatar-role">Cerner AI Specialist · Oracle Health</div>
  <div class="intro-bubble">
    Your Oracle Health AI specialist — covering
    <strong>FHIR APIs</strong>, <strong>Revenue Cycle</strong>,
    <strong>Millennium</strong>, PowerChart, and Clinical workflows.
    Every answer cited to source.
  </div>
</div>""", unsafe_allow_html=True)
    else:
        speaking_cls = " speaking" if is_speaking else ""
        st.markdown(f"""
<div class="left-panel">
  <div class="avatar-wrap{speaking_cls}">
    <div class="avatar-ring">{AVATAR_SVG}</div>
    <div class="avatar-pulse"></div>
    <div class="avatar-pulse-2"></div>
  </div>
  {speaking_html}
  <div class="avatar-name">Cerna</div>
  <div class="avatar-role">Oracle Health AI Specialist</div>
  <div class="intro-bubble">
    Your Oracle Health AI specialist — covering
    <strong>FHIR APIs</strong>, <strong>Revenue Cycle</strong>,
    <strong>Millennium</strong>, PowerChart, and Clinical workflows.
    Every answer cited to source.
  </div>
</div>""", unsafe_allow_html=True)


def render_left_footer(kb_counts: dict) -> None:
    """Knowledge-articles footer — rendered after the starter dropdown."""
    st.markdown(
        f'<div class="left-panel left-panel-footer-only">'
        f'<div class="left-footer">{_kb_footer_html(kb_counts)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_top_bar() -> None:
    """Header bar with title and interactive module filter selectbox."""
    active_key = st.session_state.get("active_module")
    active_label, active_colour = MODULES.get(active_key, ("Auto", "#6B7280"))

    badge_html = (
        f' <span class="hdr-badge" style="background:{active_colour}14;'
        f'border:1px solid {active_colour}40;color:{active_colour};">'
        f'{active_label}</span>'
    ) if active_key else ""

    hdr_col, sel_col, btn_col = st.columns([13, 5, 1])

    with hdr_col:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.55rem 0.2rem;">'
            f'<span style="font-family:Sora,sans-serif;font-size:1.05rem;font-weight:700;'
            f'color:#1F2937;letter-spacing:0.01em;">Cerna</span>'
            f'<span style="font-size:0.68rem;color:#9CA3AF;font-weight:400;">Oracle Health AI Specialist</span>'
            f'{badge_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with sel_col:
        # Module filter — None means auto-classify
        module_keys = list(MODULES.keys())           # [None, "millennium", ...]
        module_labels = [MODULES[k][0] for k in module_keys]  # ["Auto", "Millennium", ...]
        current_idx = module_keys.index(active_key) if active_key in module_keys else 0
        chosen_label = st.selectbox(
            "Module",
            options=module_labels,
            index=current_idx,
            key="module_filter_select",
            label_visibility="collapsed",
            help="Filter Cerna's retrieval to a specific module, or leave on Auto.",
        )
        chosen_key = module_keys[module_labels.index(chosen_label)]
        if chosen_key != active_key:
            st.session_state.active_module = chosen_key
            st.rerun()

    with btn_col:
        if st.button("✕", key="clear_btn", help="Clear conversation", use_container_width=True):
            st.session_state.messages        = []
            st.session_state.last_module     = None
            st.session_state.pending_prompt  = None
            st.session_state.avatar_speaking = False
            st.session_state.active_module   = None
            st.rerun()


def render_starter_grid() -> None:
    """Collapsible starter prompts dropdown in the left panel.

    Hidden by default behind a click-to-open expander styled to match the dark
    purple LHS background. Auto-hides entirely once a conversation starts.
    """
    if st.session_state.get("messages"):
        return

    # Wrapper class lets us target the expander styling without affecting
    # any other expanders in the app.
    st.markdown('<div class="starter-expander">', unsafe_allow_html=True)
    with st.expander("⚡ Quick-start prompts", expanded=False):
        # 2-column grid — fits the narrow left panel
        for i, chip in enumerate(PROMPT_CHIPS):
            if i % 2 == 0:
                cols = st.columns(2)
            with cols[i % 2]:
                if st.button(chip, key=f"chip_{i}", use_container_width=True):
                    st.session_state.pending_prompt = chip
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_cerna_response(
    cerna_resp,
    sources: list[dict] | None = None,
    classification: str | None = None,
) -> None:
    """Render a CernaResponse Pydantic object as a structured card."""
    from schemas import CernaResponse

    _MOD_DISPLAY = {
        "FHIR":          ("FHIR & APIs",    "#3B82F6"),
        "REVENUE_CYCLE": ("Revenue Cycle",  "#7B5EA7"),
        "MILLENNIUM":    ("Millennium",     "#C74634"),
        "POWERCHART":    ("PowerChart",     "#1ABCB0"),
        "CLINICAL":      ("Clinical",       "#EC4899"),
        "GENERAL":       ("General",        "#6B7280"),
    }
    _CONF_LABELS = {"high": "High Confidence", "medium": "Medium", "low": "Low Confidence"}

    parts = ['<div class="resp-card">']

    # Module + confidence header
    conf_colours = {"high": "#22C55E", "medium": "#F59E0B", "low": "#EF4444"}
    conf = (cerna_resp.confidence or "medium").lower()
    conf_col = conf_colours.get(conf, "#F59E0B")
    conf_label = _CONF_LABELS.get(conf, "Medium")
    mod_label, mod_col = _MOD_DISPLAY.get((classification or "GENERAL").upper(), ("General", "#6B7280"))
    parts.append(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:0.65rem 1.1rem 0.4rem;gap:0.5rem;">'
        f'<span style="font-size:0.64rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;'
        f'background:{mod_col}18;border:1px solid {mod_col}44;color:{mod_col};'
        f'padding:2px 10px;border-radius:20px;">{mod_label}</span>'
        f'<span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;'
        f'background:{conf_col}18;border:1px solid {conf_col}44;color:{conf_col};'
        f'padding:2px 10px;border-radius:20px;">{conf_label}</span>'
        f'</div>'
    )

    # Direct Answer
    if cerna_resp.direct_answer:
        parts += [
            '<div class="resp-sec">',
            '<div class="resp-sec-label">DIRECT ANSWER</div>',
            f'<div class="resp-sec-body">{_md_to_html(cerna_resp.direct_answer)}</div>',
            '</div>',
        ]

    # Context & Explanation
    if cerna_resp.context_explanation:
        parts += [
            '<div class="resp-sec">',
            '<div class="resp-sec-label">CONTEXT &amp; EXPLANATION</div>',
            f'<div class="resp-sec-body">{_md_to_html(cerna_resp.context_explanation)}</div>',
            '</div>',
        ]

    # Step-by-step (only if non-empty)
    if cerna_resp.step_by_step:
        steps_html = "".join(
            f'<div style="margin:0.25rem 0 0.25rem 0.5rem;">'
            f'<span style="color:#8B9DB0;font-weight:600;">{i}.</span> {_md_to_html(s)}</div>'
            for i, s in enumerate(cerna_resp.step_by_step, 1)
        )
        parts += [
            '<div class="resp-sec">',
            '<div class="resp-sec-label">STEP-BY-STEP GUIDE</div>',
            f'<div class="resp-sec-body">{steps_html}</div>',
            '</div>',
        ]

    # Best Practices
    if cerna_resp.best_practices:
        bps_html = "".join(
            f'<div style="margin:0.2rem 0 0.2rem 0.5rem;color:#96B0C8;">◦ {_md_to_html(bp)}</div>'
            for bp in cerna_resp.best_practices
        )
        parts += [
            '<div class="resp-sec">',
            '<div class="resp-sec-label">BEST PRACTICES</div>',
            f'<div class="resp-sec-body">{bps_html}</div>',
            '</div>',
        ]

    # Recommendations
    if cerna_resp.recommendations:
        parts += [
            '<div class="resp-sec">',
            '<div class="resp-sec-label">RECOMMENDATIONS</div>',
            f'<div class="resp-sec-body">{_md_to_html(cerna_resp.recommendations)}</div>',
            '</div>',
        ]

    # Source pills with source_quality badge
    src_list = sources or []
    if src_list:
        pills = []
        for s in src_list[:5]:
            sq = s.get("source_quality", "secondary")
            if sq == "archival_secondary":
                pills.append(
                    f'<span class="src-pill src-pill-archival" '
                    f'title="Archival community documentation — verify before implementing">'
                    f'{s["source"]} ⚠</span>'
                )
            elif sq == "primary":
                pills.append(f'<span class="src-pill src-pill-primary">{s["source"]}</span>')
            else:
                pills.append(f'<span class="src-pill">{s["source"]}</span>')
        parts.append(f'<div class="src-row">{"".join(pills)}</div>')

    parts.append('</div>')

    # Per-module coverage banner
    module_key = (classification or "").lower()
    banner_text = _MODULE_BANNERS.get(module_key)
    if banner_text:
        parts.append(
            f'<div class="module-banner module-banner-{module_key}">'
            f'<span class="module-banner-icon">ℹ</span> {banner_text}'
            f'</div>'
        )

    st.markdown("".join(parts), unsafe_allow_html=True)


def render_structured_response(
    plain: str,
    sections: dict[str, str],
    sources: list[dict],
) -> None:
    parts = ['<div class="resp-card">']
    if plain:
        parts.append(
            f'<div class="resp-sec-body resp-intro">{_md_to_html(plain)}</div>'
        )
    for sec in RESPONSE_SECTIONS:
        if sec not in sections:
            continue
        parts += [
            '<div class="resp-sec">',
            f'<div class="resp-sec-label">{sec}</div>',
            f'<div class="resp-sec-body">{_md_to_html(sections[sec])}</div>',
            '</div>',
        ]
    if sources:
        pills = "".join(
            f'<span class="src-pill">{s["source"]}</span>'
            for s in sources[:5]
        )
        parts.append(f'<div class="src-row">{pills}</div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_followups(follow_ups: list[str], msg_index: int) -> None:
    if not follow_ups:
        return
    st.markdown(
        '<div style="margin-top:1.2rem;border-top:1px solid rgba(123,63,228,0.08);padding-top:0.8rem;margin-bottom:0.6rem;">'
        '<span style="font-size:0.58rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;'
        'color:rgba(123,63,228,0.4);">Suggested questions</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    for qi, q in enumerate(follow_ups[:2]):
        display = q if len(q) <= 90 else q[:87] + "…"
        if st.button(f"↗  {display}", key=f"fu_{msg_index}_{qi}"):
            st.session_state.pending_prompt = q
            st.rerun()
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)


def render_features_panel() -> None:
    """Right-side features panel — always-visible categorised topic shortcuts."""
    st.markdown(
        '<div class="features-panel-title">Knowledge Areas</div>',
        unsafe_allow_html=True,
    )
    for category, items in FEATURES.items():
        st.markdown(f'<div class="feature-cat-title">{category}</div>', unsafe_allow_html=True)
        for label, prompt in items:
            if st.button(label, key=f"feat_{label}", use_container_width=True):
                st.session_state.pending_prompt = prompt
                st.rerun()
        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)


def render_chat(messages: list[dict]) -> None:
    for i, msg in enumerate(messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div class="msg-user-wrap">'
                f'<div class="msg-user">{msg["content"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            cerna_resp = msg.get("cerna_response")
            if cerna_resp is not None:
                render_cerna_response(
                    cerna_resp,
                    msg.get("sources", []),
                    classification=msg.get("vertical"),
                )
            else:
                # Legacy fallback: plain markdown messages
                plain, sections = _parse_response(msg["content"])
                render_structured_response(plain, sections, msg.get("sources", []))
            if i == len(messages) - 1:
                render_followups(msg.get("follow_ups", []), i)
