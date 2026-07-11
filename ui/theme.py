"""Rebound colour palette, theme variables, and global Streamlit CSS."""

import streamlit as st


PALETTE = {
    "honeydew": "#F6FFEA",
    "peach": "#FFDE96",
    "coral": "#FA855A",
    "tomato": "#C93638",
    "sky": "#62C4DA",
}


def theme_vars(theme):
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


def theme_css(theme):
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
.st-key-home_dashboard {{ width:100%; max-width:100%; margin-top:.65rem; }}
.st-key-home_dashboard [data-testid="stColumn"] {{ min-width:0; }}
.rb-home-study-header {{
  display:flex; align-items:center; gap:14px; min-width:0; margin:2px 0 18px;
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
.rb-home-count strong {{
  display:inline-flex; align-items:center; justify-content:center; min-width:23px; height:23px;
  margin-right:4px; border-radius:50%; background:rgba(23,35,58,.055);
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-home_session_"]) {{
  overflow:hidden; margin-bottom:11px; border-radius:20px !important;
  box-shadow:0 7px 22px rgba(23,35,58,.045) !important;
}}
[class*="st-key-home_session_"] {{ padding:1rem 1.05rem !important; }}
[class*="st-key-home_session_green_"] {{ background:rgba(232,247,222,.66) !important; }}
[class*="st-key-home_session_blue_"] {{ background:rgba(224,243,250,.72) !important; }}
[class*="st-key-home_session_amber_"] {{ background:rgba(255,241,211,.72) !important; }}
[class*="st-key-home_session_pink_"] {{ background:rgba(252,228,237,.72) !important; }}
[class*="st-key-home_session_purple_"] {{ background:rgba(237,231,251,.72) !important; }}
.rb-home-session-top {{ display:flex; align-items:center; gap:12px; min-width:0; }}
.rb-home-topic-icon {{
  display:flex; flex:0 0 auto; align-items:center; justify-content:center;
  width:42px; height:42px; border:1px solid currentColor; border-radius:50%; opacity:.92;
}}
.rb-home-session-heading {{ flex:1 1 auto; min-width:0; }}
.rb-home-session-title {{
  font-size:1.08rem; font-weight:800; line-height:1.25; overflow-wrap:anywhere;
}}
.rb-home-session-meta {{ margin-top:3px; color:var(--text-muted) !important; font-size:.76rem; }}
.rb-home-session-badges {{
  display:flex; flex:0 0 auto; flex-wrap:wrap; justify-content:flex-end; gap:4px;
}}
.rb-home-session-points {{
  margin:9px 0 10px 54px; color:var(--text-muted) !important;
  font-size:.83rem; line-height:1.5; overflow-wrap:anywhere;
}}
[class*="st-key-home_actions_"] {{ margin-top:3px; }}
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
  margin-bottom:12px; border-radius:20px !important;
  box-shadow:0 7px 22px rgba(23,35,58,.05) !important;
}}
[class*="st-key-home_rail_"] {{ padding:1rem 1.05rem !important; }}
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
.st-key-home_rail_progress [data-testid="stProgressBar"] {{ margin:.5rem 0 .65rem; }}
.st-key-home_rail_recovery {{ background:rgba(250,133,90,.045) !important; }}
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
  .rb-home-count {{ width:100%; margin-left:62px; white-space:normal; }}
  .rb-home-session-top {{ align-items:flex-start; flex-wrap:wrap; }}
  .rb-home-session-heading {{ min-width:calc(100% - 56px); }}
  .rb-home-session-badges {{ width:100%; justify-content:flex-start; margin-left:54px; }}
  .rb-home-session-points {{ margin-left:0; }}
  [class*="st-key-home_actions_"] [data-testid="stHorizontalBlock"] {{ flex-direction:column; }}
  [class*="st-key-home_actions_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important;
  }}
}}
</style>
"""


def inject_css():
    """Inject the active theme's CSS into the Streamlit page."""
    st.markdown(
        theme_css(st.session_state.get("theme", "light")),
        unsafe_allow_html=True,
    )
