"""Rebound colour palette, theme variables, and global Streamlit CSS."""

from __future__ import annotations

import streamlit as st


PALETTE: dict[str, str] = {
    "honeydew": "#F6FFEA",
    "peach": "#FFDE96",
    "coral": "#FA855A",
    "tomato": "#C93638",
    "sky": "#62C4DA",
    "navy": "#17233A",
    "warm_white": "#FFFCF8",
    "soft_green": "#E8F7DE",
    "amber": "#FFDE96",
    "purple": "#8B72D8",
    "neutral_border": "#E5E8EF",
}

DESIGN_TOKENS: dict[str, dict[str, str]] = {
    "radius": {"control": "12px", "card": "20px", "shell": "22px", "pill": "999px"},
    "shadow": {
        "card": "0 8px 26px rgba(23,35,58,.055)",
        "raised": "0 18px 52px rgba(23,35,58,.09)",
    },
    "spacing": {"xs": "6px", "sm": "10px", "md": "16px", "lg": "24px", "xl": "32px"},
}


def theme_vars(theme: str) -> dict[str, str]:
    """Return the CSS colour values for a named Rebound theme."""
    if theme == "dark":
        return {
            "app_bg": "#080A0F",
            "surface": "#12161E",
            "elevated": "#181D27",
            "text": "#F7F8FA",
            "muted": "#A7AFBE",
            "border": "#2A303B",
            "dot": "#232A36",
            "glow": (
                "radial-gradient(900px 500px at 12% -10%, rgba(250,133,90,.10), transparent 60%),"
                "radial-gradient(900px 520px at 92% 0%, rgba(98,196,218,.10), transparent 60%),"
                "radial-gradient(700px 520px at 50% 120%, rgba(246,255,234,.04), transparent 60%)"
            ),
        }
    return {
        "app_bg": "#FFFFFF",
        "surface": "#FFFFFF",
        "elevated": "#FFFFFF",
        "text": "#17233A",
        "muted": "#667085",
        "border": "#E5E8EF",
        "dot": "#E5E8EF",
        "glow": (
            "radial-gradient(820px 460px at 8% -8%, rgba(98,196,218,.16), transparent 60%),"
            "radial-gradient(820px 460px at 96% -6%, rgba(250,133,90,.13), transparent 60%),"
            "radial-gradient(900px 560px at 50% 120%, rgba(255,222,150,.15), transparent 62%),"
            "radial-gradient(1100px 720px at 50% 45%, rgba(246,255,234,.5), transparent 70%)"
        ),
    }


