# MASONRY Engine: DCDA Processing

L'**Engine** è il cuore decisionale di MASONRY.AI (Layer 2). Implementa la **Decision-Centric Data Architecture (DCDA)** per elaborare dati in modo isolato e sicuro.

---

## Architettura DCDA

In un sistema tradizionale, i dati fluiscono attraverso pipeline complesse. In MASONRY, ogni elaborazione è decomposta in **Decision Nodes** (Nodi Decisionali).

### Caratteristiche dei Nodi

- **Stateless**: Ogni nodo non mantiene stato tra le esecuzioni, facilitando la scalabilità e l'isolamento.
- **Pure Transformations**: I nodi eseguono trasformazioni deterministiche sul payload ricevuto.
- **Isolamento**: Un errore in un nodo non compromette l'intera pipeline.

---

## Esempio: ScoreBandNode

Lo `ScoreBandNode` è un esempio di come l'Engine riduca ulteriormente il rischio di identificazione trasformando dati numerici precisi in fasce (bands).

```python
# Un punteggio preciso (es: 650) viene trasformato in una fascia
payload = {"score": 650}
node = ScoreBandNode(node_id="credit_scoring")
result = node.execute(payload)
# result == {"score": 650, "score_band": "medium"}
```

---

## Grafi Decisionali (Solo Sovereign)

Nelle versioni Enterprise, l'Engine supporta grafi complessi di nodi (Decision Graphs) che permettono di:
- Eseguire nodi in parallelo.
- Definire logiche condizionali basate sui risultati dei nodi precedenti.
- Monitorare il **Turbulence Score** per identificare instabilità nei processi decisionali.

---

## Sicurezza e Minimizzazione

L'Engine riceve solo i dati che sono già stati validati e sanitizzati dal Gatekeeper. Ogni nodo riceve solo il sottoinsieme di dati necessario alla sua specifica decisione (Principio di Minimizzazione dei Dati).
