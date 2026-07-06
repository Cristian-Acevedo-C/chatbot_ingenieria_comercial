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

        .udla-resumen-titulo {
            color: var(--udla-blue);
            font-size: 0.95rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            margin: 1.1rem 0 0.6rem;
            text-transform: uppercase;
        }

        .udla-card {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-top: 4px solid var(--udla-blue-secondary);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(31, 41, 51, 0.06);
            height: 100%;
            padding: 0.85rem 0.95rem;
        }

        .udla-card__icon {
            font-size: 1.35rem;
            line-height: 1;
            margin-bottom: 0.35rem;
        }

        .udla-card__titulo {
            color: #5B6B7C;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .udla-card__valor {
            color: var(--udla-blue);
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.3;
            margin-top: 0.2rem;
        }

        .udla-card__extra {
            color: #5B6B7C;
            font-size: 0.78rem;
            margin-top: 0.3rem;
        }

        .udla-card--rojo { border-top-color: #C0392B; }
        .udla-card--amarillo { border-top-color: #D9A400; }
        .udla-card--verde { border-top-color: #1E8E3E; }

        .udla-semaforo {
            align-items: center;
            border-radius: 10px;
            display: flex;
            font-weight: 700;
            gap: 0.55rem;
            margin: 0.6rem 0 1rem;
            padding: 0.6rem 0.9rem;
        }

        .udla-semaforo__dot {
            border-radius: 50%;
            display: inline-block;
            height: 0.85rem;
            width: 0.85rem;
        }

        .udla-semaforo--verde {
            background: #E7F5EC;
            color: #1E8E3E;
        }
        .udla-semaforo--verde .udla-semaforo__dot { background: #1E8E3E; }

        .udla-semaforo--amarillo {
            background: #FDF3D9;
            color: #8A6900;
        }
        .udla-semaforo--amarillo .udla-semaforo__dot { background: #D9A400; }

        .udla-semaforo--rojo {
            background: #FBE7E4;
            color: #C0392B;
        }
        .udla-semaforo--rojo .udla-semaforo__dot { background: #C0392B; }

        .udla-semaforo__detalle {
            font-weight: 500;
            opacity: 0.85;
        }

        .udla-fuente-card {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-left: 4px solid var(--udla-orange);
            border-radius: 8px;
            margin-bottom: 0.55rem;
            padding: 0.55rem 0.85rem;
        }

        .udla-fuente-card__nombre {
            color: var(--udla-blue);
            font-weight: 700;
        }

        .udla-fuente-card__meta {
            color: #5B6B7C;
            font-size: 0.8rem;
        }

        .udla-evidencia-card {
            background: #FAFBFD;
            border: 1px solid var(--udla-border);
            border-radius: 10px;
            margin-bottom: 0.7rem;
            padding: 0.7rem 0.9rem;
        }

        .udla-evidencia-card__encabezado {
            align-items: center;
            display: flex;
            gap: 0.5rem;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }

        .udla-evidencia-card__titulo {
            color: var(--udla-blue);
            font-weight: 700;
        }

        .udla-badge {
            background: var(--udla-blue-secondary);
            border-radius: 999px;
            color: var(--udla-white);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.12rem 0.55rem;
            white-space: nowrap;
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


