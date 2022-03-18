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

    return HttpResponse(
        json.dumps({"patches": aggregate(sql_query_all("""
            WITH my_patches AS
            (
                SELECT 
                name as patch_version, 
                EXTRACT(EPOCH FROM release_date)::integer as patch_start_date, 
                LEAD(EXTRACT(EPOCH FROM release_date)::integer, 1) OVER (ORDER BY name) as patch_end_date
                FROM patches
                ORDER BY patch_version ASC
            )
            SELECT my_patches.*, matches.id as match_id, round(matches.duration::decimal / 100, 2) as duration
            FROM my_patches LEFT OUTER JOIN matches ON (matches.start_time >= my_patches.patch_start_date AND matches.start_time <= my_patches.patch_end_date);
            """), key="patch_version", new_group="matches", will_group=["match_id", "duration"]) }), content_type="application/json; charset=utf-8", status=200)

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
        return HttpResponse(
            json.dumps({
            # **sql_query_one("SELECT VERSION()")
            "id": player_id # todo: kontrola existencie => status code
                }), content_type="application/json; charset=utf-8", status=200)

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
    return HttpResponse(
        json.dumps({
            # **sql_query_one("SELECT VERSION()")
            "id": player_id
            }), content_type="application/json; charset=utf-8", status=200)

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
    return HttpResponse(
        json.dumps({
            # **sql_query_one("SELECT VERSION()")
            "id": player_id
            }), content_type="application/json; charset=utf-8", status=200)