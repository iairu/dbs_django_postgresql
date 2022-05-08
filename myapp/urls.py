from django.urls import path

from myapp import views

urlpatterns = [
    path('', views.index),
    path('v1/health/', views.v1_health),
    path('v2/patches/', views.v2_patches),
    path('v2/players/<player_id>/game_exp/', views.v2_players_game_exp),
    path('v2/players/<player_id>/game_objectives/', views.v2_players_game_objectives),
    path('v2/players/<player_id>/abilities/', views.v2_players_abilities),
    path('v3/matches/<match_id>/top_purchases/', views.v3_matches_top_purchases),
    path('v3/abilities/<ability_id>/usage/', views.v3_abilities_usage),
    path('v3/statistics/tower_kills/', views.v3_statistics_tower_kills),
    path('v4/patches/', views.v4_patches),
    path('v4/players/<player_id>/game_exp/', views.v4_players_game_exp),
]