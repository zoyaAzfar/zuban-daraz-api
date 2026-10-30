# Zuban Daraz South Asian Proverb API

A free, open API and dataset of ~500 South Asian proverbs across 15 languages, each with an English translation and a theme.  

**Base URL:** `https://zuban-daraz-proverb-api.zoe-azfar.workers.dev`

## Quick start

```bash
curl "https://zuban-daraz-proverb-api.zoe-azfar.workers.dev/v1/proverbs/random"
```

```json
{ "data": { "id": 12, "proverb": "…", "translation": "…", "language": "Punjabi", "theme": "Animals" } }
```

## Python

```bash
pip install zubandaraz
# or straight from GitHub:
pip install git+https://github.com/YOUR-USERNAME/zuban-daraz-api.git
```

```python
from zubandaraz import Client

api = Client()

p = api.random(theme="Animals")
print(p.proverb, "->", p.translation, f"({p.language})")

for p in api.iter_all(language="Punjabi"):      # pages handled for you
    print(p.proverb)

print(api.themes())      # [{'name': 'Animals', 'count': 22}, ...]
print(api.languages())
```

Prefer plain `requests`? That works too:

```python
import requests
r = requests.get("https://zuban-daraz-proverb-api.zoe-azfar.workers.dev/v1/proverbs", params={"theme": "Marriage", "limit": 10})
print(r.json()["data"])
```

## JavaScript

```js
const res = await fetch("https://zuban-daraz-proverb-api.zoe-azfar.workers.dev/v1/proverbs/random");
const { data } = await res.json();
```

CORS is enabled, so this works directly in the browser.

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /v1/proverbs` | List. Params: `language`, `theme`, `q` (search), `limit` (1–100, default 20), `offset` |
| `GET /v1/proverbs/{id}` | One proverb |
| `GET /v1/proverbs/random` | Random proverb; accepts `language` and `theme` |
| `GET /v1/languages` | Languages with counts |
| `GET /v1/themes` | Themes with counts |

Fields: `id`, `proverb`, `translation` (English, literal), `language`, `theme` (may be `null`).
Responses are cached for 5 minutes.

## Full dataset

Want everything at once? Download [`data/proverbs.json`](data/proverbs.json) or [`data/proverbs.csv`](data/proverbs.csv) instead of paging through the API. Please use the files for bulk or repeated use, since the API runs on a free tier.

## Fair use

No key is required. Please be considerate: cache responses and use the data files for bulk work. Heavy automated use may be rate-limited.

## Contributing

Corrections and new proverbs are welcome. Data changes go through review rather than pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

- **Data** (proverbs, translations, themes): [CC BY-SA 4.0](DATA_LICENSE.md). Please credit "Zuban Daraz".
- **Code** (Worker + Python client): [MIT](LICENSE).

**Citation:** Zuban Daraz South Asian Proverb API. https://github.com/zoyaAzfar/zuban-daraz-api
