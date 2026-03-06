# MASONRY Core Library

La libreria `masonry-core` è il cuore del framework e contiene le definizioni dei **Data Contracts** e dei **Privacy Predicates**. È open-source e può essere utilizzata come libreria Python stand-alone.

---

## Installazione

```bash
pip install masonry-core
```

---

## Data Contracts

Un **Data Contract** è una classe Pydantic che definisce non solo la struttura dei dati, ma anche le regole di conformità legale e le trasformazioni di privacy necessarie.

### Esempio: GDPRUserContract

Il contratto `GDPRUserContract` impone diverse restrizioni:
- L'età deve essere superiore a 18 anni.
- L'ID utente viene pseudonimizzato automaticamente.
- L'email viene mascherata (es. `m***@example.com`).
- Il consenso (GDPR) deve essere esplicitamente accettato.

```python
from masonry_core.contracts import GDPRUserContract
from pydantic import ValidationError

try:
    user = GDPRUserContract(
        user_id="user_12345",
        age=25,
        email="mario.rossi@example.com",
        consent_level=3,
        gdpr_accepted=True
    )
    print(user.email)   # Output: m***@example.com
    print(user.user_id) # Output: [sha256 hash parziale]
except ValidationError as e:
    print(f"Dati respinti: {e}")
```

### Contratti Specializzati

Il Core fornisce contratti pre-configurati per settori specifici:
- **FinanceContract**: Richiede livelli di consenso più elevati e impone pattern rigorosi per reddito e punteggio di credito (non vengono mai memorizzati i valori esatti).
- **HealthContract**: Valida i codici ICD-10 e richiede il massimo livello di consenso (Livello 4) per il trattamento di dati sensibili (Art. 9 GDPR).

---

## Privacy Predicates

I predicati sono utility statiche utilizzate dai contratti per trasformare i dati sensibili.

- **`mask_email(value: str)`**: Mantiene il primo carattere della parte locale e il dominio.
- **`pseudonymize(value: str)`**: Genera un hash SHA-256 (primi 16 caratteri) del valore.
- **`mask_partial(value: str, keep: int = 2)`**: Maschera tutto il valore tranne i primi `keep` caratteri.

---

## Differential Privacy Filter

Il modulo `dp_filter.py` fornisce un wrapper attorno a OpenDP per l'applicazione della Differential Privacy.

```python
from masonry_core.dp_filter import sanitise

raw_data = {"score": 85.5, "count": 100}
safe_data = sanitise(raw_data)
# safe_data conterrà valori con rumore statistico aggiunto
```

---

## Creazione di un Nuovo Contratto

Per creare un contratto personalizzato, eredita da `MasonContract` e utilizza i validatori Pydantic per applicare i predicati:

```python
from pydantic import Field, field_validator
from masonry_core.contracts import MasonContract
from masonry_core.predicates import PrivacyPredicate

class MyCustomContract(MasonContract):
    phone_number: str = Field(...)
    
    @field_validator("phone_number")
    @classmethod
    def mask_phone(cls, v: str) -> str:
        return PrivacyPredicate.mask_partial(v, keep=3)
```
