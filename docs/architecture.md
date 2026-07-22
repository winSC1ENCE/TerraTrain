# Architektur

Dieses Dokument beschreibt, wie TerraTrain intern aufgebaut ist: die Service-Landschaft, das
Datenbankschema und die beiden wichtigsten Abläufe — Athleten-Onboarding und der KI-Coaching-Agent.

## Inhalt

- [Service-Landschaft](#service-landschaft)
- [Datenbankschema](#datenbankschema)
- [Ablauf: Athlet verbinden & synchronisieren](#ablauf-athlet-verbinden--synchronisieren)
- [Ablauf: KI-Coaching-Agent](#ablauf-ki-coaching-agent)
- [Physiologische Validierung](#physiologische-validierung)

## Service-Landschaft

Vier Container, orchestriert über `docker-compose.yml` (+ `docker-compose.gpu.yml` für GPU-Beschleunigung):

```mermaid
flowchart TB
    subgraph Browser
        FE["Next.js Frontend<br/>App Router · React 19 · Tailwind v4"]
    end

    subgraph Docker["Docker Compose"]
        BE["FastAPI Backend<br/>:8000"]
        PG[("Postgres 16<br/>+ pgvector<br/>:5432")]
        OL["Ollama<br/>qwen2.5:14b + nomic-embed-text<br/>:11434"]
    end

    subgraph Extern
        IC["Intervals.icu REST API"]
    end

    FE -->|"REST (Athleten, Routen, Workouts)"| BE
    FE -->|"SSE-Stream"| BE
    BE -->|"SQLAlchemy async"| PG
    BE -->|"Chat / Tool-Use"| OL
    BE -->|"Embeddings (RAG)"| OL
    BE -->|"Sync Profil + Sessions<br/>Push Workout"| IC
```

**Warum lokal und nicht Cloud-LLM?** Trainingsdaten (Leistungswerte, Gesundheitsmetriken) bleiben
auf der eigenen Maschine. `OLLAMA_CHAT_MODEL` ist über eine Env-Var austauschbar — von `qwen2.5:7b`
auf CPU bis `llama3.3:70b` auf potenter GPU-Hardware.

## Datenbankschema

```mermaid
erDiagram
    USERS ||--o| ATHLETES : "besitzt Profil"
    ATHLETES ||--o{ ROUTES : "lädt hoch"
    ATHLETES ||--o{ WORKOUTS : "erhält"
    ATHLETES ||--o{ TRAINING_SESSIONS : "synchronisiert"
    ATHLETES ||--o{ WEEKLY_PLANS : "erstellt"
    WEEKLY_PLANS ||--o{ WORKOUTS : "beinhaltet"
    ROUTES ||--o{ WORKOUTS : "referenziert"

    USERS {
        uuid id PK
        string email
        string hashed_password
        string role
        boolean is_active
    }
    ATHLETES {
        uuid id PK
        uuid user_id FK
        string intervals_user_id
        string name
        string sport
        int ftp_watts
        float weight_kg
        int lthr
        jsonb training_zones
        text intervals_api_key_encrypted
    }
    WEEKLY_PLANS {
        uuid id PK
        uuid athlete_id FK
        date start_date
        string mesocycle_type
        string week_type
        text coach_rationale
        text notes
    }
    ROUTES {
        uuid id PK
        uuid athlete_id FK
        string name
        float distance_m
        float elevation_gain_m
        jsonb climb_profile
        float terrain_score
        jsonb analysis
    }
    WORKOUTS {
        uuid id PK
        uuid athlete_id FK
        uuid route_id FK
        uuid weekly_plan_id FK
        string name
        string workout_type
        string status
        text structured_text
        jsonb llm_plan
        float target_tss
    }
    TRAINING_SESSIONS {
        uuid id PK
        uuid athlete_id FK
        string intervals_activity_id
        datetime start_date
        float tss
        float avg_power_watts
    }
    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id
        string document_title
        text content
        vector embedding
    }
```

`document_chunks` gehört bewusst zu keinem Athleten — die Wissensbasis (RAG) ist global und speist
jede Coaching-Anfrage.

## Ablauf: Athlet verbinden & synchronisieren

```mermaid
sequenceDiagram
    actor U as Nutzer
    participant FE as Frontend (/connect)
    participant BE as Backend
    participant IC as Intervals.icu

    U->>FE: Athleten-ID + API-Key eingeben
    FE->>BE: POST /athletes
    BE->>BE: API-Key verschlüsseln (Fernet), speichern
    BE-->>FE: Athlet erstellt (UUID)
    FE->>BE: POST /athletes/{id}/sync
    BE->>IC: GET /athlete/{id}/activities
    BE->>IC: GET /athlete/{id} (Profil: FTP, LTHR, Gewicht)
    IC-->>BE: Sessions + Profil
    BE->>BE: In training_sessions speichern,<br/>FTP/LTHR/Gewicht übernehmen
    BE-->>FE: {sessions_synced, profile_updated}
    FE->>FE: Athlet im zustand-Store ablegen<br/>(nie wieder UUID-Eingabe)
    FE-->>U: Erfolg — weiter zum Dashboard
```

Athleten, deren Aktivitäten über Strava laufen, haben oft leere `training_sessions.tss` (Stravas
API-Bedingungen blockieren Aktivitätsdetails für Drittanbieter). Der Fitness-Endpoint erkennt das
und fällt automatisch auf Intervals.icus eigene CTL/ATL-Werte aus deren `/wellness`-Endpoint zurück
— siehe `services/fitness_service.py`.

## Ablauf: KI-Coaching-Agent

Der Coach ist ein handgeschriebener Tool-Use-Loop (kein LangChain/CrewAI) über Ollamas Chat-API,
mit einer harten Validierungs-Schleife, damit die KI keine physiologisch unmöglichen Workouts
produzieren kann.

```mermaid
sequenceDiagram
    actor U as Nutzer
    participant FE as Frontend (/coach)
    participant BE as CoachingAgent
    participant RAG as RAG-Service (pgvector)
    participant LLM as Ollama

    U->>FE: Workout-Typ + Route + Notizen
    FE->>BE: POST /coaching/generate (SSE)
    BE->>BE: Kontext sammeln:<br/>Athletenprofil, CTL/ATL/TSB, Routen-Terrain
    BE->>RAG: Trainingswissenschaft zum Workout-Typ abfragen
    RAG-->>BE: Top-5 Textabschnitte
    BE->>BE: System-Prompt bauen (Regeln + Gut-Beispiel)

    loop Agent-Loop (max. 8 Runden)
        BE->>LLM: Chat + Tools (calculate_zones, estimate_tss, ...)
        LLM-->>BE: Tool-Call oder final_answer
        BE-->>FE: SSE: thinking / tool_call / tool_result
        alt final_answer erhalten
            BE->>BE: WorkoutFormatter.validate()<br/>(Intervallgrenzen, Warmup/Cooldown, TSS-Konsistenz)
            alt Validierung fehlgeschlagen (1. Versuch)
                BE->>LLM: Fehler als Tool-Result zurück, Korrektur anfordern
            else Validierung OK
                BE->>BE: In Intervals.icu-DSL formatieren, Workout speichern
            end
        end
    end

    BE-->>FE: SSE: workout_plan (finaler Plan)
    FE-->>U: Phasen-Balken + Intervals.icu-Text + Push-Button
```

## Physiologische Validierung

`WorkoutFormatter.validate()` (`apps/backend/src/terratrain/services/workout_formatter.py`) lehnt
Pläne ab, die diese Regeln verletzen:

| Regel | Grenze |
|---|---|
| Intervalle über 105 % FTP | max. 8 min pro Intervall |
| Schwellenintervalle (95–105 % FTP) | max. 30 min pro Intervall |
| Gesamtzeit ≥ 95 % FTP | max. 60 min pro Einheit |
| Erste Phase | Warmup: ≤ 75 % FTP, ≥ 5 min |
| Letzte Phase | Cooldown: ≤ 75 % FTP |
| Ziel-TSS vs. berechnetes TSS | max. ±30 % Abweichung |

Verstößt ein von der KI generierter Plan gegen eine Regel, bekommt die KI die konkrete Fehlermeldung
als Tool-Ergebnis zurück und darf **einmal** nachbessern, bevor der Stream mit einer Fehlermeldung
endet. Das ist der Fix für den ursprünglichen Fall "4×45 Min bei 100 % FTP".

## Ablauf: KI-Wochenplaner-Agent & Mesozyklus-Erkennung

Der Wochenplaner ([`WeeklyCoachingAgent`](file:///home/winscience/src/github/TerraTrain/apps/backend/src/terratrain/services/weekly_coaching_agent.py)) koordiniert die Erstellung eines periodisierten Wochenplans:

1. **Mesozyklus-Erkennung ([`MesocycleDetector`](file:///home/winscience/src/github/TerraTrain/apps/backend/src/terratrain/services/mesocycle_detector.py))**:
   - Berechnet die wöchentliche TSS-Summe der letzten 4 Wochen aus den importierten Aktivitätsdaten (`TRAINING_SESSIONS`).
   - Schlägt basierend auf Periodisierungs-Zyklen (`3-1` oder `2-1`) und dem Belastungsverlauf den Wochentyp vor (z. B. Erholungswoche, falls 3 Wochen progressive TSS-Belastung vorausgingen).
2. **Generierungs-Loop**:
   - Sendet den gesamten Wochenplanentwurf (ausgewählte Wochentage, GPX-Routen, Zieldauern) an das LLM.
   - Das LLM liefert über ein strukturiertes JSON-Schema alle Workouts der Woche in einem einzigen Tool-Call zurück.
   - Der Agent führt für jedes generierte Workout die physiologische Validierungsprüfung ([`WorkoutFormatter.validate`](file:///home/winscience/src/github/TerraTrain/apps/backend/src/terratrain/services/workout_formatter.py)) durch und fordert im Fehlerfall Nachbesserung an.
   - Nach erfolgreicher Validierung werden der `WeeklyPlan` sowie die einzelnen `Workout`-Einträge in der PostgreSQL-Datenbank abgelegt.

