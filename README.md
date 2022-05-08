Ondrej Špánik

```
Python 3.10.2
Django 4.0
```

## SQL Queries

### Zadanie 2

> /v1/health

```sql
SELECT VERSION() as version,
pg_database_size('dota2')/1024/1024 as dota2_db_size;
```

### Zadanie 3

> /v2/patches

```sql
WITH my_patches AS
(
    SELECT name                                     as patch_version, 
         EXTRACT(EPOCH FROM release_date)::integer  as patch_start_date, 
    LEAD(EXTRACT(EPOCH FROM release_date)::integer, 1) OVER (ORDER BY name)      
                                                    as patch_end_date
    FROM patches
    ORDER BY patch_version ASC
)
SELECT my_patches.*, 
matches.id                                          as match_id, 
ROUND(matches.duration::decimal / 60, 2)            as duration
FROM my_patches 
LEFT OUTER JOIN matches ON (matches.start_time >= my_patches.patch_start_date AND 
                            matches.start_time <= COALESCE(my_patches.patch_end_date,
                            EXTRACT(EPOCH FROM NOW())::integer));

```

> /v2/players/<player_id>/game_exp

```sql
SELECT players.id                             as id, 
COALESCE(players.nick, 'unknown')             as player_nick, 
matches.id                                    as match_id,
heroes.localized_name                         as hero_localized_name, 
ROUND(matches.duration::decimal / 60, 2)      as match_duration_minutes, 
(COALESCE(mpd.xp_hero,0) + 
 COALESCE(mpd.xp_creep,0) + 
 COALESCE(mpd.xp_other,0) + 
 COALESCE(mpd.xp_roshan,0))                   as experiences_gained, 
mpd.level                                     as level_gained,
CASE WHEN     matches.radiant_win AND mpd.player_slot >= 0   AND mpd.player_slot <= 4   THEN true
     WHEN not matches.radiant_win AND mpd.player_slot >= 128 AND mpd.player_slot <= 132 THEN true
     ELSE false
END                                           as winner
FROM matches_players_details as mpd
INNER JOIN heroes ON (mpd.hero_id = heroes.id) 
INNER JOIN matches ON (mpd.match_id = matches.id) 
INNER JOIN players ON (mpd.player_id = players.id)
WHERE player_id = """ + str(secure_player_id) + """ 
ORDER BY matches.id ASC;
```

> /v2/players/<player_id>/game_objectives

```sql
SELECT players.id                          as id, 
COALESCE(players.nick,'unknown')           as player_nick, 
matches.id                                 as match_id, 
heroes.localized_name                      as hero_localized_name, 
COALESCE(gobj.subtype, 'NO_ACTION')        as hero_action,
COUNT(COALESCE(gobj.subtype, 'NO_ACTION')) as count
FROM matches_players_details as mpd 
INNER JOIN heroes ON (mpd.hero_id = heroes.id) 
INNER JOIN matches ON (mpd.match_id = matches.id) 
INNER JOIN players ON (mpd.player_id = players.id) 
FULL OUTER JOIN game_objectives as gobj ON (mpd.id = gobj.match_player_detail_id_1)
WHERE player_id = """ + str(secure_player_id) + """ 
GROUP BY players.id, player_nick, matches.id, heroes.localized_name, hero_action;

```

> /v2/players/<player_id>/abilities

```sql
SELECT players.id                      as id, 
COALESCE(players.nick,'unknown')       as player_nick, 
matches.id                             as match_id, 
heroes.localized_name                  as hero_localized_name, 
ab.name                                as ability_name, 
COUNT(ab.name)                         as count,
MAX(au.level)                          as upgrade_level 
FROM matches_players_details as mpd
INNER JOIN heroes ON (mpd.hero_id = heroes.id) 
INNER JOIN matches ON (mpd.match_id = matches.id) 
INNER JOIN players ON (mpd.player_id = players.id) 
INNER JOIN ability_upgrades as au ON (mpd.id = au.match_player_detail_id)
INNER JOIN abilities as ab ON (au.ability_id = ab.id)
WHERE player_id = """ + str(secure_player_id) + """ 
GROUP BY players.id, player_nick, matches.id, heroes.localized_name, ab.name;
```

### Zadanie 3

> /v3/matches/21421/top_purchases/

