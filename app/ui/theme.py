"""
Centralized Theme Configuration & CSS Tokens.
Provides coordinated Light and Dark design tokens, accessible contrast,
and seamless Streamlit component styling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

THEME_LIGHT: Final[str] = "Light"
THEME_DARK: Final[str] = "Dark"
SUPPORTED_THEMES: Final[list[str]] = [THEME_LIGHT, THEME_DARK]


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    bg_app: str
    bg_surface: str
    bg_card: str
    bg_nav: str
    bg_input: str
    border_color: str
    border_subtle: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_primary: str
    accent_hover: str
    status_good_text: str
    status_good_bg: str
    status_good_border: str
    status_bad_text: str
    status_bad_bg: str
    status_bad_border: str
    status_warn_text: str
    status_warn_bg: str
    status_warn_border: str
    status_info_text: str
    status_info_bg: str
    status_info_border: str
    table_header_bg: str
    table_border: str


LIGHT_TOKENS: Final[ThemeTokens] = ThemeTokens(
    name=THEME_LIGHT,
    bg_app="#f8fafc",            # Slate 50
    bg_surface="#ffffff",
    bg_card="#ffffff",
    bg_nav="#ffffff",
    bg_input="#ffffff",
    border_color="#e2e8f0",      # Slate 200
    border_subtle="#cbd5e1",     # Slate 300
    text_primary="#0f172a",      # Slate 900
    text_secondary="#334155",    # Slate 700
    text_muted="#64748b",        # Slate 500
    accent_primary="#2563eb",    # Blue 600
    accent_hover="#1d4ed8",      # Blue 700
    status_good_text="#15803d",  # Green 700
    status_good_bg="#ecfdf5",    # Green 50
    status_good_border="#86efac",
    status_bad_text="#b91c1c",   # Red 700
    status_bad_bg="#fef2f2",     # Red 50
    status_bad_border="#fca5a5",
    status_warn_text="#b45309",  # Amber 700
    status_warn_bg="#fffbeb",    # Amber 50
    status_warn_border="#fde68a",
    status_info_text="#1d4ed8",  # Blue 700
    status_info_bg="#eff6ff",    # Blue 50
    status_info_border="#bfdbfe",
    table_header_bg="#f1f5f9",
    table_border="#e2e8f0",
)

DARK_TOKENS: Final[ThemeTokens] = ThemeTokens(
    name=THEME_DARK,
    bg_app="#0b0f19",            # Dark slate canvas
    bg_surface="#111827",        # Dark surface
    bg_card="#1e293b",           # Slate 800 cards
    bg_nav="#1e293b",            # Slate 800 navigation bar
    bg_input="#1e293b",          # Input background
    border_color="#334155",      # Slate 700 borders
    border_subtle="#475569",     # Slate 600 borders
    text_primary="#f8fafc",      # Slate 50
    text_secondary="#cbd5e1",    # Slate 300
    text_muted="#94a3b8",        # Slate 400
    accent_primary="#3b82f6",    # Blue 500
    accent_hover="#2563eb",      # Blue 600
    status_good_text="#4ade80",  # Green 400
    status_good_bg="#052e16",    # Deep Green
    status_good_border="#166534",
    status_bad_text="#f87171",   # Red 400
    status_bad_bg="#450a0a",     # Deep Red
    status_bad_border="#991b1b",
    status_warn_text="#fbbf24",  # Amber 400
    status_warn_bg="#451a03",    # Deep Amber
    status_warn_border="#b45309",
    status_info_text="#60a5fa",  # Blue 400
    status_info_bg="#172554",    # Deep Blue
    status_info_border="#1e40af",
    table_header_bg="#0f172a",
    table_border="#334155",
)


def get_theme_tokens(theme: str) -> ThemeTokens:
    """Return the ThemeTokens corresponding to the selected theme name."""
    if str(theme).strip().lower() == "dark":
        return DARK_TOKENS
    return LIGHT_TOKENS


def build_theme_stylesheet(theme: str) -> str:
    """
    Generate unified, scoped CSS for all application surfaces,
    cards, badges, navigation, buttons, and tables based on the active theme.
    """
    t = get_theme_tokens(theme)

    return f"""
<style>
/* ========================================================================= */
/* THEME: {t.name.upper()}                                                    */
/* ========================================================================= */

