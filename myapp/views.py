from django.http import HttpResponse

from myapp.models import GameObjectives, MatchesPlayersDetails, Patches, Matches
from myapp.orm import datetime_unix
from myapp.raw import sql_query_all, sql_query_one, aggregate, constrained_max, rename_keys # priama SQL podpora

import datetime
import time
import simplejson as json

# Create your views here.
def index(request):
    return HttpResponse("""
        <h1>Hello FIIT!</h1>
        <h2>Content</h2>
        <nav>
            <a href=\"/v1/health/\">/v1/health/</a><br>
            <br>
            <a href=\"/v2/patches/\">/v2/patches/</a><br>
            <a href=\"/v2/players/14944/game_exp/\">/v2/players/14944/game_exp/</a><br>
            <a href=\"/v2/players/14944/game_objectives/\">/v2/players/14944/game_objectives/</a><br>
            <a href=\"/v2/players/14944/abilities/\">/v2/players/14944/abilities/</a><br>
            <br>
            <a href=\"/v3/matches/21421/top_purchases/\">/v3/matches/21421/top_purchases/</a><br>
            <a href=\"/v3/abilities/5004/usage/\">/v3/abilities/5004/usage/</a><br>
            <a href=\"/v3/statistics/tower_kills/\">/v3/statistics/tower_kills/</a><br>
            <br>
            <a href=\"/v4/patches/\">/v4/patches/</a><br>
            <a href=\"/v4/players/14944/game_exp/\">/v4/players/14944/game_exp/</a><br>
            <a href=\"/v4/players/14944/game_objectives/\">/v4/players/14944/game_objectives/</a><br>
            <a href=\"/v4/players/14944/abilities/\">/v4/players/14944/abilities/</a><br>
            <a href=\"/v4/matches/21421/top_purchases/\">/v4/matches/21421/top_purchases/</a><br>
            <a href=\"/v4/abilities/5004/usage/\">/v4/abilities/5004/usage/</a><br>
            <a href=\"/v4/statistics/tower_kills/\">/v4/statistics/tower_kills/</a><br>
        </nav>
        <h2>Relevant stuff</h2>
        <nav>
            <a href=\"https://github.com/FIIT-DBS/zadanie-stv8-binder-iairu\">github repo</a><br>
            <a href=\"https://iairu.com\">iairu.com</a>
        </nav>
    """)