```sql
SELECT id, name, item_id, item_name, item_count FROM (
SELECT mpd.hero_id as id, 
h.localized_name as name, 
pl.item_id as item_id, 
i.name as item_name, 
count(pl.item_id) as item_count,
ROW_NUMBER() OVER (
PARTITION BY mpd.hero_id 
ORDER BY mpd.hero_id ASC, count(pl.item_id) DESC, i.name DESC) as row

FROM matches_players_details as mpd 
INNER JOIN matches as m ON m.id = mpd.match_id
INNER JOIN heroes as h ON h.id = mpd.hero_id
INNER JOIN purchase_logs as pl ON mpd.id = pl.match_player_detail_id
INNER JOIN items as i ON i.id = pl.item_id

WHERE match_id = """ + str(secure_match_id) + """
AND ((m.radiant_win AND player_slot >= 0 AND player_slot <= 4) OR 
	(player_slot >= 128 AND player_slot <= 132)) 
GROUP BY mpd.hero_id, h.localized_name, pl.item_id, i.name 
ORDER BY id ASC, item_count DESC, item_name DESC

) as x WHERE row <= 5;
```

> /v3/abilities/5004/usage/

```sql
SELECT *, COUNT(bucket) as count
FROM (SELECT 
a.id                as ability_id, 
a.name              as ability_name, 
mpd.hero_id         as hero_id, 
h.localized_name    as hero_name, 
CASE WHEN m.radiant_win AND mpd.player_slot >= 0 AND mpd.player_slot <= 4 THEN true
WHEN not m.radiant_win AND mpd.player_slot >= 128 AND mpd.player_slot <= 132 THEN true
ELSE false END as winner,
CASE WHEN percentage >= 0 AND percentage < 10 THEN '0-9'
WHEN percentage >= 10 AND percentage < 20 THEN '10-19'
WHEN percentage >= 20 AND percentage < 30 THEN '20-29'
WHEN percentage >= 30 AND percentage < 40 THEN '30-39'
WHEN percentage >= 40 AND percentage < 50 THEN '40-49'
WHEN percentage >= 50 AND percentage < 60 THEN '50-59'
WHEN percentage >= 60 AND percentage < 70 THEN '60-69'
WHEN percentage >= 70 AND percentage < 80 THEN '70-79'
WHEN percentage >= 80 AND percentage < 90 THEN '80-89'
WHEN percentage >= 90 AND percentage < 100 THEN '90-99'
ELSE '100-109' END as bucket
FROM ability_upgrades as au
INNER JOIN abilities as a ON a.id = au.ability_id
INNER JOIN matches_players_details as mpd ON mpd.id = au.match_player_detail_id
INNER JOIN matches as m ON m.id = mpd.match_id
INNER JOIN heroes as h ON h.id = mpd.hero_id,
LATERAL COALESCE((au.time::decimal / m.duration::decimal) * 100) as sub(percentage)
WHERE a.id = """ + str(secure_ability_id) + """
) as x 
GROUP BY ability_id, ability_name, winner, hero_id, hero_name, bucket
ORDER BY hero_id ASC, winner DESC, count DESC;
```

> /v3/statistics/tower_kills/

```sql
SELECT hero_id as id, h.localized_name as name, MAX(match_heroid_sequence) as tower_kills
FROM(
SELECT time, hero_id, match_id,
ROW_NUMBER() OVER (PARTITION BY match_id, hero_id, match_content_counting - match_heroid_counting ORDER BY match_content_counting) as match_heroid_sequence
FROM(
SELECT time, hero_id, match_id,  
ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY time) as match_content_counting,
ROW_NUMBER() OVER (PARTITION BY match_id, hero_id ORDER BY match_id, time) as match_heroid_counting
FROM (
SELECT gao.id, gao.match_player_detail_id_1 as mpd_id, gao.time, gao.subtype, mpd1.hero_id, mpd1.match_id
FROM game_objectives as gao
INNER JOIN matches_players_details as mpd1 ON mpd1.id = gao.match_player_detail_id_1
WHERE gao.subtype = 'CHAT_MESSAGE_TOWER_KILL' AND (gao.match_player_detail_id_1 IS NOT NULL OR gao.match_player_detail_id_2 IS NOT NULL)
UNION ALL
SELECT gao.id, gao.match_player_detail_id_2 as mpd_id, gao.time, gao.subtype, mpd2.hero_id, mpd2.match_id
FROM game_objectives as gao
INNER JOIN matches_players_details as mpd2 ON mpd2.id = gao.match_player_detail_id_2
WHERE gao.subtype = 'CHAT_MESSAGE_TOWER_KILL' AND (gao.match_player_detail_id_1 IS NOT NULL OR gao.match_player_detail_id_2 IS NOT NULL)
ORDER BY match_id, time
) AS x 
) AS x
ORDER BY match_id, time
) AS x
INNER JOIN heroes as h ON h.id = hero_id
GROUP BY hero_id, h.localized_name
ORDER BY MAX(match_heroid_sequence) DESC, id DESC;
```