/* App canvas and container layout */
.block-container {{
    max-width: 1240px;
    padding-top: 4.2rem !important;
    padding-bottom: 3.5rem;
    color: {t.text_secondary};
}}

[data-testid="stAppViewContainer"] {{
    background-color: {t.bg_app} !important;
    color: {t.text_primary} !important;
}}

[data-testid="stHeader"] {{
    background-color: transparent !important;
    height: 2.875rem !important;
    z-index: 90 !important;
}}

[data-testid="stMain"] {{
    background-color: {t.bg_app} !important;
    color: {t.text_primary} !important;
}}

/* Typography & Spacing Tokens */
h1 {{
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: {t.text_primary} !important;
    margin-top: 0 !important;
    margin-bottom: 0.25rem !important;
    line-height: 1.25 !important;
}}

p.page-subtitle {{
    font-size: 0.95rem !important;
    color: {t.text_muted} !important;
    margin-top: 0 !important;
    margin-bottom: 1.5rem !important; /* 24px section gap */
    line-height: 1.4 !important;
}}

h2 {{
    font-size: 1.25rem !important;
    font-weight: 650 !important;
    color: {t.text_primary} !important;
    margin-top: 1.5rem !important; /* 24px section gap */
    margin-bottom: 0.5rem !important;
}}

h3 {{
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: {t.text_primary} !important;
    margin-top: 1rem !important; /* 16px standard gap */
    margin-bottom: 0.5rem !important;
}}

.block-container p,
.block-container span:not(button span):not([data-baseweb="tag"] span) {{
    color: {t.text_secondary};
}}

.block-container label:not([data-baseweb="radio"]) {{
    color: {t.text_secondary} !important;
    font-weight: 500;
}}

/* Sidebar theme */
[data-testid="stSidebar"] {{
    background-color: #0b0f19 !important;
    color: #f1f5f9 !important;
    border-right: 1px solid {t.border_color} !important;
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {{
    color: #f1f5f9 !important;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    color: #94a3b8 !important;
    font-size: 0.88rem !important;
    line-height: 1.35 !important;
}}

[data-testid="stSidebar"] [data-baseweb="select"] {{
    color: #0f172a;
}}

[data-testid="stSidebar"] button p {{
    color: #0f172a !important;
}}

/* Form inputs & select boxes in main content */
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] > div,
[data-testid="stMain"] input,
[data-testid="stMain"] select,
[data-testid="stMain"] textarea {{
    background-color: {t.bg_input} !important;
    color: {t.text_primary} !important;
    border-color: {t.border_color} !important;
    border-radius: 6px !important;
}}

[data-testid="stMain"] [data-baseweb="select"] span,
[data-testid="stMain"] [data-baseweb="select"] div {{
    color: {t.text_primary} !important;
}}

/* Cards, Expander Panels & Metrics */
.gov-card {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}}

.gov-card h4 {{
    margin-top: 0 !important;
    color: {t.text_primary} !important;
    font-size: 1.05rem !important;
    font-weight: 650 !important;
}}

.gov-card p, .gov-card span {{
    color: {t.text_secondary} !important;
}}

.empty-state-box {{
    text-align: center !important;
    padding: 2rem 1.5rem !important;
    margin: 1.5rem 0 !important;
}}

.empty-title {{
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: {t.text_primary} !important;
}}

.empty-desc {{
    font-size: 0.9rem !important;
    color: {t.text_muted} !important;
    margin-top: 0.35rem !important;
    margin-bottom: 0 !important;
}}

[data-testid="stExpander"] {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 8px !important;
}}

[data-testid="stExpander"] summary {{
    color: {t.text_primary} !important;
}}

[data-testid="stMetricValue"] {{
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    color: {t.text_primary} !important;
}}

[data-testid="stMetricLabel"] {{
    font-size: 0.85rem !important;
    color: {t.text_muted} !important;
}}

/* Tables and DataFrames */
[data-testid="stDataFrame"], [data-testid="stTable"] {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.table_border} !important;
    border-radius: 8px !important;
    overflow: hidden;
}}

table {{
    color: {t.text_primary} !important;
    border-collapse: collapse !important;
    width: 100% !important;
}}

table th {{
    background-color: {t.table_header_bg} !important;
    color: {t.text_primary} !important;
    border-bottom: 1px solid {t.table_border} !important;
    font-weight: 650 !important;
    padding: 8px 12px !important;
}}

