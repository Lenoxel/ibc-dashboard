import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.resolve()))

import streamlit as st
import pandas as pd
from app.db import get_members, get_members_classes
from app.forms import get_google_form
from app.matching_names import match_names

st.title("🔎 Matching de Nomes - Form x Banco")

df_members = get_members()
df_forms = get_google_form()

results = []
found_members = []

for g_name in df_forms["Nome"]:
    matched_name, score = match_names(g_name, df_members["name"].tolist())
    results.append(
        {
            "Nome Google Form": g_name,
            "Nome no Banco": matched_name if matched_name else "Não encontrado",
            "Score Similaridade": score,
        }
    )

    if matched_name:
        member_id = df_members.loc[df_members["name"] == matched_name, "id"].values[0]
        found_members.append({"member_id": member_id, "member_name": matched_name})

df_results = pd.DataFrame(results)

st.subheader("Resultados do Matching")
score_threshold = st.slider("Similaridade mínima", 0, 100, 85)
st.dataframe(df_results[df_results["Score Similaridade"] >= score_threshold])

st.write(
    "📊 Quantos matches encontrados:",
    df_results["Nome no Banco"].ne("Não encontrado").sum(),
)

df_members_classes = get_members_classes(
    [member["member_id"] for member in found_members]
)

st.subheader("Membros e suas Turmas")

st.dataframe(
    df_members_classes[["member_id", "member_name", "class_name"]].rename(
        columns={
            "member_id": "ID do Membro",
            "member_name": "Nome do Membro",
            "class_name": "Nome da Classe",
        }
    )
)

st.write("📊 Total de membros com classes:", df_members_classes["member_id"].nunique())

df_aggregated_by_class = (
    df_members_classes.groupby("class_name")
    .agg(total_members=pd.NamedAgg(column="member_id", aggfunc="nunique"))
    .reset_index()
    .sort_values(by="total_members", ascending=False)
)

st.subheader("Resumo por Classe")
st.dataframe(
    df_aggregated_by_class.rename(
        columns={"class_name": "Nome da Classe", "total_members": "Total de Membros"}
    )
)
