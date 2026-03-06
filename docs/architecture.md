# Architettura MASONRY.AI: Zero Trust Data Flow

MASONRY.AI implementa un paradigma di **Privacy by Design** attraverso un'architettura a 3 livelli. Invece di affidarsi a policy reattive, il framework impone vincoli fisici al flusso dei dati.

---

## I 3 Livelli di Difesa

L'architettura è progettata per rendere strutturalmente impossibile la violazione delle normative (GDPR, AI Act) impedendo ai dati non conformi di entrare nel sistema di elaborazione.

### 1. Ingress Layer (Privacy by Mason)
Il primo livello è gestito dal **Gatekeeper**. Ogni dato in ingresso deve superare una validazione rigorosa basata su **Data Contracts** (Contratti di Dati).
- **Fail-Fast**: Se i dati non rispettano lo schema o i requisiti legali (es. età minima, consenso esplicito), vengono respinti immediatamente.
- **Predicati di Privacy**: Durante la validazione, i dati vengono trasformati (mascheramento email, pseudonimizzazione ID) prima di passare al livello successivo.
- **Validazione Strutturale**: La privacy è una proprietà del contenitore, non solo del dato.

### 2. Processing Layer (DCDA Light)
I dati validati entrano nell'**Engine**, che segue i principi della **Decision-Centric Data Architecture (DCDA)**.
- **Stateless Decision Nodes**: La logica di business è suddivisa in micro-funzioni isolate e senza stato.
- **Data Minimization**: Ogni nodo riceve solo il set minimo di dati necessario per la sua esecuzione.
- **Resilienza**: I fallimenti sono contenuti all'interno dei singoli nodi, evitando effetti a catena (cascading failures).

### 3. Output Layer (Differential Privacy)
Prima che i risultati dell'elaborazione lascino il sistema per essere consumati da API o Dashboard, passano attraverso un filtro finale.
- **OpenDP**: Utilizza la libreria OpenDP per aggiungere rumore statistico ai dati aggregati.
- **Anonimizzazione**: Garantisce che i dati in uscita non permettano di risalire ai singoli individui, proteggendo la privacy anche contro attacchi di inferenza.

---

## Flusso dei Dati (Diagramma)

```text
[ SORGENTE DATI / INPUT UTENTE ]
         |
         v
+----------------------------------------------------------+
| LIVELLO 1: INGRESS  (Privacy by Mason)                   |
| Gatekeeper — Validazione Schema + Predicati Privacy      |
| Fallimento immediato: i dati non conformi sono RESPINTI  |
+----------------------------------------------------------+
         | (Solo dati validati e "sicuri" passano)
         v
+----------------------------------------------------------+
| LIVELLO 2: ELABORAZIONE (DCDA Light)                     |
| Decision Nodes — Micro-funzioni isolate e stateless      |
| Isolamento dei guasti. Nessun fallimento a cascata.      |
+----------------------------------------------------------+
         | (Risultati analitici grezzi)
         v
+----------------------------------------------------------+
| LIVELLO 3: OUTPUT  (Differential Privacy / NIST)         |
| Filtro Privacy — Rumore OpenDP su output aggregati       |
| L'output finale non rivela nulla sui singoli individui.  |
+----------------------------------------------------------+
         |
         v
[ DASHBOARD / CONSUMATORE API ]
```

---

## Concetti Chiave

### Privacy by Mason
Metafora: i dati sono mattoni che entrano in un cantiere. Il "Muratore" (Mason - Livello 1) ispeziona ogni mattone. Se il materiale non è conforme, viene scartato subito.

### DCDA Light
Architettura centrata sulla decisione: il sistema non è un monolite che processa dati, ma una rete di nodi che prendono decisioni atomiche e sicure.

### Privacy Strutturale
La conformità non è un check manuale fatto dallo sviluppatore, ma una caratteristica intrinseca della pipeline. Se il codice gira, i dati sono conformi.
