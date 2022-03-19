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