"""Identidad visual institucional de la aplicación."""

import streamlit as st


def aplicar_estilos():
    """Aplica únicamente la identidad visual institucional de la interfaz."""
    st.markdown(
        """
        <style>
        :root {
            --udla-blue: #003A70;
            --udla-blue-secondary: #005EB8;
            --udla-orange: #F58220;
            --udla-bg: #F5F7FA;
            --udla-white: #FFFFFF;
            --udla-text: #1F2933;
            --udla-border: #D9DEE7;
        }

        .stApp {
            background: var(--udla-bg);
            color: var(--udla-text);
        }

        [data-testid="stHeader"] {
            background: rgba(245, 247, 250, 0.94);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--udla-blue) 0%, #002B54 100%);
            border-right: 4px solid var(--udla-orange);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--udla-white);
        }

        [data-testid="stSidebar"] [data-testid="stImage"] {
            background: var(--udla-white);
            border-radius: 10px;
            padding: 0.65rem;
            border-bottom: 4px solid var(--udla-orange);
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.28);
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] * {
            color: var(--udla-text) !important;
        }

        .udla-hero {
            min-height: 168px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: linear-gradient(135deg, var(--udla-blue) 0%, var(--udla-blue-secondary) 100%);
            border-left: 7px solid var(--udla-orange);
            border-radius: 14px;
            padding: 1.6rem 2rem;
            box-shadow: 0 10px 24px rgba(0, 58, 112, 0.14);
        }

        .udla-hero__eyebrow {
            color: #DCEBFA;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }

        .udla-hero h1 {
            color: var(--udla-white);
            font-size: clamp(1.75rem, 3vw, 2.65rem);
            line-height: 1.12;
            margin: 0;
        }

        .udla-hero p {
            color: #EAF3FB;
            font-size: 1rem;
            line-height: 1.55;
            margin: 0.75rem 0 0;
            max-width: 820px;
        }

        h2, h3 {
            color: var(--udla-blue);
        }

        [data-testid="stMetric"] {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-top: 4px solid var(--udla-orange);
            border-radius: 10px;
            padding: 0.75rem;
            box-shadow: 0 4px 12px rgba(31, 41, 51, 0.06);
        }

        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"] {
            color: var(--udla-blue) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--udla-white);
            border-color: var(--udla-border) !important;
            border-radius: 12px;
            box-shadow: 0 5px 16px rgba(31, 41, 51, 0.05);
        }

        [data-testid="stButton"] button {
            border: 1px solid var(--udla-blue-secondary);
            border-radius: 8px;
            color: var(--udla-blue);
            font-weight: 650;
        }

        [data-testid="stButton"] button:hover {
            border-color: var(--udla-orange);
            color: var(--udla-blue);
        }

        [data-testid="stButton"] button[kind="primary"] {
            background: var(--udla-orange);
            border-color: var(--udla-orange);
            color: var(--udla-white);
            min-height: 3rem;
            font-size: 1rem;
        }

        [data-testid="stButton"] button[kind="primary"]:hover {
            background: #D96D12;
            border-color: #D96D12;
            color: var(--udla-white);
        }

        [data-testid="stTextArea"] textarea {
            background: var(--udla-white);
            border-color: var(--udla-border);
            border-radius: 10px;
        }

        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--udla-blue-secondary);
            box-shadow: 0 0 0 1px var(--udla-blue-secondary);
        }

        [data-testid="stDataFrame"],
        [data-testid="stExpander"] {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-radius: 10px;
        }

        .udla-response-label {
            color: var(--udla-blue);
            border-left: 5px solid var(--udla-orange);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin: 1.4rem 0 0.65rem;
            padding-left: 0.7rem;
            text-transform: uppercase;
        }

        .udla-apertura {
            color: var(--udla-text);
            font-size: 1.02rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }

        .udla-followup {
            margin-top: 1.1rem;
            padding: 0.7rem 1rem;
            background: #EAF3FB;
            border-left: 4px solid var(--udla-orange);
            border-radius: 8px;
            color: var(--udla-blue);
            font-weight: 600;
        }

        @media (max-width: 700px) {
            .udla-hero {
                min-height: auto;
                padding: 1.25rem;
            }
            .block-container {
                padding-top: 0.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


