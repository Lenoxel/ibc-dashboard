import pandas as pd


def is_register_updated(db_data, form_data) -> str:
    if pd.to_datetime(
        db_data["birth_date"], format="%d/%m/%Y", errors="coerce"
    ) != pd.to_datetime(form_data["birth_date"], format="%d/%m/%Y", errors="coerce"):
        return "Não"

    db_conversion_date = (
        pd.to_datetime(
            db_data.get("conversion_date"), format="%d/%m/%Y", errors="coerce"
        )
        if db_data.get("conversion_date")
        else ""
    )
    form_conversion_date = (
        pd.to_datetime(
            form_data.get("conversion_date"), format="%d/%m/%Y", errors="coerce"
        )
        if form_data.get("conversion_date")
        else ""
    )

    if form_conversion_date and db_conversion_date != form_conversion_date:
        return "Não"

    db_baptism_date = (
        pd.to_datetime(db_data.get("baptism_date"), format="%d/%m/%Y", errors="coerce")
        if db_data.get("baptism_date")
        else ""
    )
    form_baptism_date = (
        pd.to_datetime(
            form_data.get("baptism_date"), format="%d/%m/%Y", errors="coerce"
        )
        if form_data.get("baptism_date")
        else ""
    )

    if form_baptism_date and db_baptism_date != form_baptism_date:
        return "Não"

    return (
        "Sim"
        if db_data["last_update_date"] is not None
        and db_data["last_update_date"]
        > pd.to_datetime(form_data["register_date"], format="%d/%m/%Y %H:%M:%S")
        else "Não"
    )