table td {{
    color: {t.text_secondary} !important;
    border-bottom: 1px solid {t.table_border} !important;
    padding: 8px 12px !important;
}}

/* Status Badges */
.status {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    line-height: 1.4;
}}

.status.good {{
    color: {t.status_good_text} !important;
    background-color: {t.status_good_bg} !important;
    border: 1px solid {t.status_good_border} !important;
}}

.status.bad {{
    color: {t.status_bad_text} !important;
    background-color: {t.status_bad_bg} !important;
    border: 1px solid {t.status_bad_border} !important;
}}

.status.pending, .status.warn {{
    color: {t.status_warn_text} !important;
    background-color: {t.status_warn_bg} !important;
    border: 1px solid {t.status_warn_border} !important;
}}

.status.neutral {{
    color: {t.text_secondary} !important;
    background-color: {t.bg_surface} !important;
    border: 1px solid {t.border_subtle} !important;
}}

.status.info {{
    color: {t.status_info_text} !important;
    background-color: {t.status_info_bg} !important;
    border: 1px solid {t.status_info_border} !important;
}}

/* Multiselect Tags (Selected Field Badges) — Crisp White Text and Icons */
div[data-testid="stMultiSelect"] [data-baseweb="tag"],
[data-baseweb="tag"],
div[data-baseweb="tag"],
span[data-baseweb="tag"] {{
    background-color: {t.accent_primary} !important;
    color: #ffffff !important;
    border-radius: 5px !important;
    border: none !important;
}}

div[data-testid="stMultiSelect"] [data-baseweb="tag"] *,
[data-baseweb="tag"] *,
[data-baseweb="tag"] span,
[data-baseweb="tag"] p,
[data-baseweb="tag"] div {{
    color: #ffffff !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}

div[data-testid="stMultiSelect"] [data-baseweb="tag"] svg,
[data-baseweb="tag"] svg,
[data-baseweb="tag"] path {{
    fill: #ffffff !important;
    color: #ffffff !important;
}}

[data-baseweb="tag"]:hover {{
    background-color: {t.accent_hover} !important;
}}

/* Primary Buttons — Pure white text and polished hover states */
button[kind="primary"],
button[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"],
div.stButton > button[kind="primary"] {{
    background-color: {t.accent_primary} !important;
    border-color: {t.accent_primary} !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15) !important;
    transition: all 0.15s ease !important;
}}

button[kind="primary"] p,
button[kind="primary"] span,
button[kind="primary"] div,
button[data-testid="baseButton-primary"] p,
button[data-testid="baseButton-primary"] span,
button[data-testid="baseButton-primary"] div,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span,
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span {{
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover,
div.stButton > button[kind="primary"]:hover {{
    background-color: {t.accent_hover} !important;
    border-color: {t.accent_hover} !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25) !important;
}}

button[kind="primary"]:hover p,
button[kind="primary"]:hover span,
button[data-testid="baseButton-primary"]:hover p,
button[data-testid="baseButton-primary"]:hover span {{
    color: #ffffff !important;
}}

/* Secondary Buttons */
button[kind="secondary"],
[data-testid="baseButton-secondary"],
[data-testid="stBaseButton-secondary"],
div.stButton > button[kind="secondary"] {{
    background-color: {t.bg_card} !important;
    border-color: {t.border_color} !important;
    color: {t.text_primary} !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
}}

button[kind="secondary"] p,
button[kind="secondary"] span,
[data-testid="baseButton-secondary"] p,
[data-testid="baseButton-secondary"] span {{
    color: {t.text_primary} !important;
}}

/* ------------------------------------------------------------- */
/* TOP NAVIGATION BAR — Modern Tab Pills (No Radio Buttons)      */
/* ------------------------------------------------------------- */
[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"]) {{
    position: sticky !important;
    top: 2.875rem !important;
    z-index: 95 !important;
    background-color: {t.bg_app} !important;
    padding-top: 0.25rem !important;
    padding-bottom: 0.6rem !important;
    margin-bottom: 1.25rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}}

div[data-testid="stRadio"] {{
    position: static !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}}

div[data-testid="stRadio"] > label {{
    display: none !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 0.35rem !important;
    background: {t.bg_nav} !important;
    padding: 0.35rem 0.45rem !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 44px !important;
    box-sizing: border-box !important;
}}

/* Hide native radio circles completely */
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label > span:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label input[type="radio"] {{
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    opacity: 0 !important;
    visibility: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}}

/* Individual navigation pill */
div[data-testid="stRadio"] div[role="radiogroup"] label {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0.45rem 0.95rem !important;
    border-radius: 7px !important;
    background: transparent !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
    border: 1px solid transparent !important;
    margin: 0 !important;
    user-select: none !important;
}}

/* Inactive nav pill typography */
div[data-testid="stRadio"] div[role="radiogroup"] label p,
div[data-testid="stRadio"] div[role="radiogroup"] label span,
div[data-testid="stRadio"] div[role="radiogroup"] label div {{
    color: {t.text_muted} !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    line-height: 1.25 !important;
    margin: 0 !important;
    padding: 0 !important;
    white-space: nowrap !important;
    letter-spacing: -0.01em !important;
}}

/* Nav pill hover state */
div[data-testid="stRadio"] div[role="radiogroup"] label:hover {{
    background: {t.bg_surface} !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label:hover p,
div[data-testid="stRadio"] div[role="radiogroup"] label:hover span {{
    color: {t.text_primary} !important;
}}

/* Active selected nav pill */
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background: {t.accent_primary} !important;
    border-color: {t.accent_primary} !important;
    box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3) !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) span,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) div {{
    color: #ffffff !important;
    font-weight: 600 !important;
}}

