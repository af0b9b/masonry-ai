# MASONRY Gatekeeper Service

Il **Gatekeeper** è il servizio di Ingress (Layer 1) di MASONRY.AI. È implementato con FastAPI ed è responsabile della validazione dei dati in ingresso e del loro inoltro sicuro all'Engine.

---

## Funzionalità principali

- **Validazione dei Contratti**: Applica i Data Contracts definiti nel Core.
- **Fail-Fast Ingestion**: Respinge immediatamente i dati non conformi con motivazioni dettagliate.
- **Sanitizzazione DP**: Applica filtri di Differential Privacy prima dell'inoltro.
- **Autenticazione**: Richiede una chiave API valida via header HTTP.
- **Rate Limiting**: Limita le richieste per prevenire abusi (default: 60 req/min).

---

## API Reference

### 1. Sanitizzazione e Ingestione

`POST /sanitise`

Valida un payload contro un contratto specifico e lo inoltra all'Engine se valido.

**Request Body:**
```json
{
  "contract_type": "gdpr",
  "payload": {
    "user_id": "mario123",
    "age": 30,
    "email": "mario@example.com",
    "consent_level": 3,
    "gdpr_accepted": true
  }
}
```

**Header richiesti:**
- `X-Masonry-Key`: La tua chiave API.

**Response (Dati validi):**
```json
{
  "status": "accepted",
  "batch_id": "uuid-v4-string",
  "sanitised": {
    "user_id": "a3f9bc12...",
    "email": "m***@example.com",
    "age": 30,
    ...
  }
}
```

**Response (Dati respinti):**
```json
{
  "status": "rejected",
  "rejection_reason": "MASON STOP: age 15 < 18..."
}
```

### 2. Elenco Contratti

`GET /contracts`

Restituisce l'elenco dei nomi dei contratti disponibili nel sistema.

### 3. Health Check

`GET /health`

Verifica lo stato del servizio.

---

## Configurazione (Variabili d'ambiente)

- `MASONRY_API_KEYS`: Lista separata da virgole di chiavi API valide (es: `key1,key2,key3`). Default: `dev-secret`.
- `ENGINE_URL`: URL del servizio Engine a cui inoltrare i dati. Default: `http://engine:8001`.

---

## Audit Logs

Il Gatekeeper emette log strutturati per ogni rifiuto (`MASON_REJECT`). Questi log includono il `request_id`, il tipo di contratto e la causa del rifiuto, ma **non contengono mai i dati PII originali** che hanno causato il fallimento, garantendo la conformità anche nei log di sistema.
