import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.resolve()))

import streamlit as st
import pandas as pd
import plotly.express as px
from app.db import (
    get_members,
    get_members_classes,
    get_member_id_by_name,
    update_member_from_form,
)
from app.forms import get_google_form
from app.matching_names import match_names
from app.utils import is_register_updated

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
    st.title("🔎 Atualização de cadastro")

    df_members = get_members()
    df_member_names = df_members["name"].tolist()

    df_forms = get_google_form()

    match_names_threshold = 30

    score_threshold = st.slider(
        "Similaridade mínima", 0, 100, match_names_threshold, key="score_threshold"
    )

    results = []
    found_members = []

    members_updated_in_db = 0

    for _, form_row in df_forms.iterrows():
        form_row_person_name = form_row["Nome"].strip()

        form_row_register_date = form_row["Carimbo de data/hora"]
        form_row_phone_number = form_row["Número de telefone (WhatsApp)"]
        form_row_birth_date = form_row["Data de nascimento"]
        form_row_conversion_date = form_row["Data de conversão"]
        form_row_baptism_date = form_row["Data de batismo"]
        form_row_email = form_row["E-mail"]
        form_row_picture_url = form_row["Foto"]
        form_row_is_married = form_row["É casado?"]
        form_row_marriage_date = form_row["Data de casamento"]

        raw_partner_name = form_row["Nome do cônjuge"]
        form_row_partner_name = (
            " ".join(str(raw_partner_name).split())
            if pd.notna(raw_partner_name) and str(raw_partner_name).strip()
            else None
        )

        form_row_partner_is_member = form_row["Cônjuge é membro ou congregado da IBC?"]

        matched_name, score = match_names(
            form_row_person_name, df_member_names, match_names_threshold
        )

        member_on_db = df_members.loc[df_members["name"] == matched_name]

        member_on_db_last_update_date = None

        if not member_on_db.empty:
            raw_val = member_on_db["last_updated_date"].values[0]
            try:
                member_on_db_last_update_date = pd.to_datetime(raw_val)
            except Exception:
                member_on_db_last_update_date = raw_val

            is_updated = is_register_updated(
                {
                    "last_update_date": member_on_db_last_update_date,
                    "birth_date": member_on_db["date_of_birth"].values[0],
                    "conversion_date": member_on_db["conversion_date"].values[0],
                    "baptism_date": member_on_db["baptism_date"].values[0],
                },
                {
                    "register_date": form_row_register_date,
                    "birth_date": form_row_birth_date,
                    "conversion_date": form_row_conversion_date,
                    "baptism_date": form_row_baptism_date,
                },
            )

        results.append(
            {
                "Atualizado": is_updated,
                "Score Similaridade": score,
                "Nome no Google Form": form_row_person_name,
                "Nome no Banco de dados": (
                    matched_name if matched_name else "Não encontrado"
                ),
                "Data de Registro Google Form": form_row_register_date,
                "Última Atualização no Banco de dados": member_on_db_last_update_date.strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
                "Número de telefone (WhatsApp)": (
                    str(form_row_phone_number)
                    if pd.notna(form_row_phone_number) and form_row_phone_number
                    else ""
                ),
                "Data de nascimento": form_row_birth_date,
                "Data de conversão": form_row_conversion_date,
                "Data de batismo": form_row_baptism_date,
                "E-mail": form_row_email,
                "Foto": form_row_picture_url,
                "É casado?": form_row_is_married,
                "Data de casamento": form_row_marriage_date,
                "Nome do cônjuge": form_row_partner_name,
                "Cônjuge é membro ou congregado da IBC?": form_row_partner_is_member,
            }
        )

        if matched_name:
            member_id = int(
                df_members.loc[df_members["name"] == matched_name, "id"].values[0]
            )

            found_members.append(
                {
                    "member_id": member_id,
                    "member_name": matched_name,
                    "form_register_date": form_row_register_date,
                }
            )

            if score >= 90 and is_updated == "Não" and members_updated_in_db < 0:
                print(f"updating data in DB for member: {matched_name}")

                spouse_is_member = (
                    str(form_row_partner_is_member).strip().lower() == "sim"
                )
                spouse_data = {
                    "is_married": str(form_row_is_married).strip().lower() == "sim",
                    "union_date": form_row_marriage_date,
                }

                if spouse_data["is_married"]:
                    if spouse_is_member:
                        spouse_data["spouse_member_id"] = get_member_id_by_name(
                            form_row_partner_name
                        )
                        spouse_data["spouse_external_name"] = None
                    else:
                        spouse_data["spouse_member_id"] = None
                        spouse_data["spouse_external_name"] = (
                            form_row_partner_name if form_row_partner_name else None
                        )
                    print(f"spouse_data: {spouse_data}")

                update_member_from_form(
                    member_id,
                    {
                        "whatsapp": form_row_phone_number,
                        "email": form_row_email,
                        "picture_url": form_row_picture_url,
                        "birth_date": form_row_birth_date,
                        "conversion_date": form_row_conversion_date,
                        "baptism_date": form_row_baptism_date,
                    },
                    spouse_data=spouse_data,
                )

                print(f"Data updated in DB for member: {matched_name}")

                members_updated_in_db += 1

    df_results = pd.DataFrame(results)

    st.subheader("Resultados da Correspondência de Nomes")

    def highlight_updated(row):
        color = "#d4f8e8" if row.get("Atualizado") == "Sim" else "#f8d4d4"
        return [f"background-color: {color}" for _ in row.index]

    styled = df_results.style.apply(highlight_updated, axis=1)

    st.dataframe(styled, hide_index=True)

    st.write(
        "📊 Correspondências de nomes encontrados por similaridade:",
        df_results["Nome no Banco de dados"].ne("Não encontrado").sum(),
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

    st.dataframe(df_member_classes_sorted, hide_index=True)

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
        ),
        hide_index=True,
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

    st.plotly_chart(fig, width="stretch")

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

    st.plotly_chart(fig2, width="stretch")
