import json
import os
import textwrap

import libsql_client
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import umap
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------- config
# export TURSO_URL="libsql://..."  and  export TURSO_AUTH_TOKEN="..."  (use a NEW, ideally read-only token)
TURSO_URL = os.environ["TURSO_URL"]
AUTH_TOKEN = os.environ["TURSO_AUTH_TOKEN"]

MIN_SCORE = 0.20          # below this -> "Uncategorized". Set None to force-assign everything.
EDGE_MIN_SIM = 0.40       # minimum similarity for a link
EDGE_TOP_K = 3            # max links per node
MODEL_NAME = "all-MiniLM-L6-v2"   # try "all-mpnet-base-v2" for better quality

# ---------------------------------------------------------------- themes
# Keys are the names shown on the website (no more themeMap needed).
# Values are phrases averaged into one theme vector. Edit freely.
THEMES = {
    "Chastity & Modesty": [
        "a prostitute or loose woman", "chastity and a woman's honour",
        "modesty and shame", "adultery and immoral women",
    ],
    "Talkativeness": [
        "laughing and mockery", "too much talking and gossip",
        "a sharp tongue and words", "speaking and keeping silent",
    ],
    "Cunning & Evil": [
        "the devil and evil", "cunning tricks and deceit",
        "a crafty person full of wiles", "wickedness and treachery",
    ],
    "Bride & Wife": [
        "a bride on her wedding", "a wife and her husband",
        "a new daughter-in-law in the house", "a quarrelsome wife",
    ],
    "In-Laws": [
        "mother-in-law and daughter-in-law", "father-in-law and sister-in-law",
        "husband's family and relatives by marriage", "in-laws' house",
    ],
    "Eating Habits": [
        "eating food and bread", "hunger and a full stomach",
        "cooking, meals and a feast", "milk, butter, sweets and grain",
    ],
    "Idle & Useless": [
        "a lazy idle person", "useless and good for nothing",
        "doing nothing and wasting time", "empty effort with no result",
    ],
    "Authority": [
        "a king, ruler or chief", "orders, power and authority",
        "a leader and his followers", "master and servant",
    ],
    "Intelligence": [
        "a clever and intelligent person", "wisdom and sharp wit",
        "a fool and stupidity", "using your brain",
    ],
    "Age": [
        "young age and youth", "old age and the elderly",
        "an old man or old woman", "growing up and growing old",
    ],
    "Property & Wealth": [
        "money, wealth and riches", "land, house and property",
        "poverty and being poor", "debt, trade and gold",
    ],
    "Marriage": [
        "marriage and wedding", "a match, betrothal and dowry",
        "getting married", "husband and wife relationship",
    ],
    "Children": [
        "a son and his parents", "a daughter and her mother",
        "children and a child", "birth of a boy or girl",
    ],
    "Animals": [
        "a deer, buffalo or cow", "a dog, cat or donkey",
        "a horse, camel or goat", "a bird, snake or wild animal",
    ],
}
THEME_NAMES = list(THEMES)
OTHER = "Uncategorized"   # must match the default used in the Flask route

PALETTE = [
    "#d3968c", "#839958", "#4aa3b8", "#c49a45", "#b85d43", "#708d91",
    "#b58a96", "#a3b18a", "#e0a458", "#c3b3a3", "#7fb7be", "#e6c35c",
    "#b07fb0", "#6b9080",
]
THEME_COLOR = {t: PALETTE[i % len(PALETTE)] for i, t in enumerate(THEME_NAMES)}
THEME_COLOR[OTHER] = "#9a9a9a"

# ---------------------------------------------------------------- load data
client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=AUTH_TOKEN)
result = client.execute(
    "SELECT id, word, literal_definition, language FROM entries "
    "WHERE status='approved' AND LOWER(pos) LIKE '%idiom%'"
)
client.close()

entries = [
    {"rowid": int(r[0]), "word": r[1], "literal_definition": r[2], "language": r[3]}
    for r in result.rows
]
print(f"Loaded {len(entries)} entries")

# ---------------------------------------------------------------- embeddings
print("Loading AI model...")
model = SentenceTransformer(MODEL_NAME)
emb = normalize(model.encode([e["literal_definition"] or "" for e in entries]))

theme_emb = np.array([
    normalize(normalize(model.encode(THEMES[n])).mean(axis=0, keepdims=True))[0]
    for n in THEME_NAMES
])

# ---------------------------------------------------------------- assignment
sims = emb @ theme_emb.T
best_idx = sims.argmax(axis=1)
best_score = sims.max(axis=1)

