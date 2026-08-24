"""
Thin psycopg2 data-access layer for the CRM prospects table.

Deliberately independent from pooly-core's `packages/core/database` module:
this service owns a single table (`crm_prospects`) in the same Postgres
instance, and keeps its own connection handling so its deploys never depend
on pooly-core's DB abstraction changing underneath it.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json

# Maps the JSON keys the frontend already speaks (short, camel-ish names
# carried over from the original prototype) to the readable snake_case
# columns in Postgres. Keeping this translation in one place means the
# large existing frontend file needs zero renaming.
FIELD_MAP = {
    "empresa": "empresa",
    "cat": "categoria",
    "ig": "ig",
    "ciudad": "ciudad",
    "pri": "prioridad",
    "status": "status",
    "contacto": "contacto",
    "canal": "canal",
    "ult": "ultimo_contacto",
    "email": "email",
    "wp": "whatsapp",
    "emailEmpresa": "email_empresa",
    "wpEmpresa": "whatsapp_empresa",
    "notas": "notas",
    "fechaPrimerContacto": "fecha_primer_contacto",
    "proximaAccion": "proxima_accion",
    "fechaProximaAccion": "fecha_proxima_accion",
    "historialEstados": "historial_estados",
    "plantillaEnviada": "plantilla_enviada",
    "plantillaOverride": "plantilla_override",
    "plantillaTexto": "plantilla_texto",
}
DB_TO_API = {db_col: api_key for api_key, db_col in FIELD_MAP.items()}
MUTABLE_COLUMNS = list(FIELD_MAP.values())  # everything except id/created_at/updated_at


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        # psycopg2 wants postgresql:// — Railway historically hands out postgres://
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def is_user_admin(username):
    """Read-only lookup against pooly-core's `users` table, which lives in
    this same Postgres instance. Deliberately just a raw SELECT — this repo
    still never imports pooly-core's Python code, only shares its database."""
    if not username:
        return False
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        return bool(row and row.get("is_admin"))


def _row_to_api(row):
    if row is None:
        return None
    out = {"id": row["id"]}
    for db_col, api_key in DB_TO_API.items():
        val = row.get(db_col)
        if db_col == "historial_estados":
            out[api_key] = val if val is not None else []
        elif db_col == "plantilla_enviada":
            out[api_key] = bool(val)
        else:
            out[api_key] = val if val is not None else ""
    return out


def _prep_value(db_col, val):
    if db_col == "historial_estados":
        return Json(val if val is not None else [])
    return val


def list_prospects():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM crm_prospects ORDER BY created_at DESC")
        return [_row_to_api(r) for r in cur.fetchall()]


def get_prospect(prospect_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM crm_prospects WHERE id = %s", (prospect_id,))
        return _row_to_api(cur.fetchone())


def create_prospect(prospect_id, data):
    cols = ["id"] + MUTABLE_COLUMNS
    values = [prospect_id] + [_prep_value(c, data.get(DB_TO_API[c])) for c in MUTABLE_COLUMNS]
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO crm_prospects ({col_list}) VALUES ({placeholders}) RETURNING *",
            values,
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_api(row)


def update_prospect(prospect_id, data):
    """Partial update — only touches columns present in `data`."""
    set_cols = [FIELD_MAP[k] for k in data.keys() if k in FIELD_MAP]
    if not set_cols:
        return get_prospect(prospect_id)
    set_clause = ", ".join([f"{c} = %s" for c in set_cols] + ["updated_at = now()"])
    values = [_prep_value(c, data[DB_TO_API[c]]) for c in set_cols]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"UPDATE crm_prospects SET {set_clause} WHERE id = %s RETURNING *",
            values + [prospect_id],
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_api(row)


def delete_prospect(prospect_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM crm_prospects WHERE id = %s", (prospect_id,))
        deleted = cur.rowcount
        conn.commit()
        return deleted > 0


def upsert_many(prospects):
    """Insert-or-update by id. Used both for the ongoing frontend sync
    (which pushes its full in-memory list on every change) and for the
    one-time migration of the original 296 seed rows."""
    if not prospects:
        return 0
    cols = ["id"] + MUTABLE_COLUMNS
    col_list = ", ".join(cols)
    update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in MUTABLE_COLUMNS] + ["updated_at = now()"])
    placeholders = ", ".join(["%s"] * len(cols))
    with get_conn() as conn, conn.cursor() as cur:
        for p in prospects:
            values = [p.get("id")] + [_prep_value(c, p.get(DB_TO_API[c])) for c in MUTABLE_COLUMNS]
            cur.execute(
                f"""INSERT INTO crm_prospects ({col_list}) VALUES ({placeholders})
                    ON CONFLICT (id) DO UPDATE SET {update_clause}""",
                values,
            )
        conn.commit()
        return len(prospects)
