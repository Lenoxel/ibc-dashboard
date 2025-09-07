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
    query = "SELECT ebd_ebdclass.id AS class_id, ebd_ebdclass.name AS class_name, core_member.id AS member_id, core_member.name AS member_name FROM core_member JOIN ebd_ebdclass_students ON core_member.id = ebd_ebdclass_students.member_id JOIN ebd_ebdclass ON ebd_ebdclass.id = ebd_ebdclass_students.ebdclass_id"

    if member_ids:
        query += f" WHERE core_member.id IN ({','.join(map(str, member_ids))})"

    with engine.connect() as conn:
        return pd.read_sql(query, conn)
