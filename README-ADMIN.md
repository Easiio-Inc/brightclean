# BrightClean local admin

Run `./start-demo.sh`, then open **http://127.0.0.1:8200/**. Website: http://127.0.0.1:8188/. Public chatbot health: http://127.0.0.1:8199/health. Stop all three with `./stop-demo.sh`. Python 3.11+ and curl are sufficient; there are no pip or npm dependencies. Set `BRIGHTCLEAN_PYTHON` to choose a Python executable.

## Classroom credentials

**CLASSROOM DEFAULT: username `admin`, password `admin-change-me`.** This deliberately public default is for fictional classroom data on localhost only. The login shows a reminder after sign-in. All three servers bind to `127.0.0.1`; there is no remote-bind option. Do not forward ports, expose them through a proxy, or use the classroom default with private data.

## Set or change your password

Generate a salted PBKDF2-SHA256 hash using hidden, confirmed terminal input:

```bash
python3 admin_server.py --hash-password
```

Set these environment variables in the terminal that starts the demo:

```bash
export BRIGHTCLEAN_ADMIN_USERNAME='your-admin-name'
read -r -s -p 'Paste generated password hash: ' BRIGHTCLEAN_ADMIN_PASSWORD_HASH
printf '\n'
export BRIGHTCLEAN_ADMIN_PASSWORD_HASH
./start-demo.sh
```

The supported hash format is `pbkdf2_sha256$600000$<32 hex salt characters>$<64 hex digest characters>`. Each generation uses a new random salt. An invalid configured hash fails startup rather than falling back to the classroom password. The hash variable takes priority over the development password variable.

For temporary development, `BRIGHTCLEAN_ADMIN_DEV_PASSWORD` can hold a password instead. Enter it without shell history:

```bash
read -r -s -p 'Development password: ' BRIGHTCLEAN_ADMIN_DEV_PASSWORD
printf '\n'
export BRIGHTCLEAN_ADMIN_DEV_PASSWORD
unset BRIGHTCLEAN_ADMIN_PASSWORD_HASH
./start-demo.sh
```

Never commit passwords, hashes, `.env` files or shell exports. Only the explicitly labeled classroom default is in source. Passwords are hashed in memory with 600,000 PBKDF2 iterations and verified with constant-time comparison. To change credentials, generate a fresh hash, replace the environment value, and restart using `./start-demo.sh`. Restarting invalidates every existing session. Unset both password variables to return to the classroom default.

## Dashboard and data

The overview counts this site's contacts, deals, activities and knowledge articles. Each tab provides search, create, edit and confirmed deletion. Deal and activity forms can link only to records belonging to BrightClean. Input is validated in the browser and server. CRM deletes use the schema's `ON DELETE SET NULL` relationships; deleting a contact does not delete its deals or activities.

Knowledge reads and writes target only `sites.class3-brightclean-san-jose` in `data/rag-content.json`. Other tenants and document metadata are preserved. Writes use atomic file replacement. CRM uses `data/class3-demo-crm.db`, its real schema, parameterized values, explicit editable-field allowlists and SQLite foreign-key enforcement. CRM operations are scoped by the corresponding `websites.id`. Startup preserves edits; it does not reseed data. `./reset-demo.sh` intentionally resets classroom data, including knowledge.

Sessions contain random opaque IDs in an HttpOnly, SameSite=Strict cookie and live on the server for one hour. The cookie deliberately omits Secure because this loopback demo uses HTTP. Mutations, including logout, require a per-session CSRF token. Host and Origin checks protect the admin from cross-origin requests and DNS rebinding. Ten failed logins in a minute temporarily throttle further attempts. Sign out destroys the session; expired sessions require a new sign-in. Configured credentials, hashes and session IDs are never returned in dashboard records or logged.

`public_server.py` serves only the home page and public assets on 8188, preventing downloads of databases, knowledge files, source and Git metadata. On 8199 it loads the dependency-free chatbot and SoloCRM source included in `backend/`, then permits only health, public form configuration, chat session, message and lead intake. No external shared-tool installation is required. All public RAG/CRM administration routes are denied. The public chatbot still answers questions and captures visitor-submitted leads as intended; this is the intentional public intake path, not general CRM CRUD. Trusted page context and fixed site metadata prevent visitors from replacing the assistant's knowledge via conversation payloads. Runtime chatbot stores are redirected inside this repository.

Admin HTML/CSS/JS is a public login shell; data endpoints require authentication. The UI renders record values as text, and no credentials or hashes are embedded in assets. Do not run a separate unrestricted shared backend or `python -m http.server` over this repo. Startup stops only recorded demo processes and refuses occupied ports rather than silently reusing insecure services.

## Chatbot and OpenAI settings

The authenticated **Chatbot Settings** area controls Appearance, Behavior, Business profile, Lead capture, and AI Model for the fixed `class3-brightclean-san-jose` tenant. Safe widget values are atomically persisted in `data/site-settings.json`; AI provider/model/base URL metadata is in `data/llm-settings.json`. The public widget retrieves an explicit non-secret allowlist from `GET http://127.0.0.1:8199/widget-config` on page load. Its site ID, API base, and `ragAdmin=false` security boundary remain deployment-controlled and cannot be edited in the dashboard.