def theme_css(theme: str) -> str:
    """Build the global CSS block for the selected theme."""
    v = theme_vars(theme)
    p = PALETTE
    return f"""
<style>
:root {{
  --app-bg:{v['app_bg']}; --surface:{v['surface']}; --surface-elevated:{v['elevated']};
  --text-primary:{v['text']}; --text-muted:{v['muted']}; --border:{v['border']};
  --primary:{p['coral']}; --secondary:{p['sky']}; --warning:{p['peach']};
  --danger:{p['tomato']}; --success:{p['honeydew']};
  --rb-navy:{p['navy']}; --rb-coral:{p['coral']}; --rb-warm-white:{p['warm_white']};
  --rb-soft-green:{p['soft_green']}; --rb-sky:{p['sky']}; --rb-amber:{p['amber']};
  --rb-purple:{p['purple']}; --rb-neutral-border:{p['neutral_border']};
  --rb-radius-control:{DESIGN_TOKENS['radius']['control']};
  --rb-radius-card:{DESIGN_TOKENS['radius']['card']};
  --rb-radius-shell:{DESIGN_TOKENS['radius']['shell']};
  --rb-shadow-card:{DESIGN_TOKENS['shadow']['card']};
  --rb-shadow-raised:{DESIGN_TOKENS['shadow']['raised']};
}}
.stApp {{ background:{v['glow']}, var(--app-bg); color:var(--text-primary); }}
.block-container {{ max-width:1240px; padding-top:1rem; }}
html, body, [class*="css"] {{ font-family:Inter, Arial, Helvetica, sans-serif; }}
h1,h2,h3,.rb-serif {{ font-family:Georgia,'Times New Roman',serif !important;
  color:var(--text-primary) !important; letter-spacing:.2px; }}
p,li,label,span,div,input,textarea {{ color:var(--text-primary); }}
.rb-muted {{ color:var(--text-muted) !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{
  border:1px solid var(--border) !important; border-radius:20px !important;
  background:var(--surface); box-shadow:0 6px 22px rgba(23,35,58,.06) !important; }}
.stButton>button {{ border-radius:12px; font-weight:600; min-height:42px; }}
.stButton>button[kind="primary"] {{ background:var(--primary); border:1px solid var(--primary); color:#fff; }}
.stButton>button[kind="primary"]:hover {{ filter:brightness(1.05); }}
.stButton>button[kind="secondary"] {{ background:transparent; border:1px solid var(--secondary); color:var(--text-primary); }}
.stButton>button[kind="secondary"]:hover {{ background:rgba(255,222,150,.28); }}
.stButton>button:focus-visible {{ outline:3px solid var(--secondary); outline-offset:2px; }}
/* top nav: even single-row pills with coral active underline */
div[role="radiogroup"] {{ display:flex; flex-wrap:nowrap; justify-content:space-between; width:100%; gap:4px; }}
div[role="radiogroup"] label {{ flex:1 1 0; justify-content:center; text-align:center; white-space:nowrap;
  border:none; border-bottom:3px solid transparent; border-radius:0; padding:6px 6px; background:transparent;
  color:var(--text-muted); font-size:.92rem; }}
div[role="radiogroup"] label>div:first-child {{ display:none !important; }}
div[role="radiogroup"] label:hover {{ color:var(--text-primary); }}
div[role="radiogroup"] label:has(input:checked) {{ color:var(--primary); border-bottom-color:var(--primary); font-weight:700; }}
[data-testid="stAlert"] {{ border-radius:14px; }}
[data-testid="stProgressBar"] div div div div {{ background:var(--primary); }}
.rb-chip {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:700; }}
.rb-canvas {{ background-image:radial-gradient(circle, {v['dot']} 1.2px, transparent 1.2px);
  background-size:22px 22px; border:1px solid var(--border); border-radius:16px; padding:10px; }}
.rb-sess {{ border:1px solid var(--border); border-radius:16px; padding:14px 16px; margin-bottom:10px; }}
.rb-evt {{ border:1px solid var(--border); border-radius:12px; padding:8px 10px; margin:6px 0; }}
.rb-evt .t {{ font-weight:700; font-size:.85rem; line-height:1.2; }}
.rb-evt .m {{ font-size:.72rem; color:var(--text-muted); }}
.rb-daycol {{ border:1px solid var(--border); border-radius:12px; padding:6px; background:var(--surface); margin-bottom:6px; }}
.rb-today {{ background:rgba(98,196,218,.12); border-color:var(--secondary); }}
.rb-datebadge {{ display:inline-block; min-width:24px; text-align:center; border-radius:8px; padding:1px 6px; font-weight:700; }}
.rb-hero {{ font-family:Georgia,serif; font-size:2.4rem; line-height:1.12; font-weight:700; }}
.rb-feat {{ font-weight:700; }}

/* Setup page ------------------------------------------------------------- */
.st-key-setup_page {{
  position:relative; box-sizing:border-box; width:100%; overflow:hidden; margin-top:1.15rem;
  padding:clamp(1.1rem, 2.8vw, 2.5rem); border:1px solid rgba(255,255,255,.78);
  border-radius:30px; background:
    radial-gradient(520px 360px at -8% 108%, rgba(250,133,90,.13), transparent 66%),
    radial-gradient(460px 320px at 104% -8%, rgba(98,196,218,.13), transparent 64%),
    var(--surface);
  box-shadow:0 24px 70px rgba(23,35,58,.11);
}}
.st-key-setup_intro {{ padding:1.05rem .35rem .8rem; }}
.rb-setup-brand {{ margin-bottom:3.2rem; }}
.rb-setup-kicker {{
  display:inline-flex; align-items:center; gap:7px; margin-bottom:1.5rem;
  padding:7px 12px; border-radius:10px; background:rgba(250,133,90,.12);
  color:#8a3b1e !important; font-size:.78rem; font-weight:750;
}}
.rb-setup-kicker * {{ color:#8a3b1e !important; }}
.rb-setup-hero {{
  max-width:610px; margin:0 0 1.15rem; font-family:Inter,Arial,sans-serif;
  font-size:clamp(2rem, 2.7vw, 2.5rem); line-height:1.1; letter-spacing:-.035em;
  font-weight:820; color:var(--text-primary);
}}
.rb-setup-copy {{
  max-width:520px; margin:0 0 2.25rem; color:var(--text-muted) !important;
  font-size:1rem; line-height:1.65;
}}
.rb-setup-feature-icon {{
  display:flex; align-items:center; justify-content:center; width:44px; height:44px;
  margin-bottom:12px; border-radius:11px;
}}
.rb-setup-feature-icon.mint {{ background:rgba(192,236,169,.34); color:#3f6b1f; }}
.rb-setup-feature-icon.gold {{ background:rgba(255,222,150,.34); color:#8a6817; }}
.rb-setup-feature-icon.blue {{ background:rgba(98,196,218,.18); color:#0d5c6e; }}
.rb-setup-feature-title {{ margin-bottom:5px; font-size:.91rem; font-weight:750; }}
.rb-setup-feature-copy {{
  max-width:150px; color:var(--text-muted) !important; font-size:.78rem; line-height:1.5;
}}
.st-key-setup_form_card {{
  padding:clamp(1.05rem, 2.4vw, 1.8rem) !important; border-radius:24px !important;
  background:var(--surface) !important; box-shadow:0 16px 40px rgba(23,35,58,.09) !important;
}}
.st-key-setup_form_card h3 {{
  margin:0 !important; font-family:Inter,Arial,sans-serif !important;
  font-size:1.35rem !important; letter-spacing:-.02em !important;
}}
.st-key-setup_form_card [data-testid="stCaptionContainer"] {{ color:var(--text-muted); }}
.st-key-setup_form_card [data-baseweb="select"] > div,
.st-key-setup_form_card [data-baseweb="input"] {{
  border-radius:11px !important; border-color:var(--border) !important;
}}
.st-key-setup_form_card [data-testid="stFileUploaderDropzone"] {{
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;
  min-height:126px; padding:24px 20px; border:1.5px dashed #CCD2DD;
  border-radius:16px; background:rgba(98,196,218,.025);
}}
.st-key-setup_form_card [data-testid="stFileUploaderDropzone"] button {{
  border-color:rgba(250,133,90,.3); background:rgba(250,133,90,.09);
  color:#8a3b1e;
}}
.st-key-setup_form_card [data-testid="stFileUploaderDropzoneInstructions"] {{ text-align:center; }}
.st-key-setup_form_card [data-testid="stFileUploaderDropzoneInstructions"] span {{ display:none; }}
.st-key-setup_form_card [data-testid="stFileUploaderDropzoneInstructions"]::before {{
  content:"Drag and drop your PDF here"; display:block; font-size:.84rem; font-weight:650;
}}
.st-key-setup_form_card [data-testid="stFileUploaderDropzoneInstructions"]::after {{
  content:"or click Upload to browse"; display:block; margin-top:2px; color:var(--text-muted);
  font-size:.74rem;
}}
.st-key-setup_form_card [data-testid="stFormSubmitButton"] button {{
  min-height:46px; box-shadow:0 7px 18px rgba(250,133,90,.22);
}}
.st-key-setup_success {{
  padding:1rem !important; border:1px solid #D8EBCB !important;
  border-radius:15px !important; background:#F7FCF3 !important; box-shadow:none !important;
}}
.rb-setup-success-row {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:2px; }}
.rb-setup-success-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:42px; height:42px; border-radius:50%; background:#E8F7DE; color:#3f6b1f !important;
}}
.rb-setup-success-copy {{ padding-top:2px; color:#17233A !important; font-size:.91rem; line-height:1.35; }}
.rb-setup-success-copy strong {{ color:#17233A !important; }}
.st-key-setup_success [data-testid="stCaptionContainer"] {{ color:#667085 !important; }}
.st-key-setup_success button {{ min-height:40px; background:#fff !important; color:#17233A !important; }}
@media (max-width: 900px) {{
  .st-key-setup_page {{ padding:1rem; border-radius:22px; }}
  .rb-setup-brand {{ margin-bottom:1.8rem; }}
  .rb-setup-copy {{ margin-bottom:1.5rem; }}
}}

/* Home dashboard --------------------------------------------------------- */
.st-key-home_dashboard {{ width:100%; max-width:1500px; margin:.8rem auto 1.5rem; }}
.st-key-home_dashboard [data-testid="stColumn"] {{ min-width:0; }}
.st-key-home_main {{ padding:1.25rem !important; border:1px solid var(--border); border-radius:22px;
  background:rgba(255,255,255,.88); box-shadow:0 12px 38px rgba(23,35,58,.055); }}
.rb-home-study-header {{
  display:flex; align-items:center; gap:14px; min-width:0; margin:2px 0 22px;
}}
.rb-home-heading-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:48px; height:48px; border-radius:50%; background:rgba(23,35,58,.045);
}}
.rb-home-heading-copy {{ min-width:0; }}
.rb-home-heading-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px 10px; }}
.rb-home-heading-row h2 {{
  margin:0 !important; font-family:Inter,Arial,sans-serif !important;
  font-size:1.45rem !important; letter-spacing:-.025em !important;
}}
.rb-home-subtitle {{ margin-top:2px; color:var(--text-muted) !important; font-size:.86rem; }}
.rb-home-count {{
  flex:0 0 auto; margin-left:auto; padding:7px 10px; border:1px solid var(--border);
  border-radius:999px; background:var(--surface); color:var(--text-muted) !important;
  font-size:.78rem; white-space:nowrap;
}}
.rb-home-rebuild-badge {{ flex:0 0 auto; margin-left:auto; }}
.rb-home-count strong {{
  display:inline-flex; align-items:center; justify-content:center; min-width:23px; height:23px;
  margin-right:4px; border-radius:50%; background:rgba(23,35,58,.055);
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-home_session_"]) {{
  overflow:hidden; margin-bottom:13px; border:1px solid rgba(23,35,58,.075) !important;
  border-radius:20px !important; box-shadow:0 8px 25px rgba(23,35,58,.05) !important;
}}
[class*="st-key-home_session_"] {{ padding:1.05rem 1.15rem !important; }}
[class*="st-key-home_session_"]:has(.rb-home-session-shell.expanded) {{ padding:1.3rem 1.4rem !important; }}
[class*="st-key-home_session_green_"] {{ background:rgba(232,247,222,.66) !important; }}
[class*="st-key-home_session_blue_"] {{ background:rgba(224,243,250,.72) !important; }}
[class*="st-key-home_session_amber_"] {{ background:rgba(255,241,211,.72) !important; }}
[class*="st-key-home_session_pink_"] {{ background:rgba(252,228,237,.72) !important; }}
[class*="st-key-home_session_purple_"] {{ background:rgba(237,231,251,.72) !important; }}
.rb-home-session-top {{ display:flex; align-items:center; gap:12px; min-width:0; }}
.rb-home-topic-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:52px; height:52px; border:1px solid rgba(255,255,255,.7); border-radius:50%;
  background:rgba(255,255,255,.48); box-shadow:inset 0 0 0 1px rgba(23,35,58,.035); opacity:.96;
}}
.rb-home-session-shell.expanded .rb-home-topic-icon {{ width:62px; height:62px; }}
.rb-home-session-heading {{ flex:1 1 auto; min-width:0; }}
.rb-home-session-title {{
  font-size:1.08rem; font-weight:800; line-height:1.25; overflow-wrap:anywhere;
}}
.rb-home-session-meta {{ margin-top:3px; color:var(--text-muted) !important; font-size:.76rem; }}
.rb-home-session-meta svg {{ margin-right:3px; }}
.rb-home-session-meta span {{ padding:0 4px; color:var(--text-muted) !important; }}
.rb-home-session-badges {{
  display:flex; flex:0 0 auto; flex-wrap:wrap; justify-content:flex-end; gap:4px;
}}
.rb-home-session-description {{ margin-top:7px; color:var(--text-muted) !important;
  font-size:.82rem; line-height:1.5; overflow-wrap:anywhere; }}
.rb-home-subject {{ margin-top:8px; }}
[class*="st-key-home_actions_"] {{ margin:10px 0 2px 74px; }}
[class*="st-key-home_actions_"] [data-testid="stPopover"] button {{ width:100%; min-height:42px; }}
[class*="st-key-home_session_"] [data-testid="stExpander"] {{
  margin-top:8px; border-color:rgba(23,35,58,.10); border-radius:12px;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-home_empty_state) {{
  border-style:dashed !important; border-radius:20px !important; box-shadow:none !important;
}}
.st-key-home_empty_state {{ padding:2.5rem 1.5rem !important; text-align:center; }}
.rb-home-empty-icon {{
  display:flex; align-items:center; justify-content:center; width:52px; height:52px;
  margin:0 auto 12px; border-radius:50%; background:rgba(98,196,218,.14);
}}
.rb-home-empty-title {{ font-size:1rem; font-weight:800; }}
.rb-home-empty-copy {{ margin-top:5px; color:var(--text-muted) !important; font-size:.84rem; }}
div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-home_rail_"]) {{
  margin-bottom:14px; border:1px solid var(--border) !important; border-radius:20px !important;
  background:rgba(255,255,255,.92); box-shadow:0 8px 28px rgba(23,35,58,.055) !important;
}}
[class*="st-key-home_rail_"] {{ padding:1.2rem 1.25rem !important; }}
.rb-home-rail-title {{
  display:flex; align-items:center; gap:8px; margin-bottom:13px;
  font-size:.9rem; font-weight:800;
}}
.rb-home-rail-title.accent-green, .rb-home-rail-title.accent-green * {{ color:#3f8f35 !important; }}
.rb-home-rail-title.accent-coral, .rb-home-rail-title.accent-coral * {{ color:#C93638 !important; }}
.rb-home-rail-title.accent-blue, .rb-home-rail-title.accent-blue * {{ color:#147DA1 !important; }}
.rb-home-metric {{
  margin:0 0 2px; font-family:Inter,Arial,sans-serif; font-size:1.75rem;
  font-weight:820; letter-spacing:-.035em;
}}
.rb-home-metric-caption {{ margin-top:4px; color:var(--text-muted) !important; font-size:.76rem; }}
.rb-home-rail-visual-row {{ display:flex; align-items:center; justify-content:space-between; gap:14px; }}
.rb-home-calendar-art {{ display:flex; align-items:center; justify-content:center; width:62px; height:62px;
  flex:0 0 auto; border-radius:50%; background:rgba(250,133,90,.11); }}
.rb-home-sparkline {{ width:112px; height:50px; overflow:visible; }}
.rb-home-sparkline path {{ fill:none; stroke:#45B957; stroke-width:2.4; stroke-linecap:round; }}
.rb-home-sparkline circle {{ fill:#45B957; }}
.rb-home-progress-layout {{ display:flex; align-items:center; gap:18px; }}
.rb-home-progress-ring {{ display:grid; place-items:center; width:112px; height:112px; flex:0 0 auto;
  border-radius:50%; background:conic-gradient(#54BE62 var(--progress),#D9EFF8 0); }}
.rb-home-progress-ring::before {{ content:""; grid-area:1/1; width:86px; height:86px; border-radius:50%; background:#fff; }}
.rb-home-progress-ring>div {{ z-index:1; grid-area:1/1; display:flex; flex-direction:column; align-items:center; }}
.rb-home-progress-ring strong {{ font-size:1.45rem; line-height:1; }}
.rb-home-progress-ring span {{ margin-top:5px; color:var(--text-muted) !important; font-size:.66rem; }}
.rb-home-progress-legend {{ display:flex; flex-direction:column; gap:9px; min-width:0; font-size:.72rem; }}
.rb-home-progress-legend span {{ display:grid; grid-template-columns:9px 24px 1fr; align-items:center; gap:5px; }}
.rb-home-progress-legend i {{ width:8px; height:8px; border-radius:50%; }}
.rb-home-progress-legend i.completed {{ background:#54BE62; }}
.rb-home-progress-legend i.active {{ background:#5AA9E6; }}
.rb-home-progress-legend i.planned {{ background:#B8C0CC; }}
.st-key-home_rail_quick button {{ min-height:40px; }}
.st-key-home_no_plan {{ padding:1.3rem !important; }}
@media (max-width: 900px) {{
  .st-key-home_dashboard [data-testid="stHorizontalBlock"]:has(.st-key-home_main):has(.st-key-home_rail) {{
    flex-direction:column;
  }}
  .st-key-home_dashboard [data-testid="stHorizontalBlock"]:has(.st-key-home_main):has(.st-key-home_rail)
    > [data-testid="stColumn"] {{ width:100% !important; flex:1 1 100% !important; }}
  .st-key-home_rail {{ margin-top:8px; }}
}}
@media (max-width: 650px) {{
  .rb-home-study-header {{ align-items:flex-start; flex-wrap:wrap; }}
  .rb-home-rebuild-badge {{ margin-left:0; }}
  .rb-home-count {{ width:100%; margin-left:62px; white-space:normal; }}
  .rb-home-session-top {{ align-items:flex-start; flex-wrap:wrap; }}
  .rb-home-session-heading {{ min-width:calc(100% - 56px); }}
  .rb-home-session-badges {{ width:100%; justify-content:flex-start; margin-left:54px; }}
  .rb-home-session-description {{ margin-left:0; }}
  [class*="st-key-home_actions_"] {{ margin-left:0; }}
  [class*="st-key-home_actions_"] [data-testid="stHorizontalBlock"] {{ flex-direction:column; }}
  [class*="st-key-home_actions_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
}}

/* Shared Rebound presentation primitives -------------------------------- */
[class*="st-key-rb_page_"] {{
  box-sizing:border-box; width:100%; max-width:100%; overflow-x:clip;
  padding:clamp(1rem, 2.5vw, 1.75rem) !important;
}}
.rb-ui-page-header {{
  display:flex; align-items:center; gap:14px; min-width:0; margin:0 0 1.5rem;
}}
.rb-ui-page-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:50px; height:50px; border-radius:14px; background:rgba(250,133,90,.11);
}}
.rb-ui-page-heading {{ min-width:0; }}
.rb-ui-page-title-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px 10px; }}
.rb-ui-page-title-row h1 {{
  margin:0 !important; font-family:Inter,Arial,sans-serif !important;
  font-size:clamp(1.55rem, 2.5vw, 2rem) !important; font-weight:820;
  line-height:1.15; letter-spacing:-.035em; overflow-wrap:anywhere;
}}
.rb-ui-page-subtitle {{ margin-top:4px; color:var(--text-muted) !important; font-size:.9rem; }}
.rb-ui-section-header {{
  display:flex; align-items:center; gap:10px; min-width:0; margin:0 0 1rem;
}}
.rb-ui-section-icon {{ display:flex; flex:0 0 auto; align-items:center; justify-content:center; }}
.rb-ui-section-copy {{ flex:1 1 auto; min-width:0; }}
.rb-ui-section-copy h2 {{
  margin:0 !important; font-family:Inter,Arial,sans-serif !important;
  font-size:1.18rem !important; font-weight:800; letter-spacing:-.02em;
  overflow-wrap:anywhere;
}}
.rb-ui-section-subtitle {{ margin-top:2px; color:var(--text-muted) !important; font-size:.8rem; }}
.rb-ui-section-trailing {{
  flex:0 0 auto; color:var(--text-muted) !important; font-size:.78rem; text-align:right;
}}
[class*="st-key-rb_card_"], [class*="st-key-rb_metric_"],
[class*="st-key-rb_insight_"], [class*="st-key-rb_feedback_"],
[class*="st-key-rb_empty_"] {{
  box-sizing:border-box; width:100%; min-width:0; margin-bottom:1rem;
  padding:1.15rem 1.25rem !important; border:1px solid var(--rb-neutral-border);
  border-radius:var(--rb-radius-card); background:var(--surface);
  box-shadow:var(--rb-shadow-card);
}}
[class*="st-key-rb_insight_"] {{ padding:1rem 1.05rem !important; }}
[class*="st-key-rb_card_coral_"], [class*="st-key-rb_metric_coral_"],
[class*="st-key-rb_insight_coral_"], [class*="st-key-rb_feedback_coral_"] {{
  background:rgba(250,133,90,.07);
}}
[class*="st-key-rb_card_green_"], [class*="st-key-rb_metric_green_"],
[class*="st-key-rb_insight_green_"], [class*="st-key-rb_feedback_green_"] {{
  background:rgba(232,247,222,.62);
}}
[class*="st-key-rb_card_blue_"], [class*="st-key-rb_metric_blue_"],
[class*="st-key-rb_insight_blue_"], [class*="st-key-rb_feedback_blue_"] {{
  background:rgba(224,243,250,.65);
}}
[class*="st-key-rb_card_amber_"], [class*="st-key-rb_metric_amber_"],
[class*="st-key-rb_insight_amber_"], [class*="st-key-rb_feedback_amber_"] {{
  background:rgba(255,241,211,.68);
}}
[class*="st-key-rb_card_purple_"], [class*="st-key-rb_metric_purple_"],
[class*="st-key-rb_insight_purple_"], [class*="st-key-rb_feedback_purple_"] {{
  background:rgba(237,231,251,.68);
}}
[class*="st-key-rb_card_danger_"], [class*="st-key-rb_metric_danger_"],
[class*="st-key-rb_insight_danger_"], [class*="st-key-rb_feedback_danger_"] {{
  background:rgba(201,54,56,.07);
}}
.rb-ui-badge {{
  display:inline-flex; align-items:center; width:max-content; max-width:100%;
  padding:4px 9px; border:1px solid transparent; border-radius:999px;
  font-size:.7rem; font-weight:800; line-height:1.25; overflow-wrap:anywhere;
}}
.rb-ui-tone-neutral {{ background:rgba(23,35,58,.06); color:var(--text-muted) !important; }}
.rb-ui-tone-coral {{ background:rgba(250,133,90,.13); color:#8a3b1e !important; }}
.rb-ui-tone-green {{ background:rgba(232,247,222,.9); color:#3f6b1f !important; }}
.rb-ui-tone-blue {{ background:rgba(224,243,250,.9); color:#0d5c6e !important; }}
.rb-ui-tone-amber {{ background:rgba(255,241,211,.95); color:#7a5a17 !important; }}
.rb-ui-tone-purple {{ background:rgba(237,231,251,.95); color:#4b3f7a !important; }}
.rb-ui-tone-danger {{ background:rgba(201,54,56,.11); color:#8a1f1f !important; }}
.rb-ui-metric-label {{
  display:flex; align-items:center; gap:7px; margin-bottom:.65rem;
  color:var(--text-muted) !important; font-size:.78rem; font-weight:750;
}}
.rb-ui-metric-value {{
  font-size:1.75rem; font-weight:820; line-height:1.15; letter-spacing:-.035em;
  overflow-wrap:anywhere;
}}
.rb-ui-metric-caption {{ margin-top:4px; color:var(--text-muted) !important; font-size:.76rem; }}
.rb-ui-feedback-content {{ display:flex; align-items:flex-start; gap:11px; }}
.rb-ui-feedback-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:34px; height:34px; border-radius:50%; background:rgba(255,255,255,.56);
}}
.rb-ui-feedback-title {{ font-size:.9rem; font-weight:800; }}
.rb-ui-feedback-message {{
  margin-top:3px; color:var(--text-muted) !important; font-size:.8rem; line-height:1.5;
  overflow-wrap:anywhere;
}}
[class*="st-key-rb_empty_"] {{ text-align:center; border-style:dashed; box-shadow:none; }}
.rb-ui-empty-icon {{
  display:flex; align-items:center; justify-content:center; width:50px; height:50px;
  margin:0 auto 11px; border-radius:50%; background:rgba(98,196,218,.13);
}}
.rb-ui-empty-title {{ font-size:.95rem; font-weight:800; }}
.rb-ui-empty-message {{
  max-width:540px; margin:5px auto 0; color:var(--text-muted) !important;
  font-size:.8rem; line-height:1.5; overflow-wrap:anywhere;
}}
.rb-ui-progress-label {{
  display:flex; align-items:center; justify-content:space-between; gap:12px;
  margin-bottom:6px; font-size:.78rem; font-weight:750;
}}
[class*="st-key-rb_progress_"] [data-testid="stProgress"] [data-testid="stProgressBarTrack"] > div {{
  background:var(--rb-coral) !important;
}}
[class*="st-key-rb_primary_actions_"], [class*="st-key-rb_secondary_actions_"] {{
  box-sizing:border-box; width:100%; padding:.85rem 0 0 !important;
}}
[class*="st-key-rb_primary_actions_"] {{ border-top:1px solid var(--rb-neutral-border); }}
[class*="st-key-rb_primary_actions_"] [data-testid="stButton"] button {{
  background:var(--rb-coral); border-color:var(--rb-coral); color:#fff;
}}
[class*="st-key-rb_secondary_actions_"] [data-testid="stButton"] button {{
  background:var(--surface); border-color:var(--rb-neutral-border); color:var(--text-primary);
}}
[class*="st-key-rb_primary_actions_"] [data-testid="stButton"] button:focus-visible,
[class*="st-key-rb_secondary_actions_"] [data-testid="stButton"] button:focus-visible,
[class*="st-key-rb_button_row_"] [data-testid="stButton"] button:focus-visible {{
  outline:3px solid var(--rb-sky); outline-offset:2px;
}}
[class*="st-key-rb_button_row_"] {{ box-sizing:border-box; width:100%; }}
[class*="st-key-rb_button_row_"] [data-testid="stColumn"] {{ min-width:0; }}
@media (max-width: 800px) {{
  [class*="st-key-rb_page_"] {{ padding:.85rem !important; }}
  .rb-ui-page-header, .rb-ui-section-header {{ align-items:flex-start; flex-wrap:wrap; }}
  .rb-ui-section-trailing {{ width:100%; text-align:left; }}
  [class*="st-key-rb_button_row_"] [data-testid="stHorizontalBlock"] {{ flex-direction:column; }}
  [class*="st-key-rb_button_row_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
  [class*="st-key-rb_button_row_"] [data-testid="stButton"] button {{ width:100%; }}
}}

/* Diagnostic question layout V2 ----------------------------------------- */
[class*="st-key-rb_page_diagnostic_question"] {{
  max-width:1240px; margin:1rem auto 1.5rem; padding:clamp(1.1rem, 2.6vw, 2rem) !important;
  border:1px solid rgba(229,232,239,.9); border-radius:22px;
  background:var(--rb-warm-white); box-shadow:var(--rb-shadow-raised);
}}
[class*="st-key-rb_card_neutral_diagnostic_header"] {{
  margin-bottom:1.35rem; padding:1.15rem 1.25rem !important;
  background:rgba(255,255,255,.74); box-shadow:none;
}}
[class*="st-key-rb_card_neutral_diagnostic_header"] .rb-ui-page-header {{ margin:0; }}
[class*="st-key-rb_card_neutral_diagnostic_header"] .rb-ui-page-icon {{ width:48px; height:48px; }}
[class*="st-key-rb_card_neutral_diagnostic_header"] .rb-ui-page-title-row h1 {{ font-size:1.4rem !important; }}
[class*="st-key-rb_card_neutral_diagnostic_header"]
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] + [data-testid="stColumn"] {{
  border-left:1px solid var(--rb-neutral-border); padding-left:1.35rem;
}}
[class*="st-key-rb_progress_diagnostic_header"] {{ width:100%; }}
[class*="st-key-rb_progress_diagnostic_header"] .rb-ui-progress-label {{
  color:var(--rb-coral) !important;
}}
.rb-diagnostic-v2-metadata {{
  display:flex; align-items:center; justify-content:flex-end; gap:9px;
  min-width:0; flex-wrap:wrap;
}}
.rb-diagnostic-v2-metadata .rb-ui-badge {{
  min-height:38px; justify-content:center; padding:7px 11px; text-align:center;
}}
[class*="st-key-rb_card_coral_diagnostic_question"] {{
  padding:clamp(1.25rem, 2.8vw, 2rem) !important;
  border-color:rgba(250,133,90,.18); background:#FFFAF6;
  box-shadow:0 8px 28px rgba(23,35,58,.045);
}}
.rb-diagnostic-v2-number {{ color:var(--rb-coral) !important; font-size:1.05rem; font-weight:820; }}
.rb-diagnostic-v2-marks {{ display:flex; justify-content:flex-end; }}
.rb-diagnostic-v2-question {{
  max-width:960px; margin:1.15rem 0 1rem; font-size:clamp(1.25rem, 2.2vw, 1.6rem);
  font-weight:680; line-height:1.42; letter-spacing:-.022em; overflow-wrap:anywhere;
}}
.rb-diagnostic-v2-subject {{ margin-bottom:1rem; }}
[class*="st-key-rb_card_coral_diagnostic_question"] [data-testid="stTextArea"] textarea {{
  min-height:240px; padding:1.05rem !important; border:1px solid var(--rb-neutral-border) !important;
  border-radius:14px !important; background:var(--surface) !important;
  font-size:.96rem; line-height:1.55;
}}
[class*="st-key-rb_card_coral_diagnostic_question"] [data-testid="stTextArea"] textarea:focus {{
  border-color:var(--rb-sky) !important; box-shadow:0 0 0 3px rgba(98,196,218,.14) !important;
}}
.rb-diagnostic-v2-helper {{
  display:flex; align-items:flex-start; gap:9px; margin-top:.65rem;
  color:var(--text-muted) !important; font-size:.8rem; line-height:1.5;
}}
.rb-diagnostic-v2-helper * {{ color:var(--text-muted) !important; }}
.rb-diagnostic-v2-helper-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:28px; height:28px; border-radius:50%; background:rgba(250,133,90,.10);
}}
[class*="st-key-rb_page_diagnostic_question"] [role="separator"] {{ margin:1.25rem 0; }}
[class*="st-key-rb_button_row_diagnostic_navigation"] [data-testid="stButton"] button {{
  min-height:48px; border-color:var(--rb-neutral-border);
}}
[class*="st-key-rb_button_row_diagnostic_navigation"] [class*="st-key-dq_finish"] button {{
  background:var(--rb-coral); border-color:var(--rb-coral); color:#fff;
  box-shadow:0 8px 20px rgba(250,133,90,.22);
}}
@media (max-width: 850px) {{
  [class*="st-key-rb_card_neutral_diagnostic_header"] [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_header"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
    border-left:0 !important; padding-left:0 !important;
  }}
  .rb-diagnostic-v2-metadata {{ justify-content:flex-start; }}
}}
@media (min-width: 651px) and (max-width: 800px) {{
  [class*="st-key-rb_button_row_diagnostic_navigation"] [data-testid="stHorizontalBlock"] {{
    flex-direction:row;
  }}
  [class*="st-key-rb_button_row_diagnostic_navigation"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:auto !important; flex:1 1 0 !important;
  }}
}}
@media (max-width: 650px) {{
  [class*="st-key-rb_page_diagnostic_question"] {{
    margin:.65rem auto 1rem; padding:.75rem !important; border-radius:18px;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_header"],
  [class*="st-key-rb_card_coral_diagnostic_question"] {{ padding:1rem !important; }}
  .rb-diagnostic-v2-marks {{ justify-content:flex-start; }}
  .rb-diagnostic-v2-question {{ font-size:1.18rem; }}
  [class*="st-key-rb_button_row_diagnostic_navigation"] [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_button_row_diagnostic_navigation"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
}}

/* Diagnostic results layout V2 ------------------------------------------ */
[class*="st-key-rb_page_diagnostic_results"] {{
  max-width:1240px; margin:1rem auto 1.5rem; padding:clamp(1rem, 2.2vw, 1.75rem) !important;
  overflow:hidden; border:1px solid rgba(229,232,239,.9); border-radius:22px;
  background:var(--rb-warm-white); box-shadow:var(--rb-shadow-raised);
}}
[class*="st-key-rb_card_neutral_diagnostic_results_header"] {{
  margin-bottom:1.35rem; padding:1.1rem 1.25rem !important;
  background:rgba(255,255,255,.78); box-shadow:none;
}}
[class*="st-key-rb_card_neutral_diagnostic_results_header"] .rb-ui-page-header {{ margin:0; }}
[class*="st-key-rb_card_neutral_diagnostic_results_header"] .rb-ui-page-icon {{ width:48px; height:48px; }}
[class*="st-key-rb_card_neutral_diagnostic_results_header"] .rb-ui-page-title-row h1 {{ font-size:1.4rem !important; }}
[class*="st-key-rb_card_neutral_diagnostic_results_header"]
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] + [data-testid="stColumn"] {{
  border-left:1px solid var(--rb-neutral-border); padding-left:1.35rem;
}}
[class*="st-key-rb_progress_diagnostic_results_completion"] .rb-ui-progress-label {{
  color:var(--rb-coral) !important;
}}
[class*="st-key-rb_progress_diagnostic_results_completion"] [data-testid="stCaptionContainer"] {{
  color:var(--text-muted); font-size:.76rem;
}}
[class*="st-key-rb_card_neutral_diagnostic_results_review"] {{
  min-width:0; padding:clamp(1.2rem, 2.3vw, 1.8rem) !important;
  background:#fff; box-shadow:0 8px 28px rgba(23,35,58,.045);
}}
.rb-results-question-number {{ color:var(--rb-coral) !important; font-size:1rem; font-weight:820; }}
.rb-results-marks {{ display:flex; justify-content:flex-end; }}
.rb-results-question {{
  margin:1rem 0 .85rem; font-size:clamp(1.2rem, 2vw, 1.5rem); font-weight:700;
  line-height:1.42; letter-spacing:-.02em; overflow-wrap:anywhere;
}}
.rb-results-subject {{ margin-bottom:1.25rem; }}
.rb-results-label {{ margin-bottom:.45rem; color:var(--text-muted) !important; font-size:.8rem; font-weight:750; }}
.rb-results-answer {{
  min-height:100px; margin-bottom:1.1rem; padding:1rem 1.05rem; border:1px solid var(--rb-neutral-border);
  border-radius:14px; background:rgba(255,255,255,.75); font-size:.93rem; line-height:1.62;
  white-space:pre-wrap; overflow-wrap:anywhere;
}}
[class*="st-key-rb_card_green_diagnostic_results_correct"],
[class*="st-key-rb_card_danger_diagnostic_results_missing"],
[class*="st-key-rb_card_amber_diagnostic_results_misconceptions"] {{
  height:100%; margin-bottom:.85rem; padding:1rem !important; border-radius:16px;
  box-shadow:none;
}}
.rb-results-feedback-title {{
  display:flex; align-items:center; gap:8px; margin-bottom:.65rem; font-size:.87rem; font-weight:820;
}}
.rb-results-feedback-title-green, .rb-results-feedback-title-green * {{ color:#3f6b1f !important; }}
.rb-results-feedback-title-danger, .rb-results-feedback-title-danger * {{ color:#8a1f1f !important; }}
.rb-results-feedback-list {{ margin:.15rem 0 0; padding-left:1.15rem; }}
.rb-results-feedback-list li {{
  margin:.36rem 0; color:var(--text-muted) !important; font-size:.79rem; line-height:1.45;
  overflow-wrap:anywhere;
}}
.rb-results-empty-feedback {{ color:var(--text-muted) !important; font-size:.79rem; }}
[class*="st-key-rb_results_improvement"] {{
  margin:.15rem 0 .85rem; padding:1rem 1.05rem !important; border:1px solid var(--rb-neutral-border);
  border-radius:16px; background:rgba(255,255,255,.7);
}}
.rb-results-score-line {{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }}
.rb-results-score-line > span:last-child {{ display:inline-flex; align-items:center; gap:7px; font-size:.86rem; }}
.rb-results-improvement-copy {{
  margin:.55rem 0 0; padding-left:calc(14px + 5.6rem); color:var(--text-muted) !important;
  font-size:.81rem; line-height:1.5; overflow-wrap:anywhere;
}}
[class*="st-key-rb_insight_coral_diagnostic_results_score"] {{
  padding:1.5rem 1.1rem !important; text-align:center; border-color:rgba(250,133,90,.18);
}}
.rb-results-overall-score {{
  color:var(--rb-coral) !important; font-size:clamp(2.7rem, 5vw, 4rem); font-weight:850;
  line-height:1; letter-spacing:-.055em;
}}
.rb-results-overall-caption {{ margin-top:.75rem; font-size:.86rem; font-weight:650; }}
[class*="st-key-rb_insight_neutral_diagnostic_results_overview"] {{ padding:1.15rem !important; }}
.rb-results-overview-title {{ margin-bottom:.75rem; font-size:1rem; font-weight:820; }}
.rb-results-legend {{ display:flex; gap:9px; margin-bottom:.8rem; flex-wrap:wrap; }}
.rb-results-legend span {{
  display:inline-flex; align-items:center; gap:5px; color:var(--text-muted) !important;
  font-size:.67rem; white-space:nowrap;
}}
.rb-results-legend i {{ width:8px; height:8px; border-radius:50%; }}
.rb-results-legend i.green {{ background:#34B56A; }}
.rb-results-legend i.amber {{ background:#F4B51E; }}
.rb-results-legend i.red {{ background:#E8504F; }}
[class*="st-key-rb_result_overview_"] {{ margin:.48rem 0; padding:0 !important; border-radius:12px; }}
[class*="st-key-rb_result_overview_"] [data-testid="stButton"] button {{
  min-height:52px; padding:.55rem .7rem; border:1px solid transparent; border-radius:12px;
  box-shadow:none; font-size:.74rem; text-align:left; white-space:normal;
}}
[class*="st-key-rb_result_overview_green_"] [data-testid="stButton"] button {{ background:rgba(232,247,222,.72); }}
[class*="st-key-rb_result_overview_amber_"] [data-testid="stButton"] button {{ background:rgba(255,241,211,.78); }}
[class*="st-key-rb_result_overview_danger_"] [data-testid="stButton"] button {{ background:rgba(201,54,56,.075); }}
[class*="st-key-rb_result_overview_"][class*="_selected_"] [data-testid="stButton"] button {{
  border-color:var(--rb-sky); box-shadow:0 0 0 2px rgba(98,196,218,.12);
}}
[class*="st-key-rb_button_row_diagnostic_results_actions"] {{ max-width:560px; margin-left:auto; }}
[class*="st-key-rb_button_row_diagnostic_results_actions"] [data-testid="stButton"] button {{
  min-height:48px; border-color:var(--rb-neutral-border);
}}
[class*="st-key-rb_button_row_diagnostic_results_actions"] [class*="st-key-res_plan"] button {{
  background:var(--rb-coral); border-color:var(--rb-coral); color:#fff;
  box-shadow:0 8px 20px rgba(250,133,90,.22);
}}
@media (max-width: 900px) {{
  [class*="st-key-rb_results_main_layout"] > div > [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_results_main_layout"] > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_results_header"] [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_results_header"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important; border-left:0 !important; padding-left:0 !important;
  }}
}}
@media (min-width: 651px) and (max-width: 800px) {{
  [class*="st-key-rb_button_row_diagnostic_results_actions"] [data-testid="stHorizontalBlock"] {{
    flex-direction:row;
  }}
  [class*="st-key-rb_button_row_diagnostic_results_actions"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:auto !important; flex:1 1 0 !important;
  }}
}}
@media (max-width: 650px) {{
  [class*="st-key-rb_page_diagnostic_results"] {{
    margin:.65rem auto 1rem; padding:.75rem !important; border-radius:18px;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_results_header"],
  [class*="st-key-rb_card_neutral_diagnostic_results_review"] {{ padding:1rem !important; }}
  .rb-results-marks {{ justify-content:flex-start; }}
  .rb-results-improvement-copy {{ padding-left:0; }}
  [class*="st-key-rb_card_neutral_diagnostic_results_review"] [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_card_neutral_diagnostic_results_review"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
  [class*="st-key-rb_button_row_diagnostic_results_actions"] [data-testid="stHorizontalBlock"] {{
    flex-direction:column;
  }}
  [class*="st-key-rb_button_row_diagnostic_results_actions"]
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
}}

</style>
"""


def inject_css() -> None:
    """Inject the active theme's CSS into the Streamlit page."""
    st.markdown(
        theme_css(st.session_state.get("theme", "light")),
        unsafe_allow_html=True,
    )