### Zadanie 4

**Časť 1:**

Modely `myapp.models` vygenerované pomocou `inspectdb`, prečistené a funkčnosť skontrolovaná.

Súčasťou bolo sprevádzkovanie DB routeru a čistenie podľa komentárov v hlavičke `myapp.models`.

**Časť 2:**

Použité bolo Django ORM, i keď retrospektívne SQL Alchemy sa mi pozdáva o dosť viac.

Implementované:

> /v2/patches

1x `patches` ORM query, 1x `matches` ORM query, následne spracovanie na strane web servera

> /v2/players/<player_id>/game_exp

1x `matches_players_details` ORM query s filter a select_related, následne spracovanie na strane web servera

> /v2/players/<player_id>/game_objectives

1x `matches_players_details` ORM query s filter a select_related, následne Nx `game_objectives` ORM query (viem že to je dosť low-quality, pokúsil som sa o chained filter, aby stačila jedna query, ale ten zjavne nefunguje ako by som chcel), následne spracovanie na strane web servera

> /v2/players/<player_id>/abilities

1x `matches_players_details` ORM query s filter a select_related, následne Nx `ability_upgrades` ORM query (viem že to je dosť low-quality, pokúsil som sa o chained filter, aby stačila jedna query, ale ten zjavne nefunguje ako by som chcel), následne spracovanie na strane web servera

> /v3/...

nevypracované

**Časť 3:**

nevypracované

## Sprevádzkovanie

1. jednorázovo: `python -m venv venv` vytvorí virtuálny environment
2. `venv/Scripts/activate.bat` pre **aktiváciu virtuálneho environmentu** 

> prípadne na linuxoch to môže byť `./venv/bin/activate`, názov je hlavný

3. **environment variables aktivácia** cez `env_dev.bat` (lokálna DB u mňa alebo `env_prod.bat` pre lokálne použitie FIIT databázy zo zadania) 

> nie je súčasť repozitára kvôli bezpečnosti, obsah je nasledovný:

```powershell
@echo off
set DBHOST=zo zadania pre env_prod alebo lokalna pre env_dev
set DBNAME=dota2
set DBUSER=ais login
set DBPASS=ais heslo
:: debug je lokalne vzdy 1, na digitalocean je 0
set DEBUG=1
set SECRET_KEY=nieco nahodne som prebehol cez SHA-1
```

4. nepovinné: kontrola funkčnosti venv pomocou `which python` alebo `where python`

> ak sa nepoužíva python v lokálnej venv zložke, tak treba venv odstrániť, reinštalovať python (ideálne na spomenutú verziu) a ísť od 1.
>
> u mňa sa tento problém vyskytol pretože môj msys2 mingw sa rozhodol byť preferovaný v PATH a teda som používal niečo ako "unixový build pythonu na windowse", nemal som ani activate.bat a venv odmietal akokoľvek fungovať

5. jednorázovo: `pip install -r requirements.txt` pre inštaláciu packages

6. hotovo, ak je správne nakonfigurovaný prístup k DB tak by mal fungovať Django webserver pomocou `python manage.py runserver`

> v budúcnosti už treba aplikovať len 2. a 3. krok po otvorení terminálu a pred prácou s manage.py

## DigitalOcean deployment

Zdroj: https://docs.digitalocean.com/tutorials/app-deploy-django-app/#step-4-deploying-to-digitalocean-with-app-platform

- Beží to na GitHub Student Benefits $100 promo kóde
- Využíva **gunicorn** (nedostupné na Windowse, ale momentálne nevidím pre seba využitie, Windows alternatíva je vraj waitress https://stackoverflow.com/a/66485423)
- Použitý spomenutý run command `gunicorn --worker-tmp-dir /dev/shm mysite.wsgi` kde `mysite.wsgi` je meno modulu `wsgi.py` nie meno súboru (ma trochu domotalo)
- DBPASS a SECRET_KEY env.variables majú zaškrtnuté Encrypt
- Zvolená najlacnejšia varianta ($5/mesiac)