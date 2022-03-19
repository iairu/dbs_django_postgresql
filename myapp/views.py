from django.shortcuts import render
from django.http import HttpResponse

from .models import sql_query_all, sql_query_one, aggregate # priama SQL podpora
import simplejson as json

# Create your views here.
def index(request):
    return HttpResponse("""
        <h1>Hello FIIT!</h1>
        <h2>Content</h2>
        <nav>
            <a href=\"/v1/health/\">/v1/health/</a><br>
            <a href=\"/v2/patches/\">/v2/patches/</a><br>
            <a href=\"/v2/players/14944/game_exp/\">/v2/players/14944/game_exp/</a><br>
            <a href=\"/v2/players/14944/game_objectives/\">/v2/players/14944/game_objectives/</a><br>
            <a href=\"/v2/players/14944/abilities/\">/v2/players/14944/abilities/</a><br>
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
    return HttpResponse(
        json.dumps({"pgsql":{ # spojenie dvoch dict do jedneho cez unpack operator **
            **sql_query_one("SELECT VERSION()"), 
            **sql_query_one("SELECT pg_database_size('dota2')/1024/1024 as dota2_db_size")
            }}), content_type="application/json; charset=utf-8", status=200)

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
            SELECT name 																as patch_version, 
                 EXTRACT(EPOCH FROM release_date)::integer 								as patch_start_date, 
            LEAD(EXTRACT(EPOCH FROM release_date)::integer, 1) OVER (ORDER BY name)  	as patch_end_date
            FROM patches
            ORDER BY patch_version ASC
        )
        SELECT my_patches.*, 
        matches.id 																		as match_id, 
        ROUND(matches.duration::decimal / 60, 2) 										as duration
        FROM my_patches 
        LEFT OUTER JOIN matches ON (matches.start_time >= my_patches.patch_start_date AND 
                                    matches.start_time <= COALESCE(my_patches.patch_end_date, EXTRACT(EPOCH FROM NOW())::integer));

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

            SELECT players.id 							as id, 
            COALESCE(players.nick, 'unknown') 			as player_nick, 
            matches.id 									as match_id,
            heroes.localized_name 						as hero_localized_name, 
            ROUND(matches.duration::decimal / 60, 2)	as match_duration_minutes, 
            (COALESCE(mpd.xp_hero,0) + 
             COALESCE(mpd.xp_creep,0) + 
             COALESCE(mpd.xp_other,0) + 
             COALESCE(mpd.xp_roshan,0)) 				as experiences_gained, 
            mpd.level									as level_gained,
            CASE WHEN     matches.radiant_win AND mpd.player_slot >= 0   AND mpd.player_slot <= 4   THEN true
                 WHEN not matches.radiant_win AND mpd.player_slot >= 128 AND mpd.player_slot <= 132 THEN true
                 ELSE false
            END 										as winner
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

            SELECT players.id               	       as id, 
            COALESCE(players.nick,'unknown')           as player_nick, 
            matches.id 							       as match_id, 
            heroes.localized_name           	       as hero_localized_name, 
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

            SELECT players.id 					as id, 
            COALESCE(players.nick,'unknown') 	as player_nick, 
            matches.id 							as match_id, 
            heroes.localized_name 				as hero_localized_name, 
            ab.name 							as ability_name, 
            COUNT(ab.name) 						as count,
            MAX(au.level) 						as upgrade_level 
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