OpenAI is the fixed provider. Select a suggested model or enter a validated compatible model name; the base URL must be HTTPS. The API key is written separately to ignored `data/secrets/openai.env` with directory mode 0700 and file mode 0600. It is never returned to the browser or public config; the UI receives only configured/not-configured and at most the last four characters. A blank key preserves the existing key, while **Clear API key** explicitly removes it. **Test connection** performs a server-side `GET /models` with an eight-second timeout and returns a redacted error.

AI changes require a chatbot restart because the included backend reads environment configuration during import. Run `./stop-demo.sh && ./start-demo.sh` (or simply `./start-demo.sh`, which stops recorded demo processes first). `public_server.py` loads the protected key, model, and base URL into `EASIIO_CHATBOT_LLM_API_KEY`, `EASIIO_CHATBOT_LLM_MODEL`, and `EASIIO_CHATBOT_LLM_BASE_URL` before importing `backend/chatbot_app.py`. If no key is configured, no key is exported and the backend's existing no-key/fallback response behavior applies. Never put a real key in source, HTML, logs, or `data/llm-settings.json`.

## Verify

```bash
python3 -m unittest discover -s tests -v
node --check admin/app.js
./start-demo.sh
python3 scripts/smoke_demo.py
./stop-demo.sh
```

The HTTP integration tests use temporary copies of the real schema and RAG file. They cover login denial/success, logout, expiry, CSRF/origin/host protection, throttling, tenant-scoped RAG and CRM CRUD, settings validation and atomic persistence, secret lifecycle and permissions, mocked OpenAI connection checks, runtime environment loading, public-config allowlisting, password hashing, rejection of empty configured hashes, public-route/file allowlists, and redaction of internal chatbot automation results. Phase A tests were written and run before production changes; the RED run had four expected errors for missing settings, LLM, public-config, and runtime-loading behavior. The complete repository suite now includes admin, public-boundary, RAG, self-contained-backend, and WordPress-conversion coverage.

The smoke script checks the three live services, denied private data URLs, authenticated admin reads, public chatbot responses and logout. It uses current environment credentials, or the labeled classroom default, and creates a synthetic public chat session. No admin mutations are needed in live smoke testing. Browser visual QA requires a locally available browser; no browser packages are required by this project.

Logs and PID files are in `.run/` (ignored by Git). If a service fails to start, inspect `.run/admin.log`, `.run/backend.log` and `.run/site.log`. Chatbot and SoloCRM source are included under `backend/`; runtime databases remain local ignored files under `data/`. Public chat quality may depend on the configured model. This is a local teaching server, not an internet production deployment.

Current verification includes the complete automated suite plus desktop/mobile browser checks, failed/successful login, contact creation/edit/deletion, literal script-tag text rendering, knowledge creation/deletion, tab navigation, logout, and JavaScript syntax checks.

## Optional pgvector hybrid RAG and document uploads

JSON lexical retrieval remains the offline default and CRM remains SQLite. Setting server-only `EASIIO_RAG_DATABASE_URL` enables tenant-scoped PostgreSQL semantic, full-text, and parameterized exact-phrase retrieval merged by reciprocal-rank fusion. Operational failures are logged as sanitized warnings and remain observable through status fields while chat falls back to JSON. Every PostgreSQL query is tenant-filtered. At very large multi-tenant scale, filtering can reduce ANN recall; use tenant partitioning and/or pgvector iterative scans and tune index parameters.

Install `requirements-rag.txt`, set a local `RAG_POSTGRES_PASSWORD`, start `docker compose -f docker-compose.rag.yml up -d`, and apply `backend/sql/001_pgvector_rag.sql`. Configure `EASIIO_RAG_EMBEDDING_API_KEY` (fallback `OPENAI_API_KEY`), optional `EASIIO_RAG_EMBEDDING_BASE_URL`, model (default `text-embedding-3-small`), and dimension (default 1536). The SQL schema is 1536-dimensional; a different configured dimension requires a matching migration and mismatches are rejected. Preview the non-destructive, tenant-scoped import with `python3 scripts/import_rag_pgvector.py --site-id class3-brightclean-san-jose --dry-run`, then omit `--dry-run` to ingest idempotently.

Authenticated Knowledge uploads accept `.pdf`, `.docx`, `.pptx`, and UTF-8 TXT. The default limit is 10 MiB (`EASIIO_RAG_UPLOAD_MAX_BYTES`); extracted text defaults to 2 MiB and PDFs to 250 pages (`EASIIO_RAG_MAX_EXTRACTED_CHARS`, `EASIIO_RAG_MAX_PDF_PAGES`). Random server names, tenant manifests, per-member ZIP size/compression/expanded-size bounds, Office declarations, magic/container checks, CSRF, and authenticated downloads protect originals under ignored `data/knowledge-files/<site_id>/`; public_server never serves them. PyMuPDF is required for PDFs. Encrypted or scanned/no-text PDFs are rejected with an actionable message; OCR is not included. JSON, manifest, and original-file changes roll back together on local write failures; optional pgvector indexing is a separate operation, and upload/delete responses expose `indexed=false` with a safe warning if it fails. Deleting through the dedicated upload route removes its knowledge record, pgvector document/chunks when available, manifest row, and original.
