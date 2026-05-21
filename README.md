# Aeon's End Assistant

A web application that assists with card randomization for the [Aeon's End](https://www.boardgamegeek.com/boardgame/191189/aeons-end) series of board games. Handles both single-game randomization and full expedition mode, including persistent barracks management across battles.

> **Status:** Backend complete. Frontend in progress.

---

## What It Does

Aeon's End involves randomizing a player supply of gems, relics, and spells, selecting breach mages, and drawing a nemesis at the start of each game. With 9 waves of content, the sheer volume of randomizer cards makes setup tedious. This app automates that process.

**Single game:** Randomly select a supply, mages, and nemesis from your owned sets.

**Expedition mode:** Manage a persistent campaign across multiple battles. The app tracks your barracks (available cards and mages), handles post-battle randomizer draws, and enforces banishing rules between fights. Supports Standard, Short, Extended, and Big Pockets variants.

Card data is sourced from the [Aeon's End wiki](https://aeonsend.wiki.gg) via its MediaWiki API.

---

## Tech Stack

- **Backend:** Python, FastAPI, SQLModel, PostgreSQL, Alembic
- **Infrastructure:** Docker, Docker Compose
- **Data Ingestion:** Python, MediaWiki API, mwparserfromhell

---

## Getting Started

### Prerequisites

- Docker Desktop
- Git

### Setup

**1. Clone the repository**
```bash
git clone https://github.com/timothygaus/AeonsEndAssistant.git
cd AeonsEndAssistant
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```
Fill in your preferred Postgres credentials in `.env`.

**3. Start the containers**
```bash
docker-compose up --build -d
```

**4. Run database migrations**
```bash
docker-compose exec api alembic upgrade head
```

**5. Seed the database**

Pulls card data from the Aeon's End wiki. Takes several minutes on first run due to API rate limiting — subsequent runs use a local cache.
```bash
docker-compose exec api python -u -m ingestion.seed
```

**6. Verify the API is running**

Visit `http://localhost:8000/docs` to explore the API via Swagger UI.

---

## Reseeding

A convenience script is included to wipe and recreate the database from scratch:
```bash
./reseed.sh
```

---

## API Overview

### Sets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sets` | List all available sets |

### Expeditions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/expeditions` | List all expeditions |
| POST | `/expeditions` | Create a new expedition and draw the initial barracks |
| GET | `/expeditions/{id}` | Get full expedition state (barracks, mages, battles) |
| POST | `/expeditions/{id}/resolve-battle` | Record a win or loss and draw new randomizers |
| POST | `/expeditions/{id}/select-supply` | Select the 9 supply cards for the next fight, banishing the rest |
| DELETE | `/expeditions/{id}` | Delete an expedition |

### Creating an expedition

```json
POST /expeditions
{
  "name": "My Expedition",
  "set_ids": [1, 2, 3],
  "variant": "standard"
}
```

Supported variants: `standard`, `short`, `extended`, `big_pockets`

---

## Project Structure

```
AeonsEndAssistant/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app and router registration
│   │   ├── database.py      # Engine and session setup
│   │   ├── models.py        # SQLModel table definitions
│   │   ├── schemas.py       # Request/response schemas
│   │   ├── enums.py         # Shared enums
│   │   └── routers/
│   │       ├── sets.py
│   │       └── expeditions.py
│   ├── ingestion/
│   │   └── seed.py          # Wiki API ingestion script
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── reseed.sh
```

---

## Notes

- Card data is scraped once at setup and cached locally during development. The wiki is not queried at runtime.
- Treasures are not handled by this application.
- Legacy content filtering and Outcasts mode support are planned for a future version.