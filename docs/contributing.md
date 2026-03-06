# Guida per i Contributori

Grazie per l'interesse nel contribuire a MASONRY.AI! Il progetto è composto da parti open-source e parti proprietarie.

---

## Struttura del Repository

- `packages/core`: Open-source (AGPL-3.0). Core logic, contratti e predicati.
- `packages/gatekeeper`: Open-source (AGPL-3.0). Servizio di Ingress.
- `packages/engine`: Proprietario. Logica di elaborazione avanzata.
- `packages/api`: Proprietario. API di gestione.
- `packages/dashboard`: Proprietario. Interfaccia utente.

---

## Sviluppo Locale

### Prerequisiti

- Python 3.11+
- Node.js (per la dashboard)
- Docker (opzionale, per i servizi completi)

### Setup Ambiente

Clona il repository e installa i pacchetti in modalità editabile:

```bash
git clone https://github.com/af0b9b/masonry-ai
cd masonry-ai
pip install -e packages/core
pip install -e packages/gatekeeper
```

### Esecuzione Test

Utilizziamo `pytest` per tutti i test dei pacchetti Python:

```bash
python -m pytest packages/core/tests/
```

---

## Linee Guida per i Contributi

1. **Focus sulla Privacy**: Ogni nuova funzionalità deve rispettare i principi di Privacy by Design.
2. **Data Contracts**: Se aggiungi un nuovo servizio che riceve dati PII, devi definire un Data Contract nel pacchetto `core`.
3. **Stateless Logic**: Mantieni i Decision Nodes nell'Engine il più possibile stateless e puri.
4. **Test Obbligatori**: Ogni modifica o aggiunta deve essere accompagnata da test unitari.

---

## Processo di Pull Request

1. Apri una Issue per discutere la modifica proposta.
2. Crea un branch per la tua feature.
3. Invia la PR verso il branch `main`.
4. Assicurati che tutti i test passino nel CI.

---

## Licenza

I pacchetti `core` e `gatekeeper` sono rilasciati sotto licenza [GNU AGPL v3.0](../LICENSE).
I pacchetti `engine`, `api` e `dashboard` sono proprietari.
