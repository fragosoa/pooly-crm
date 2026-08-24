# CLAUDE.md — Pooly CRM

## Qué es esto

Herramienta interna de seguimiento de outreach/ventas ("Pooly CRM", instancia MEXAICAN). Antes vivía como una sola app React sin build persistida en `localStorage` del navegador (ver `index.html` en la raíz — prototipo original, ya no se toca). Ahora corre como dos servicios Flask propios sobre Postgres, deployados en el **mismo proyecto Railway que pooly-core**, para poder alimentar procesos automáticos de contacto en el futuro.

Repo: `fragosoa/pooly-crm` (fork de `marlongonzalezmartinez-snai/mexaican`, renombrado). **Todo el trabajo del CRM vive bajo `services/`** — el resto de archivos en la raíz (`index.html`, `plataformas.html`, `recursos.html`, `mexaicancom.html`, `_redirects`) son herramientas/sitio previos del repo original, no relacionados, y no se tocan desde aquí.

## Estructura

```
services/
├── api/            ← Flask + psycopg2, CRUD de prospectos, JWT compartido con pooly-core
│   ├── app.py
│   ├── db.py           (mapeo entre JSON del frontend y columnas de crm_prospects)
│   ├── routes/prospects.py
│   └── migrations/     (Alembic propio — tabla de versiones separada: crm_alembic_version)
└── web/            ← Frontend estático (mismo index.html del prototipo, sin build)
    ├── index.html      (portado: localStorage → fetch a services/api)
    └── server.py        (sirve el HTML, inyecta CRM_API_URL/POOLY_CORE_URL desde env vars)

scripts/
└── migrate_seed_data.py   (uso único: extrae los 296 prospectos hardcodeados
                             del index.html original y los sube a Postgres)
```

## Invariantes con pooly-core

- **Misma Postgres, tabla nueva.** `crm_prospects` vive en la misma instancia de Railway que las tablas de pooly-core, pero este repo nunca importa `packages/core/database` de pooly-core — tiene su propio `db.py` autocontenido.
- **Mismo JWT.** `JWT_SECRET_KEY` debe ser idéntico al de pooly-core. Un token emitido por `POST /login` en pooly-core es válido aquí — este servicio no tiene tabla de usuarios ni login propio.
- **Solo admins.** Todas las rutas `/prospects*` exigen `is_admin=true` en la tabla `users` de pooly-core (ver `services/api/auth.py` — `admin_required`, y `db.is_user_admin()`, un SELECT de solo lectura contra esa tabla compartida). `GET /me` es la excepción: solo exige JWT válido, sin exigir admin, para que el frontend pueda distinguir "credenciales inválidas" de "login correcto pero sin permisos" y mostrar el mensaje adecuado antes de renderizar la app.
- **Alembic separado.** `services/api/migrations` usa `version_table = crm_alembic_version` (ver `migrations/env.py`) para no chocar con la tabla `alembic_version` que ya usa pooly-core en la misma DB. `alembic upgrade head` corre automáticamente al arrancar la API (mismo patrón que `PostgresBackend._run_migrations()` en pooly-core).
- **id lo genera el cliente.** El frontend ya generaba ids con `uid()` (string corto aleatorio) antes de que existiera backend — se mantiene como PK en Postgres (`TEXT PRIMARY KEY`) para no tener que reconciliar ids entre el estado local y la DB.

## Contrato del frontend con la API

El frontend sigue hablando en los nombres de campo cortos del prototipo original (`cat`, `ig`, `pri`, `ult`, `wp`, etc.) — la traducción a columnas legibles (`categoria`, `prioridad`, `ultimo_contacto`, `whatsapp`...) pasa una sola vez, en `services/api/db.py` (`FIELD_MAP`). No renombrar campos en el frontend sin actualizar ese mapa.

El frontend sincroniza con un patrón simple, no CRUD granular por campo:
- Al montar: `GET /prospects` hidrata el estado.
- En cualquier cambio del arreglo `prospects` (crear, editar, cambiar status): `POST /prospects/bulk` (upsert por id) empuja el arreglo completo. Barato de mantener, aceptable al volumen actual (~300 filas).
- `deleteProspect` además llama `DELETE /prospects/:id` explícito (el bulk upsert no puede borrar).

## Cómo correr localmente

```bash
cd pooly-crm   # este repo (fork bajo fragosoa/pooly-crm)
python3 -m venv .venv && source .venv/bin/activate
pip install -r services/api/requirements.txt -r services/web/requirements.txt

# Terminal 1 — API (requiere Postgres; docker compose de pooly-core sirve igual)
cd services/api
cp .env.example .env   # completar DATABASE_URL y JWT_SECRET_KEY (igual al de pooly-core)
python app.py           # → http://localhost:8081

# Terminal 2 — Web
cd services/web
cp .env.example .env
python server.py        # → http://localhost:8082
```

Login: usa las mismas credenciales de un usuario de pooly-core (`POOLY_CORE_URL` debe apuntar al API de pooly-core corriendo, local o Railway).

## Deploy (pendiente de crear en Railway)

Dos servicios nuevos en el proyecto Railway existente de Pooly, ambos con Root Directory propio y branch `develop`:

| Servicio | Root Directory | Start command (ya en su `railway.toml`) |
|---|---|---|
| `pooly-crm-api` | `services/api` | `gunicorn -w 2 -b 0.0.0.0:$PORT app:app` |
| `pooly-crm-web` | `services/web` | `gunicorn -w 2 -b 0.0.0.0:$PORT server:app` |

Variables de entorno a configurar en cada uno (ver `.env.example` de cada servicio): `DATABASE_URL` (referenciar el plugin Postgres del proyecto), `JWT_SECRET_KEY` (igual al de pooly-core), y en `web`: `CRM_API_URL`, `POOLY_CORE_URL`.