def v1_health(request):
    # content_type a pod.: https://docs.djangoproject.com/en/4.0/ref/request-response/#id4
    # django ma namiesto HttpResponse aj JsonResponse, ale mam pocit ze pointa bola precvicit si manualne MIME type nastavenie
    try:
        data = sql_query_one("""
            SELECT VERSION() as version,
            pg_database_size('dota2')/1024/1024 as dota2_db_size;
        """)
        return HttpResponse(json.dumps({"pgsql": data}), content_type="application/json; charset=utf-8", status=200)
    except BaseException as err:
        # 500 "error" catch all
        return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v2_patches(request):
    # {
    #   "patches": [
    #     {
    #       "patch_version": "6.71",
    #       "patch_start_date": 1446681600,
    #       "patch_end_date": 1446768000,
    #       "matches": [
    #         {
    #           "match_id": 0,
    #           "duration": 39.58
    #         }
    #       ]
    #     }
    #   ]
    # }
    try:
        # SQL + agregacie do noveho zoskupenia "matches"
        data = aggregate(sql_query_all("""

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

        """), key="patch_version", new_group="matches", will_group=["match_id", "duration"])
        return HttpResponse(json.dumps({"patches": data }), content_type="application/json; charset=utf-8", status=200)
    except BaseException as err:
        # 500 "error" catch all
        return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v2_players_game_exp(request, player_id):
    # {
    #   "id": 14944,
    #   "player_nick": "kakao`",
    #   "matches": [
    #     {
    #       "match_id": 30221,
    #       "hero_localized_name": "Dark Seer",
    #       "match_duration_minutes": 52.93,
    #       "experiences_gained": 25844,
    #       "level_gained": 22,
    #       "winner": true
    #     }
    #   ]
    # }
    try:
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_player_id = int(player_id)
        # SQL + agregacie do noveho zoskupenia "matches"
        data = aggregate(sql_query_all("""

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

        """), key="id", new_group="matches", will_group=["match_id", "hero_localized_name", "match_duration_minutes",
        "experiences_gained", "level_gained", "winner"])
        # Vybratie prveho vysledku agregacie (v tomto pripade moze byt jedine 1 alebo ziadne kedze cely query sa tyka len 1 hraca) alebo zaznacenie neexistencie
        data = data[0] if len(data) else None
        # 404 "error" ak ziadne data napr. nenajdene player_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid player_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v2_players_game_objectives(request, player_id):
    # {
    #   "id": 14944,
    #   "player_nick": "kakao`",
    #   "matches": [
    #     {
    #       "match_id": 17730,
    #       "hero_localized_name": "Slardar",
    #       "actions": [
    #         {
    #           "hero_action": "CHAT_MESSAGE_TOWER_KILL",
    #           "count": 1
    #         }
    #       ]
    #     }
    #   ]
    # }
    try:
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_player_id = int(player_id)
        # SQL + agregacie do noveho zoskupenia "matches" (vratane obsahu buducich sub-agregacii)
        data = aggregate(sql_query_all("""

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

        """), key="id", new_group="matches", will_group=["match_id", "hero_localized_name", "hero_action", "count"])
        # Vybratie prveho vysledku agregacie (v tomto pripade moze byt jedine 1 alebo ziadne kedze cely query sa tyka len 1 hraca) alebo zaznacenie neexistencie
        data = data[0] if len(data) else None
        # Dalsie agregacie v ramci matches do noveho zoskupenia "actions"
        if (data): data["matches"] = aggregate(data["matches"], key="match_id", new_group="actions", will_group=["hero_action", "count"])
        # 404 "error" ak ziadne data napr. nenajdene player_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid player_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v2_players_abilities(request, player_id):
    # {
    #   "id": 14944,
    #   "player_nick": "kakao`",
    #   "matches": [
    #     {
    #       "match_id": 2980,
    #       "hero_localized_name": "Slardar",
    #       "abilities": [
    #         {
    #           "ability_name": "slardar_slithereen_crush",
    #           "count": 1,
    #           "upgrade_level": 7
    #         }
    #       ]
    #     }
    #   ]
    # }
    try: 
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_player_id = int(player_id)
        # SQL + agregacie do noveho zoskupenia "matches" (vratane obsahu buducich sub-agregacii)
        data = aggregate(sql_query_all("""

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

        """), key="id", new_group="matches", will_group=["match_id", "hero_localized_name", "ability_name", "count", "upgrade_level"])
        # Vybratie prveho vysledku agregacie (v tomto pripade moze byt jedine 1 alebo ziadne kedze cely query sa tyka len 1 hraca) alebo zaznacenie neexistencie
        data = data[0] if len(data) else None
        # Dalsie agregacie v ramci matches do noveho zoskupenia "abilities"
        if (data): data["matches"] = aggregate(data["matches"], key="match_id", new_group="abilities", will_group=["ability_name", "count", "upgrade_level"])
        # 404 "error" ak ziadne data napr. nenajdene player_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid player_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v3_matches_top_purchases(request, match_id):
    # 2,5b
    # Pre vybranú hru identifikovanú v URL ako {match_id} a v nej
    # víťazný tím, vytvorte pre každého hrdinu zoznam piatich
    # najčastejšie nakúpených predmetov. Výsledky zoraďte podľa id
    # hrdinu vzostupne a podľa počtu jeho nákupov daného predmetu
    # zostupne. Sekundárne zoradenie je podľa item_name zostupne.
    # {
    #   "id": 21421,
    #   "heroes": [
    #     {
    #       "id": 18,
    #       "name": "Sven",
    #       "top_purchases": [
    #         {
    #           "id": 46,
    #           "name": "tpscroll",
    #           "count": 25
    #         }
    #       ]
    #     }
    #   ]
    #   }
    try: 
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_match_id = int(match_id)
        # SQL
        data = sql_query_all("""

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
            AND ((m.radiant_win AND player_slot >= 0 AND player_slot <= 4) OR (player_slot >= 128 AND player_slot <= 132)) 
            GROUP BY mpd.hero_id, h.localized_name, pl.item_id, i.name 
            ORDER BY id ASC, item_count DESC, item_name DESC

            ) as x WHERE row <= 5;

        """)

        if (data): data = aggregate(data, "name", "top_purchases", ["item_id", "item_name", "item_count"])
        if (data): data = rename_keys(data, ["item_id", "item_name", "item_count"], ["id", "name", "count"])
        if (data): data = {"id": secure_match_id, "heroes": data}
        # 404 "error" ak ziadne data napr. nenajdene ability_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid match_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v3_abilities_usage(request, ability_id):
    # 3,5b
    # Pre vybranú schopnosť identifikovanú v URL ako {ability_id},
    # (abilities.id) porovnajte v ktorej časti hry si ju víťazní a
    # porazení hráči najčastejšie vybrali. Rozdeľte hru
    # (matches.duration) na percentuálne rozsahy podľa času - 0-9,
    # 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80-89, 90-99,
    # 100-109 a do nich zatrieďte všetky vybraté schopností podľa času
    # ich vybratia (ability_upgrades.time) a podľa hrdinu. Vo výsledku
    # teda budete vedieť, pre ktorého hrdinu je v ktorej percentuálnej
    # časti hry spraviť dané vylepšenie schopnosti ak bol víťaz aj keď
    # bol porazený. Výsledky zoraďte podľa id hrdinu vzostupne.
    # { 
    #   "id": 5004,
    #   "name": "antimage_blink",
    #   "heroes": [
    #     {
    #       "id": 1,
    #       "name": "Anti-Mage",
    #       "usage_winners": {
    #         "bucket": "20-29",
    #         "count": 3373
    #       },
    #       "usage_loosers": {
    #         "bucket": "10-19",
    #         "count": 3272
    #       }
    #     }
    #   ]
    #   }
    try: 
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_ability_id = int(ability_id)
        # SQL
        data = sql_query_all("""

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

        """)

        # v prvom rade sa vytiahne ability_id a ability_name nad zvysnymi hodnotami, ktore budu odteraz v heroes
        # funkciu agregacie som navrhol pre komplexnejsie ucely (napr. rozne ability_id), ktore tu niesu, takze sa
        # nasledne vytiahne len data[0] lebo je len jeden ability_id v celom query
        data = aggregate(data, "ability_id", "heroes", ["hero_id", "hero_name", "winner", "bucket", "count"])
        data = data[0] if len(data) else None
        # nasledne pre heroes sa najde maximum podla rozdielnych hodnot winner
        if (data): data["heroes"] = constrained_max(data["heroes"], "hero_id", "winner", "count", ["hero_name"])
        # rekurzivne premenovanie klucov, pretoze maju byt na roznych urovniach rovnake, co sa pred agregaciou neda
        if (data): data = rename_keys(data, ["ability_id", "ability_name", "hero_id", "hero_name", "true", "false"], ["id", "name", "id", "name", "usage_winners", "usage_loosers"])
        # 404 "error" ak ziadne data napr. nenajdene ability_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid ability_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v3_statistics_tower_kills(request):
    # 4,5b
    # Vytvorte zoznam hrdinov (heroes.localized_name) a každému
    # priraďte sumu reprezentujúcu počet zabití veží
    # (game_objectives.subtype = 'CHAT_MESSAGE_TOWER_KILL') za sebou
    # (v sekvencii) v jednej hre jedným hrdinom. Pod "za sebou" sa
    # myslí zoradenie zabitia veží pre danú hru hrdinom v čase od
    # začiatku po koniec hry. Ak hrdina v hre zabije prvú, druhú a
    # tretiu vežu v poradí a iný hrdina zabije štvrtú vežu v poradí,
    # tak suma pre danú sekvenciu zabitia veží prvého hrdinu je 3. V
    # jednej hre však môže mať jeden hrdina viac takýchto sekvencií.
    # Vaša query má teda vybrať pre všetky zápasy a všetkých hrdinov
    # najdlhšiu sekvenciu zabitia veží daným hrdinom v poradí a
    # zobraziť najdlhšiu sekvenciu pre každého hrdinu (hrdina je
    # výstupe len raz). Zoznam hrdinov zoraďte podľa počtu zabití v
    # sekvencii od najväčšieho po najmenší. V prípade, že veža je
    # zabitá NPC postavami match_player_detail_id1 = null a tiež
    # match_player_detail_id2 = null, tak takéto záznamy ignorujte pre
    # výpočet sekvencie.
    # {
    #   "heroes": [
    #     {
    #       "id": 18,
    #       "name": "Sven",
    #       "tower_kills": 11
    #     }
    #   ]
    #   }
    try:
        # SQL
        data = sql_query_all("""

            -- priradenie hero_id pre jednotlive mpd_id
            -- rozdelenie mpd_id1 a mpd_id2 do separatnych riadkov cez UNION ALL pricom NOT(IS NULL AND IS NULL) => IS NOT NULL OR IS NOT NULL => vyhodenie NULL parov
            -- \_ i ked tu nevidim zmysel pri CHAT_MESSAGE_TOWER_KILL lebo mpd_id2 je vzdy null, tak to dava zmysel pre viac vseobecne riesenie 
            -- zoradenie podla id znamena zoradenie v case hry (kedze pocas hry sa postupne pridavali do tabulky hodnoty neskor = vyssie id), co potvrdzuje aj odvodena zoradenost match_id
            -- rozdelenie id v danom case do particii podla match_id vdaka ROW_NUMBER PARTITION
            -- vnorene selecty a viacero PARTITION pre match_heroid_sequence lokalne pocitany (a nie pre cely match) trikom odcitania, lebo jeden PARTITION je tohto zjavne neschopny

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

        """)

        # data = aggregate(data, "ability_id", "heroes", ["hero_id", "hero_name", "winner", "bucket", "count"])
        # 404 "error" ak ziadne data napr. nenajdene ability_id, inac 200
        return HttpResponse(json.dumps({"heroes": data} if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v4_patches(request):
    # {
    #   "patches": [
    #     {
    #       "patch_version": "6.71",
    #       "patch_start_date": 1446681600,
    #       "patch_end_date": 1446768000,
    #       "matches": [
    #         {
    #           "match_id": 0,
    #           "duration": 39.58
    #         }
    #       ]
    #     }
    #   ]
    # }

    try:
        # original SQL:
        # WITH my_patches AS
        # (
        #     SELECT name                                     as patch_version, 
        #         EXTRACT(EPOCH FROM release_date)::integer  as patch_start_date, 
        #     LEAD(EXTRACT(EPOCH FROM release_date)::integer, 1) OVER (ORDER BY name)      
        #                                                     as patch_end_date
        #     FROM patches
        #     ORDER BY patch_version ASC
        # )
        # SELECT my_patches.*, 
        # matches.id                                          as match_id, 
        # ROUND(matches.duration::decimal / 60, 2)            as duration
        # FROM my_patches 
        # LEFT OUTER JOIN matches ON (matches.start_time >= my_patches.patch_start_date AND 
        #                             matches.start_time <= COALESCE(my_patches.patch_end_date,
        #                             EXTRACT(EPOCH FROM NOW())::integer));

        # ORM
        patches = []
        _patches_ = Patches.objects.all().order_by("name")
        _matches_ = Matches.objects.all()
        _patches_len = len(_patches_)
        for i, _patch_ in enumerate(_patches_):
            patch = {}
            patch["patch_version"] = _patch_.name
            patch["patch_start_date"] = int(datetime_unix(_patch_.release_date))
            patch["patch_end_date"] = None if (i >= _patches_len - 1) else int(datetime_unix(_patches_[i + 1].release_date))
            matches = []
            for j, _match_ in enumerate(_matches_):
                match_start_time = int(_match_.start_time)
                if (match_start_time >= patch["patch_start_date"] and (patch["patch_end_date"] == None or match_start_time <= patch["patch_end_date"])):
                    match = {}
                    match["match_id"] = _match_.id
                    match["duration"] = round(_match_.duration / 60, 2)
                    matches.append(match)
            patch["matches"] = matches
            patches.append(patch)

        data = {"patches": patches}

        return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8", status=200)
    except BaseException as err:
        # 500 "error" catch all
        return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v4_players_game_exp(request, player_id):
    # {
    #   "id": 14944,
    #   "player_nick": "kakao`",
    #   "matches": [
    #     {
    #       "match_id": 30221,
    #       "hero_localized_name": "Dark Seer",
    #       "match_duration_minutes": 52.93,
    #       "experiences_gained": 25844,
    #       "level_gained": 22,
    #       "winner": true
    #     }
    #   ]
    # }
    try:
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_player_id = int(player_id)

        # original SQL:
        # SELECT players.id                             as id, 
        # COALESCE(players.nick, 'unknown')             as player_nick, 
        # matches.id                                    as match_id,
        # heroes.localized_name                         as hero_localized_name, 
        # ROUND(matches.duration::decimal / 60, 2)      as match_duration_minutes, 
        # (COALESCE(mpd.xp_hero,0) + 
        # COALESCE(mpd.xp_creep,0) + 
        # COALESCE(mpd.xp_other,0) + 
        # COALESCE(mpd.xp_roshan,0))                   as experiences_gained, 
        # mpd.level                                     as level_gained,
        # CASE WHEN     matches.radiant_win AND mpd.player_slot >= 0   AND mpd.player_slot <= 4   THEN true
        #     WHEN not matches.radiant_win AND mpd.player_slot >= 128 AND mpd.player_slot <= 132 THEN true
        #     ELSE false
        # END                                           as winner
        # FROM matches_players_details as mpd
        # INNER JOIN heroes ON (mpd.hero_id = heroes.id) 
        # INNER JOIN matches ON (mpd.match_id = matches.id) 
        # INNER JOIN players ON (mpd.player_id = players.id)
        # WHERE player_id = """ + str(secure_player_id) + """ 
        # ORDER BY matches.id ASC;

        # ORM
        matches = []
        _player_ = None
        _mpds_ = MatchesPlayersDetails.objects.filter(player_id=secure_player_id).order_by("match_id").select_related()
        for _mpd_ in _mpds_:
            _match_ = _mpd_.match
            if (_player_ == None): _player_ = _mpd_.player
            _hero_ = _mpd_.hero
            match = {}
            match["match_id"] = _match_.id
            match["hero_localized_name"] = _hero_.localized_name
            match["match_duration_minutes"] = round(_match_.duration / 60, 2)
            match["experiences_gained"] = int(0 if (_mpd_.xp_hero == None) else _mpd_.xp_hero) + \
                                          int(0 if (_mpd_.xp_creep == None) else _mpd_.xp_creep) + \
                                          int(0 if (_mpd_.xp_other == None) else _mpd_.xp_other) + \
                                          int(0 if (_mpd_.xp_roshan == None) else _mpd_.xp_roshan)
            match["level_gained"] = _mpd_.level
            match["winner"] = True if ( (_match_.radiant_win and _mpd_.player_slot >= 0 and _mpd_.player_slot <= 4) or \
                                        (not _match_.radiant_win and _mpd_.player_slot >= 128 and _mpd_.player_slot <= 132)) \
                                        else False
            matches.append(match)

        data = {}
        data["id"] = _player_.id
        data["player_nick"] = "unknown" if (_player_.nick == None) else _player_.nick
        data["matches"] = matches

        # Vybratie prveho vysledku agregacie (v tomto pripade moze byt jedine 1 alebo ziadne kedze cely query sa tyka len 1 hraca) alebo zaznacenie neexistencie
        # data = data[0] if len(data) else None
        # 404 "error" ak ziadne data napr. nenajdene player_id, inac 200
        return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid player_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

def v4_players_game_objectives(request, player_id):
    # {
    #   "id": 14944,
    #   "player_nick": "kakao`",
    #   "matches": [
    #     {
    #       "match_id": 17730,
    #       "hero_localized_name": "Slardar",
    #       "actions": [
    #         {
    #           "hero_action": "CHAT_MESSAGE_TOWER_KILL",
    #           "count": 1
    #         }
    #       ]
    #     }
    #   ]
    # }
    try:
        # zabezpecenie vstupu od pouzivatela pred SQL: povolene len ciselne znaky
        secure_player_id = int(player_id)

        # original SQL:
        # SELECT players.id                          as id, 
        # COALESCE(players.nick,'unknown')           as player_nick, 
        # matches.id                                 as match_id, 
        # heroes.localized_name                      as hero_localized_name, 
        # COALESCE(gobj.subtype, 'NO_ACTION')        as hero_action,
        # COUNT(COALESCE(gobj.subtype, 'NO_ACTION')) as count
        # FROM matches_players_details as mpd 
        # INNER JOIN heroes ON (mpd.hero_id = heroes.id) 
        # INNER JOIN matches ON (mpd.match_id = matches.id) 
        # INNER JOIN players ON (mpd.player_id = players.id) 
        # FULL OUTER JOIN game_objectives as gobj ON (mpd.id = gobj.match_player_detail_id_1)
        # WHERE player_id = """ + str(secure_player_id) + """ 
        # GROUP BY players.id, player_nick, matches.id, heroes.localized_name, hero_action;

        # ORM
        matches = []
        _player_ = None
        _mpds_ = MatchesPlayersDetails.objects.filter(player_id=secure_player_id).order_by("match_id").select_related()
        
        # _gobjs_ = GameObjectives.objects # nefunguje
        # for _mpd_ in _mpds_:
        #     _gobjs_ = _gobjs_.filter(match_player_detail_id_1=_mpd_.id)
        # _gobjs_.all()

        for _mpd_ in _mpds_:
            _match_ = _mpd_.match
            if (_player_ == None): _player_ = _mpd_.player
            _hero_ = _mpd_.hero
            match = {}
            match["match_id"] = _match_.id
            match["hero_localized_name"] = _hero_.localized_name
            actions = []
            i = 0
            _gobjs_ = GameObjectives.objects.filter(match_player_detail_id_1=_mpd_.id).order_by("subtype").all()
            for _gobj_ in _gobjs_:
                action = {}
                action["hero_action"] = "NO_ACTION" if (_gobj_.subtype == None) else _gobj_.subtype
                if (i > 0 and actions[i - 1]["hero_action"] == action["hero_action"]):
                    actions[i - 1]["count"] += 1
                else:
                    action["count"] = 1
                    actions.append(action)
                    i += 1
            if (len(actions) == 0):
                action = {}
                action["hero_action"] = "NO_ACTION"
                action["count"] = 1
                actions.append(action)
            match["actions"] = actions
            matches.append(match)

        data = {}
        data["id"] = _player_.id
        data["player_nick"] = "unknown" if (_player_.nick == None) else _player_.nick
        data["matches"] = matches

        # 404 "error" ak ziadne data napr. nenajdene player_id, inac 200
        return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid player_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error"}), content_type="application/json; charset=utf-8", status=500) # internal error

