# Aeon's End Assistant

A web application that assists with card randomization for the [Aeon's End](https://www.boardgamegeek.com/boardgame/191189/aeons-end) series of board games. Handles both single-game randomization and full expedition mode, including persistent barracks management across battles.

---

## What It Does

Aeon's End involves randomizing a player supply of gems, relics, and spells, selecting breach mages, and drawing a nemesis at the start of each game. With 9 waves of content, the sheer volume of randomizer cards makes setup tedious. This app automates that process.

**Single game (Quickplay):** Randomly select a supply, mages, and nemesis from your owned sets.

**Expedition mode:** Manage a persistent campaign across multiple battles. The app tracks your barracks (available cards and mages), handles post-battle randomizer draws, and enforces banishing rules between fights. Supports Standard, Short, Extended, and Big Pockets variants.

Card data is sourced from the [Aeon's End wiki](https://aeonsend.wiki.gg) via its MediaWiki API, scraped once at setup and cached locally — the wiki is not queried at runtime.

---

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS
- **Backend:** Python, FastAPI, SQLModel, PostgreSQL 15, Alembic
- **Infrastructure:** Docker, Docker Compose, AWS EC2
- **CI/CD:** GitHub Actions (tests on PR, deploy to EC2 on merge to main)
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

**6. Open the app**

- Frontend: `http://localhost:5173`
- API (Swagger UI): `http://localhost:8000/docs`

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
| GET | `/sets/saved` | Get the user's saved set preferences |
| PUT | `/sets/saved` | Update the user's owned sets |

### Quickplay
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/quickplay` | Generate a single-game randomization (`?num_mages=N`) |

### Expeditions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/expeditions` | List all expeditions |
| POST | `/expeditions` | Create a new expedition and draw the initial barracks |
| GET | `/expeditions/{id}` | Get full expedition state (barracks, mages, battles) |
| POST | `/expeditions/{id}/resolve-battle` | Record a win or loss and draw new randomizers |
| POST | `/expeditions/{id}/lock-supply` | Banish cards not selected for the next battle |
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
│   │       ├── quickplay.py
│   │       └── expeditions.py
│   ├── ingestion/
│   │   ├── seed.py          # Wiki API ingestion script
│   │   └── cache/           # Cached card JSON files
│   ├── tests/               # pytest test suite
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Home, Quickplay, SetSelection, Expedition views
│   │   ├── components/
│   │   ├── api.ts           # API client
│   │   └── types.ts         # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/
│   ├── ci.yml               # Run tests on push/PR to develop or main
│   └── deploy.yml           # Deploy to EC2 on push to main
├── docker-compose.yml
├── .env.example
└── reseed.sh
```

---

## Notes

- Treasures are not handled by this application.
- Legacy content filtering and Outcasts mode support are planned for a future version.