/* Fallback selectors for checked state */
div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"],
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] {{
    background: {t.accent_primary} !important;
    border-color: {t.accent_primary} !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] p,
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] p {{
    color: #ffffff !important;
    font-weight: 600 !important;
}}

/* Theme Toggle Button: Aligned, Compact 44x44px Square */
.theme-toggle-container {{
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 100% !important;
}}

.theme-toggle-container button,
div[data-testid="stColumn"] button[key="theme_toggle"],
button[data-testid="baseButton-secondary"]:has(p:only-child) {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: {t.bg_nav} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 10px !important;
    height: 44px !important;
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    padding: 0 !important;
    font-size: 1.25rem !important;
    cursor: pointer !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    transition: all 0.15s ease-in-out !important;
    box-sizing: border-box !important;
}}

.theme-toggle-container button p,
.theme-toggle-container button span,
div[data-testid="stColumn"] button[key="theme_toggle"] p,
div[data-testid="stColumn"] button[key="theme_toggle"] span {{
    font-size: 1.25rem !important;
    line-height: 1 !important;
    color: {t.text_primary} !important;
    margin: 0 !important;
    padding: 0 !important;
}}

.theme-toggle-container button:hover,
div[data-testid="stColumn"] button[key="theme_toggle"]:hover {{
    background: {t.bg_surface} !important;
    border-color: {t.accent_primary} !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
    transform: translateY(-1px) !important;
}}

.theme-toggle-container button:focus,
div[data-testid="stColumn"] button[key="theme_toggle"]:focus {{
    outline: 2px solid {t.accent_primary} !important;
    outline-offset: 2px !important;
}}

/* Horizontal Dividers */
hr {{
    border: none !important;
    border-top: 1px solid {t.border_color} !important;
    margin: 1.2rem 0 !important;
}}

/* Alert Boxes (Info, Warning, Error, Success) */
[data-testid="stAlert"] {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 8px !important;
    color: {t.text_primary} !important;
}}

[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {{
    color: {t.text_primary} !important;
}}

/* Checkboxes */
div[data-testid="stCheckbox"] label span {{
    color: {t.text_primary} !important;
}}

/* Code blocks and architecture diagrams */
[data-testid="stCode"], code, pre {{
    background-color: {t.bg_surface} !important;
    color: {t.text_primary} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 6px !important;
}}

/* BaseWeb Dropdown Menus and Popovers */
div[data-baseweb="popover"],
div[data-baseweb="menu"],
ul[data-baseweb="menu"] {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.border_color} !important;
}}

li[data-baseweb="menu-item"] {{
    background-color: {t.bg_card} !important;
    color: {t.text_primary} !important;
}}

li[data-baseweb="menu-item"]:hover {{
    background-color: {t.border_color} !important;
}}

/* JSON Tree Inspector */
[data-testid="stJson"] {{
    background-color: {t.bg_card} !important;
    border: 1px solid {t.border_color} !important;
    border-radius: 6px !important;
}}
</style>
"""
