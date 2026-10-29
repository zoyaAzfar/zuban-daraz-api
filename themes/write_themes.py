import json
import os

import libsql_client

client = libsql_client.create_client_sync(
    url=os.environ["TURSO_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],   # needs a read-WRITE token
)

try:
    client.execute("ALTER TABLE entries ADD COLUMN theme TEXT")
    print("Added 'theme' column")
except Exception as e:
    print("Column probably already exists, continuing:", e)

with open("theme_assignments.json", encoding="utf-8") as f:
    rows = json.load(f)

for r in rows:
    theme = None if r["theme"] == "Uncategorized" else r["theme"]
    client.execute("UPDATE entries SET theme = ? WHERE id = ?", [theme, r["rowid"]])
print(f"Updated {len(rows)} rows")

check = client.execute(
    "SELECT COALESCE(theme, '(none)'), COUNT(*) FROM entries "
    "WHERE status='approved' AND LOWER(pos)='idiom' GROUP BY theme ORDER BY 2 DESC"
)
for theme, count in check.rows:
    print(f"{count:4d}  {theme}")

client.close()
