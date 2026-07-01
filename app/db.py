from datetime import datetime, date

import streamlit as st
import pandas as pd
import sqlalchemy

from app.google_drive import download_google_drive_image
from providers import image_storage_provider


@st.cache_resource
def init_connection():
    return sqlalchemy.create_engine(st.secrets["connections"]["postgres"]["url"])


engine = init_connection()


@st.cache_data(ttl=60)
def get_members():
    query = "SELECT id, name, date_of_birth, conversion_date, baptism_date, whatsapp, email, picture, last_updated_date FROM core_member"
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def parse_form_date(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    string_value = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(string_value, fmt).date()
        except ValueError:
            continue

    parsed = pd.to_datetime(string_value, dayfirst=True, errors="coerce")
    return parsed.date() if not pd.isna(parsed) else None


def save_picture_reference(picture_url):
    if not picture_url:
        return None

    image_bytes = download_google_drive_image(picture_url)
    if image_bytes:
        picture_ref = image_storage_provider.upload_image(image_bytes)

        if picture_ref:
            print(f"Upload successful to image storage provider: {picture_ref}")
            return picture_ref

    print("Process failed: Could not download or upload the image.")
    return picture_url


def get_member_id_by_name(name):
    if not name:
        return None

    lower_name = name.lower().strip()

    query = "SELECT id FROM core_member WHERE LOWER(name) = :name LIMIT 1"
    with engine.connect() as conn:
        result = (
            conn.execute(sqlalchemy.text(query), {"name": lower_name})
            .mappings()
            .first()
        )
        return result["id"] if result else None


def update_member_union(
    member_id,
    spouse_member_id=None,
    spouse_external_name=None,
    union_date=None,
    conn=None,
):
    parameters = {
        "member_id": member_id,
        "spouse_member_id": spouse_member_id,
        "spouse_external_name": spouse_external_name,
        "union_date": union_date,
    }

    should_close = conn is None
    if should_close:
        conn = engine.connect()

    try:
        if spouse_member_id:
            query_exact = """
                SELECT id FROM core_membersunion
                WHERE (person_one_id = :member_id AND person_two_id = :spouse_member_id)
                   OR (person_one_id = :spouse_member_id AND person_two_id = :member_id)
                LIMIT 1
            """
            exact_row = (
                conn.execute(sqlalchemy.text(query_exact), parameters)
                .mappings()
                .first()
            )

            if exact_row:
                query_upd = "UPDATE core_membersunion SET union_date = :union_date, union_type = 'casamento', last_updated_date = NOW() WHERE id = :id"
                conn.execute(
                    sqlalchemy.text(query_upd),
                    {"union_date": union_date, "id": exact_row["id"]},
                )

                print(f"Update successful for member ID {member_id}")

                return

        query_find = """
            SELECT id, person_one_id, person_two_id
            FROM core_membersunion
            WHERE person_one_id = :member_id OR person_two_id = :member_id
            LIMIT 1
        """
        row = (
            conn.execute(sqlalchemy.text(query_find), {"member_id": member_id})
            .mappings()
            .first()
        )

        if row:
            is_person_one = row["person_one_id"] == member_id

            update_fields = [
                "union_date = :union_date",
                "union_type = 'casamento'",
                "last_updated_date = NOW()",
            ]

            if spouse_member_id:
                conn.execute(
                    sqlalchemy.text(
                        "UPDATE core_membersunion SET person_two_id = NULL WHERE person_two_id = :spouse_member_id AND id != :id"
                    ),
                    {"spouse_member_id": spouse_member_id, "id": row["id"]},
                )

                print(f"Cleared existing union for spouse member ID {spouse_member_id}")

            if is_person_one:
                if spouse_member_id:
                    update_fields.extend(
                        [
                            "person_two_id = :spouse_member_id",
                            "person_two_external = NULL",
                        ]
                    )
                else:
                    update_fields.extend(
                        [
                            "person_two_id = NULL",
                            "person_two_external = :spouse_external_name",
                        ]
                    )
            else:
                if spouse_member_id:
                    update_fields.extend(
                        [
                            "person_one_id = :member_id",
                            "person_two_id = :spouse_member_id",
                            "person_two_external = NULL",
                        ]
                    )
                else:
                    update_fields.extend(
                        [
                            "person_one_id = :member_id",
                            "person_two_id = NULL",
                            "person_two_external = :spouse_external_name",
                        ]
                    )

            query_update = f"UPDATE core_membersunion SET {', '.join(update_fields)} WHERE id = :id"

            print(
                f"Updating union for member ID {member_id} with spouse member ID {spouse_member_id} and external name '{spouse_external_name}'"
            )

            exec_params = {
                "union_date": union_date,
                "spouse_member_id": spouse_member_id,
                "spouse_external_name": spouse_external_name,
                "member_id": member_id,
                "id": row["id"],
            }
            conn.execute(sqlalchemy.text(query_update), exec_params)

        else:
            if spouse_member_id:
                conn.execute(
                    sqlalchemy.text(
                        "UPDATE core_membersunion SET person_two_id = NULL WHERE person_two_id = :spouse_member_id"
                    ),
                    {"spouse_member_id": spouse_member_id},
                )

                print(f"Cleared existing union for spouse member ID {spouse_member_id}")

            query_insert = (
                "INSERT INTO core_membersunion (person_one_id, person_two_id, person_two_external, union_type, union_date, creation_date, last_updated_date) "
                "VALUES (:member_id, :spouse_member_id, :spouse_external_name, 'casamento', :union_date, NOW(), NOW())"
            )
            conn.execute(sqlalchemy.text(query_insert), parameters)

            print(
                f"Inserted new union for member ID {member_id} with spouse member ID {spouse_member_id} and external name '{spouse_external_name}'"
            )

    finally:
        if should_close:
            conn.close()


def update_member_from_form(member_id, form_data, spouse_data=None):
    if not member_id:
        return

    whatsapp = form_data.get("whatsapp")
    email = form_data.get("email")
    picture_url = form_data.get("picture_url")
    birth_date = parse_form_date(form_data.get("birth_date"))
    conversion_date = parse_form_date(form_data.get("conversion_date"))
    baptism_date = parse_form_date(form_data.get("baptism_date"))

    update_fields = {}
    if whatsapp:
        update_fields["whatsapp"] = str(whatsapp).strip()
    if email:
        update_fields["email"] = str(email).strip()
    if birth_date:
        update_fields["date_of_birth"] = birth_date
    if conversion_date:
        update_fields["conversion_date"] = conversion_date
    if baptism_date:
        update_fields["baptism_date"] = baptism_date
    if picture_url:
        picture_ref = save_picture_reference(picture_url)
        if picture_ref:
            update_fields["picture"] = picture_ref

    should_update_member = bool(update_fields)
    should_update_union = spouse_data and spouse_data.get("is_married")

    with engine.begin() as conn:
        if should_update_member:
            set_clauses = ", ".join(f"{col} = :{col}" for col in update_fields)
            query = f"UPDATE core_member SET {set_clauses}, last_updated_date = NOW() WHERE id = :member_id"
            params = {**update_fields, "member_id": member_id}
            conn.execute(sqlalchemy.text(query), params)

        if should_update_union:
            update_member_union(
                member_id=member_id,
                spouse_member_id=spouse_data.get("spouse_member_id"),
                spouse_external_name=spouse_data.get("spouse_external_name"),
                union_date=parse_form_date(spouse_data.get("union_date")),
                conn=conn,
            )


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