assigned, umap_labels = [], []
for idx, score in zip(best_idx, best_score):
    if MIN_SCORE is not None and score < MIN_SCORE:
        assigned.append(OTHER)
        umap_labels.append(-1)            # unlabeled for semi-supervised UMAP
    else:
        assigned.append(THEME_NAMES[idx])
        umap_labels.append(int(idx))

print("\nBest-score percentiles (10/25/50/75/90):",
      np.round(np.percentile(best_score, [10, 25, 50, 75, 90]), 3))
print("Theme counts:")
for t in THEME_NAMES + [OTHER]:
    print(f"  {assigned.count(t):4d}  {t}")

# ---------------------------------------------------------------- UMAP
reducer = umap.UMAP(
    n_components=3, metric="cosine", n_neighbors=15,
    min_dist=0.4, target_weight=0.3, random_state=41,
)
pos_3d = np.round(reducer.fit_transform(emb, y=np.array(umap_labels)), 4)

# ---------------------------------------------------------------- edges (same theme, top-K neighbours)
edges = set()
for theme in THEME_NAMES:
    idx = np.array([i for i, a in enumerate(assigned) if a == theme])
    if len(idx) < 2:
        continue
    sub = emb[idx] @ emb[idx].T
    np.fill_diagonal(sub, -1)
    k = min(EDGE_TOP_K, len(idx) - 1)
    top = np.argsort(-sub, axis=1)[:, :k]
    for a in range(len(idx)):
        for b in top[a]:
            if sub[a, b] > EDGE_MIN_SIM:
                i, j = sorted((int(idx[a]), int(idx[b])))
                edges.add((i, j))

edge_x, edge_y, edge_z = [], [], []
for a, b in edges:
    edge_x += [float(pos_3d[a][0]), float(pos_3d[b][0]), None]
    edge_y += [float(pos_3d[a][1]), float(pos_3d[b][1]), None]
    edge_z += [float(pos_3d[a][2]), float(pos_3d[b][2]), None]

traces = [go.Scatter3d(
    x=edge_x, y=edge_y, z=edge_z, mode="lines",
    line=dict(color="rgba(255,255,255,0.18)", width=1),
    hoverinfo="none", showlegend=False, name="links",
)]

# ---------------------------------------------------------------- one marker trace per theme
def hover_for(i):
    e = entries[i]
    definition = "<br>".join(textwrap.wrap(e["literal_definition"] or "No translation", 60))
    return f"<b>{e['word']}</b><br>{definition}<br><i>{e['language']}</i>"

for theme in THEME_NAMES + [OTHER]:
    idx = [i for i, a in enumerate(assigned) if a == theme]
    if not idx:
        continue
    traces.append(go.Scatter3d(
        x=pos_3d[idx, 0].tolist(), y=pos_3d[idx, 1].tolist(), z=pos_3d[idx, 2].tolist(),
        mode="markers",
        name=theme, legendgroup=theme, showlegend=True,
        hoverinfo="text", text=[hover_for(i) for i in idx],
        # [entry id, theme, language] -> the Flask route reads the id -> theme map from here
        customdata=[[entries[i]["rowid"], theme, entries[i]["language"]] for i in idx],
        marker=dict(color=THEME_COLOR[theme], size=6, line=dict(width=0)),
    ))

axis_style = dict(showgrid=False, zeroline=False, showticklabels=False,
                  showbackground=False, title="", visible=False)
fig = go.Figure(data=traces)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, b=0, t=0), showlegend=True,
    scene=dict(xaxis=axis_style, yaxis=axis_style, zaxis=axis_style, dragmode="turntable"),
)

# ---------------------------------------------------------------- outputs
with open("galaxy_graph.json", "w", encoding="utf-8") as f:
    f.write(pio.to_json(fig))          # upload this one

preview = go.Figure(fig)               # standalone preview with your site's dark green bg
preview.update_layout(paper_bgcolor="#0a3323", font=dict(color="white"))
preview.write_html("galaxy_preview.html", include_plotlyjs="cdn")

with open("theme_assignments.json", "w", encoding="utf-8") as f:
    json.dump(
        [{"rowid": e["rowid"], "word": e["word"], "language": e["language"],
          "theme": assigned[i], "score": round(float(best_score[i]), 4)}
         for i, e in enumerate(entries)],
        f, ensure_ascii=False, indent=1,
    )

print("\nDone: galaxy_graph.json (upload), galaxy_preview.html (open locally), theme_assignments.json")
