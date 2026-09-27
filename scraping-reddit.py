import requests
import pandas as pd
import time
from datetime import datetime
import random

HEADERS = {"User-Agent": "projet_textmining_universitaire/1.0"}

KEYWORDS_FR = [
    "femme battue",           # Violence physique - terme le plus courant
    "violence conjugale",     # Terme générique le plus recherché
    "emprise conjugale",      # Violence psychologique - très spécifique
    "conjoint violent",       # Cible directement l'auteur masculin
    "fuir conjoint violent",  # Situation de détresse concrète
    "féminicide"              # Cas extrême - très médiatisé
]

KEYWORDS_EN = [
    "battered woman",          # Violence physique - terme classique
    "domestic violence woman", # Terme générique le plus recherché
    "abusive husband",         # Cible directement l'auteur masculin
    "coercive control partner",# Violence psychologique - très spécifique
    "leaving abusive partner", # Situation de détresse concrète
    "femicide"                 # Cas extrême - equivalent de féminicide
]


def get_posts_par_recherche(keyword, langue, limite=50):
    posts_pertinents = []
    after = None

    while len(posts_pertinents) < limite:
        url = f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=new&limit=25"
        if after:
            url += f"&after={after}"

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            # Gestion du 429 : attendre longtemps avant de réessayer
            if response.status_code == 429:
                wait_time = 60  # Attendre 60 secondes
                print(f"  ⚠️ Bloqué (429) pour '{keyword}'. Pause de {wait_time}s...")
                time.sleep(wait_time)
                continue  # Réessayer la même requête

            if response.status_code != 200:
                print(f"  Erreur {response.status_code} pour '{keyword}'")
                break

            data = response.json()["data"]
            children = data["children"]
            if not children:
                break

            for post in children:
                p = post["data"]
                if p["num_comments"] > 0:
                    posts_pertinents.append({
                        "post_id": p["id"],
                        "post_titre": p["title"],
                        "subreddit": p["subreddit"],
                        "langue": langue,
                        "url": f"https://www.reddit.com{p['permalink']}"
                    })

            after = data.get("after")
            if not after:
                break

        except Exception as e:
            print(f"  ⚠️ Exception pour '{keyword}' : {e}")
            break

        # Pause aléatoire entre 5 et 10 secondes entre chaque page
        pause = random.uniform(5, 10)
        time.sleep(pause)

    print(f"  → '{keyword}' : {len(posts_pertinents)} posts trouvés")
    return posts_pertinents


def scraper_commentaires(post_info):
    commentaires = []
    url = post_info["url"] + ".json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 429:
            print(f"  ⚠️ Bloqué (429) sur commentaires. Pause de 60s...")
            time.sleep(60)
            response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()
        comments_data = data[1]["data"]["children"]

        for comment in comments_data:
            if comment["kind"] == "t1":
                c = comment["data"]
                texte = c.get("body", "").strip()
                if not texte or texte in ["[deleted]", "[removed]"]:
                    continue
                commentaires.append({
                    "commentaire_id": c.get("id"),
                    "post_id": post_info["post_id"],
                    "post_titre": post_info["post_titre"],
                    "subreddit": post_info["subreddit"],
                    "langue": post_info["langue"],
                    "texte": texte,
                    "score": c.get("score", 0),
                    "date": datetime.fromtimestamp(c["created_utc"]).strftime("%Y-%m-%d %H:%M:%S")
                })

    except Exception as e:
        print(f"  ⚠️ Erreur commentaires : {e}")

    return commentaires


# ─── COLLECTE PRINCIPALE ───────────────────────────────────────────────

all_comments = []

print("🇫🇷 Recherche en FRANÇAIS...")
for i, keyword in enumerate(KEYWORDS_FR):
    print(f"\n[{i+1}/{len(KEYWORDS_FR)}] '{keyword}'")
    posts = get_posts_par_recherche(keyword, "français", limite=30)
    for post in posts:
        comments = scraper_commentaires(post)
        all_comments.extend(comments)
        # Pause aléatoire entre chaque post
        time.sleep(random.uniform(4, 8))
    # Pause plus longue entre chaque mot-clé
    time.sleep(random.uniform(10, 20))

print("\n🇬🇧 Recherche en ANGLAIS...")
for i, keyword in enumerate(KEYWORDS_EN):
    print(f"\n[{i+1}/{len(KEYWORDS_EN)}] '{keyword}'")
    posts = get_posts_par_recherche(keyword, "anglais", limite=30)
    for post in posts:
        comments = scraper_commentaires(post)
        all_comments.extend(comments)
        time.sleep(random.uniform(4, 8))
    time.sleep(random.uniform(10, 20))

# ─── SAUVEGARDE ────────────────────────────────────────────────────────

df = pd.DataFrame(all_comments)
df.drop_duplicates(subset="commentaire_id", inplace=True)

df.to_csv("reddit_commentaires.csv", index=False, encoding="utf-8-sig")
df[df["langue"] == "anglais"].to_csv("reddit_commentaires_en.csv", index=False, encoding="utf-8-sig")
df[df["langue"] == "français"].to_csv("reddit_commentaires_fr.csv", index=False, encoding="utf-8-sig")

print(f"\n✅ Collecte terminée !")
print(f"   Total commentaires : {len(df)}")
print(f"   En anglais        : {len(df[df['langue'] == 'anglais'])}")
print(f"   En français       : {len(df[df['langue'] == 'français'])}")