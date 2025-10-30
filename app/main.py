import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.resolve()))

import streamlit as st
import pandas as pd
import plotly.express as px
from app.db import get_members, get_members_classes
from app.forms import get_google_form
from app.matching_names import match_names

st.set_page_config(
    page_title="Dashboard IBC", layout="wide", initial_sidebar_state="expanded"
)

# ...existing code...
st.markdown(
    """
    <style>
    html, body, [class^="css"] {
        font-size: 1.25rem !important;
    }

    [data-testid="stAppViewContainer"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    .main .block-container {
        padding-top: rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# ...existing code...

tabs = ["Home", "Quantidade de Membros por Classe", "Percentual de Membros por Classe"]

tab1, tab2, tab3 = st.tabs(tabs)

with tab1:
    st.title("🔎 Matching de Nomes - Form x Banco")

    df_members = get_members()
    df_forms = get_google_form()

    match_names_threshold = 50

    results = []
    found_members = []

    for _, form_row in df_forms.iterrows():
        form_row_person_name = form_row["Nome"].strip()

        form_row_register_date = form_row["Carimbo de data/hora"]

        matched_name, score = match_names(
            form_row_person_name, df_members["name"].tolist(), match_names_threshold
        )

        results.append(
            {
                "Data de Registro Google Form": form_row_register_date,
                "Nome Google Form": form_row_person_name,
                "Nome no Banco": matched_name if matched_name else "Não encontrado",
                "Score Similaridade": score,
            }
        )

        if matched_name:
            member_id = df_members.loc[df_members["name"] == matched_name, "id"].values[
                0
            ]
            found_members.append(
                {
                    "member_id": member_id,
                    "member_name": matched_name,
                    "form_register_date": form_row_register_date,
                }
            )

    df_results = pd.DataFrame(results)

    st.subheader("Resultados do Matching")
    score_threshold = st.slider("Similaridade mínima", 0, 100, match_names_threshold)

    st.dataframe(df_results[df_results["Score Similaridade"] >= score_threshold])

    st.write(
        "📊 Quantos matches encontrados:",
        df_results["Nome no Banco"].ne("Não encontrado").sum(),
    )

    df_members_classes = get_members_classes()

    for member in found_members:
        df_members_classes.loc[
            df_members_classes["member_id"] == member["member_id"], "form_register_date"
        ] = member["form_register_date"]

    df_members_classes["form_register_date"] = pd.to_datetime(
        df_members_classes["form_register_date"], format="%d/%m/%Y %H:%M:%S"
    )

    st.subheader("Membros e suas Turmas")

    df_member_classes_sorted = df_members_classes[
        ["member_name", "class_name", "role", "form_register_date"]
    ].rename(
        columns={
            "member_name": "Membro",
            "class_name": "Classe",
            "role": "Papel",
            "form_register_date": "Data de Registro",
        }
    )

    df_member_classes_sorted = df_member_classes_sorted.sort_values(
        by="Data de Registro", na_position="last", ascending=False
    )

    st.dataframe(df_member_classes_sorted)

    st.write(
        "📊 Total de membros com classes:",
        df_members_classes["form_register_date"].notna().sum(),
    )

    df_aggregated_by_class = (
        df_members_classes.groupby("class_name")
        .agg(
            total_members=pd.NamedAgg(column="member_id", aggfunc="nunique"),
            members_completed=pd.NamedAgg(column="form_register_date", aggfunc="count"),
        )
        .reset_index()
        .sort_values(by="total_members", ascending=False)
    )

    df_aggregated_by_class["percent_completed"] = (
        df_aggregated_by_class["members_completed"]
        / df_aggregated_by_class["total_members"]
        * 100
    )

    df_aggregated_by_class = df_aggregated_by_class.sort_values(
        by="percent_completed", ascending=False
    )

    st.subheader("Resumo por Classe")

    st.text(
        "Quantidade de membros de cada classe que fizeram a atualização de cadastro."
    )

    st.dataframe(
        df_aggregated_by_class.rename(
            columns={
                "class_name": "Nome da Classe",
                "total_members": "Membros na Classe",
                "members_completed": "Membros que Atualizaram",
                "percent_completed": "Percentual de Membros que Atualizaram",
            }
        )
    )

with tab2:
    st.title("📊 Quantidade de Membros por Classe")

    fig = px.bar(
        df_aggregated_by_class,
        x="members_completed",
        y="class_name",
        orientation="h",
        color="members_completed",
        color_continuous_scale="Greens",
        title="Quantidade de Membros por Classe",
        subtitle="Contagem de Membros que atualizaram o cadastro por classe",
        labels={"members_completed": "Membros na Classe", "class_name": "Classe"},
        text="members_completed",
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    fig.update_layout(
        title_font_size=32,
        xaxis=dict(title_font=dict(size=24), tickfont=dict(size=20)),
        yaxis=dict(title_font=dict(size=24), tickfont=dict(size=20)),
        coloraxis_colorbar=dict(
            title="Alunos", title_font=dict(size=22), tickfont=dict(size=18)
        ),
        bargap=0.4,
        height=800,
    )

    fig.update_traces(
        textposition="outside",
        textfont_size=22,
        textangle=0,
        marker_line_color="black",
        hovertemplate="<b>%{y}</b><br>Alunos na Classe: %{x}<extra></extra>",
        hoverlabel=dict(font_size=16),
        marker=dict(
            color=df_aggregated_by_class["members_completed"], colorscale="Greens"
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.title("📊 Percentual de Membros por Classe")

    fig2 = px.bar(
        df_aggregated_by_class,
        x="percent_completed",
        y="class_name",
        orientation="h",
        color="percent_completed",
        color_continuous_scale="Greens",
        title="Percentual de Membros por Classe",
        subtitle="Percentual de Membros que atualizaram o cadastro por classe",
        labels={"percent_completed": "Percentual (%)", "class_name": "Classe"},
        range_x=[0, 100],
        custom_data=["members_completed", "total_members"],
    )

    fig2.update_layout(yaxis={"categoryorder": "total ascending"})

    fig2.update_layout(
        title_font_size=32,
        xaxis=dict(title_font=dict(size=24), tickfont=dict(size=20)),
        yaxis=dict(title_font=dict(size=24), tickfont=dict(size=20)),
        coloraxis_colorbar=dict(
            title="Percentual", title_font=dict(size=22), tickfont=dict(size=18)
        ),
        bargap=0.4,
        height=800,
    )

    fig2.update_traces(
        texttemplate="%{x:.0f}% (%{customdata[0]} de %{customdata[1]} alunos)",
        textposition="auto",
        textfont_size=22,
        textangle=0,
        marker_line_color="black",
        hovertemplate="<b>%{y}</b><br>Percentual: %{x:.2f}%<extra></extra>",
        hoverlabel=dict(font_size=16),
        marker=dict(
            color=df_aggregated_by_class["percent_completed"], colorscale="Greens"
        ),
    )

    st.plotly_chart(fig2, use_container_width=True)
