from django.shortcuts import render
from django.http import HttpResponse

from .models import sql_query_all, sql_query_one, aggregate, constrained_max, rename_keys # priama SQL podpora
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
            ORDER BY mpd.hero_id ASC, count(pl.item_id) DESC, i.name ASC) as row

            FROM matches_players_details as mpd 
            INNER JOIN matches as m ON m.id = mpd.match_id
            INNER JOIN heroes as h ON h.id = mpd.hero_id
            INNER JOIN purchase_logs as pl ON mpd.id = pl.match_player_detail_id
            INNER JOIN items as i ON i.id = pl.item_id

            WHERE match_id = """ + str(secure_match_id) + """
            AND ((m.radiant_win AND player_slot >= 0 AND player_slot <= 4) OR (player_slot >= 128 AND player_slot <= 132)) 
            GROUP BY mpd.hero_id, h.localized_name, pl.item_id, i.name 
            ORDER BY id ASC, item_count DESC, item_name ASC

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
            return HttpResponse(json.dumps({"error": "internal error " + str(err)}), content_type="application/json; charset=utf-8", status=500) # internal error


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

            WITH results AS (
                SELECT * 
                FROM (
                    SELECT *, COUNT(bucket) as count,
                    ROW_NUMBER() OVER (PARTITION BY hero_id, winner ORDER BY COUNT(bucket) DESC) as row_n
                    FROM (
                        SELECT 
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
                    ORDER BY hero_id ASC, winner DESC, count DESC
                ) as x WHERE row_n = 1
            )
            
            SELECT ability_id, ability_name, hero_id, hero_name, 
            MAX(win_bucket) as usage_winners_bucket, MAX(win_count) as usage_winners_count, 
            MAX(lose_bucket) as usage_losers_bucket, MAX(lose_count) as usage_losers_count
            FROM (
                SELECT ability_id, ability_name, hero_id, hero_name, 
                bucket as win_bucket, count as win_count, NULL as lose_bucket, NULL as lose_count 
                FROM results WHERE winner IS TRUE
            UNION
                SELECT ability_id, ability_name, hero_id, hero_name, 
                NULL as win_bucket, NULL as win_count, bucket as lose_bucket, count as lose_count
                FROM results WHERE winner IS FALSE
            ) as x GROUP BY ability_id, ability_name, hero_id, hero_name;

        """)

        # usage_winners a usage_loosers agregacia
        data = aggregate(data, "hero_id", "usage_winners", ["usage_winners_bucket", "usage_winners_count"])
        if (data):
            for x in data:
                if (x["usage_winners"]): x["usage_winners"] = x["usage_winners"][0]
        if (data): data = aggregate(data, "hero_id", "usage_loosers", ["usage_losers_bucket", "usage_losers_count"])
        if (data):
            for x in data:
                if (x["usage_loosers"]): x["usage_loosers"] = x["usage_loosers"][0]
        if (data):data = aggregate(data, "ability_id", "heroes", ["hero_id", "hero_name", "usage_winners", "usage_loosers"])
        if (data): data = data[0] if len(data) else None

        if (data): data = rename_keys(data, 
            ["hero_id", "hero_name", "usage_winners_bucket", "usage_winners_count", "usage_losers_bucket", "usage_losers_count"], 
            ["id", "name", "bucket", "count", "bucket", "count"]
            )

        # 404 "error" ak ziadne data napr. nenajdene ability_id, inac 200
        return HttpResponse(json.dumps(data if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        if "invalid literal for int" in str(err):
            return HttpResponse(json.dumps({"error": "invalid ability_id"}), content_type="application/json; charset=utf-8", status=400) # bad request
        else:
            return HttpResponse(json.dumps({"error": "internal error " + str(err)}), content_type="application/json; charset=utf-8", status=500) # internal error


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
            ORDER BY MAX(match_heroid_sequence) DESC, name ASC;

        """)

        # data = aggregate(data, "ability_id", "heroes", ["hero_id", "hero_name", "winner", "bucket", "count"])
        # 404 "error" ak ziadne data napr. nenajdene ability_id, inac 200
        return HttpResponse(json.dumps({"heroes": data} if data else {"error": "no data"}), content_type="application/json; charset=utf-8", status=200 if data else 404)
    except BaseException as err:
        # 400 "error" ak napr. player_id na vstupe obsahuje neciselne znaky + 500 catch all
        return HttpResponse(json.dumps({"error": "internal error " + str(err)}), content_type="application/json; charset=utf-8", status=500) # internal error
