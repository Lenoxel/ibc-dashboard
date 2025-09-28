import streamlit as st
import pandas as pd
import sqlalchemy


@st.cache_resource
def init_connection():
    return sqlalchemy.create_engine(st.secrets["connections"]["postgres"]["url"])


engine = init_connection()


@st.cache_data(ttl=60)
def get_members():
    query = "SELECT id, name FROM core_member"
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=300)
def get_members_classes(member_ids=None):
    filter_by_active_classes = "WHERE ebd_ebdclass.is_active = TRUE"

    query_get_students = f"SELECT ebd_ebdclass.id AS class_id, ebd_ebdclass.name AS class_name, core_member.id AS member_id, core_member.name AS member_name, 'Aluno' AS role FROM core_member JOIN ebd_ebdclass_students ON core_member.id = ebd_ebdclass_students.member_id JOIN ebd_ebdclass ON ebd_ebdclass.id = ebd_ebdclass_students.ebdclass_id {filter_by_active_classes}"

    query_get_secretaries = f"SELECT ebd_ebdclass.id AS class_id, ebd_ebdclass.name AS class_name, core_member.id AS member_id, core_member.name AS member_name, 'Secretário' AS role FROM core_member JOIN ebd_ebdclass_secretaries ON core_member.id = ebd_ebdclass_secretaries.member_id JOIN ebd_ebdclass ON ebd_ebdclass.id = ebd_ebdclass_secretaries.ebdclass_id {filter_by_active_classes}"

    query_get_teachers = f"SELECT ebd_ebdclass.id AS class_id, ebd_ebdclass.name AS class_name, core_member.id AS member_id, core_member.name AS member_name, 'Professor' AS role FROM core_member JOIN ebd_ebdclass_teachers ON core_member.id = ebd_ebdclass_teachers.member_id JOIN ebd_ebdclass ON ebd_ebdclass.id = ebd_ebdclass_teachers.ebdclass_id {filter_by_active_classes}"

    if member_ids:
        query_get_students += (
            f" WHERE core_member.id IN ({','.join(map(str, member_ids))})"
        )
        query_get_secretaries += (
            f" WHERE core_member.id IN ({','.join(map(str, member_ids))})"
        )
        query_get_teachers += (
            f" WHERE core_member.id IN ({','.join(map(str, member_ids))})"
        )

    query = f"({query_get_students}) UNION ({query_get_secretaries}) UNION ({query_get_teachers})"

    with engine.connect() as conn:
        return pd.read_sql(query, conn)
