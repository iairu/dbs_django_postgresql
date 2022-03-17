from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('v1/health/', views.v1_health),
    path('v2/patches/', views.v2_patches),
    path('v2/players/<player_id>/game_exp/', views.v2_players_game_exp),
    path('v2/players/<player_id>/game_objectives/', views.v2_players_game_objectives),
    path('v2/players/<player_id>/abilities/', views.v2_players_abilities)
]