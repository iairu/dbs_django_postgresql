# Pouzity prikaz: python manage.py inspectdb --database readonly > models.py
# Nasledne skontrolovane priradenie id ako primary_key pre kazdy model
# ForeignKey on_delete neriesene lebo ORM bude len pre SELECT (read only)
from django.db import models


class Abilities(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'abilities'


class AbilityUpgrades(models.Model):
    id = models.IntegerField(primary_key=True)
    ability = models.ForeignKey(Abilities, models.DO_NOTHING, blank=True, null=True)
    match_player_detail = models.ForeignKey('MatchesPlayersDetails', models.DO_NOTHING, blank=True, null=True)
    level = models.IntegerField(blank=True, null=True)
    time = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'ability_upgrades'


# class Chats(models.Model):
#     id = models.IntegerField(primary_key=True)
#     match_player_detail = models.ForeignKey('MatchesPlayersDetails', models.DO_NOTHING, blank=True, null=True)
#     message = models.TextField(blank=True, null=True)
#     time = models.IntegerField(blank=True, null=True)
#     nick = models.TextField(blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'chats'


class ClusterRegions(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'cluster_regions'


class GameObjectives(models.Model):
    id = models.IntegerField(primary_key=True)
    match_player_detail_id_1 = models.ForeignKey('MatchesPlayersDetails', models.DO_NOTHING, db_column='match_player_detail_id_1', related_name='match_player_detail_id_1', blank=True, null=True)
    match_player_detail_id_2 = models.ForeignKey('MatchesPlayersDetails', models.DO_NOTHING, db_column='match_player_detail_id_2', related_name='match_player_detail_id_2', blank=True, null=True)
    key = models.IntegerField(blank=True, null=True)
    subtype = models.TextField(blank=True, null=True)
    team = models.IntegerField(blank=True, null=True)
    time = models.IntegerField(blank=True, null=True)
    value = models.IntegerField(blank=True, null=True)
    slot = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'game_objectives'


class Heroes(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    localized_name = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'heroes'


class Items(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'items'

class Players(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    nick = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'players'


class Matches(models.Model):
    id = models.IntegerField(primary_key=True)
    cluster_region = models.ForeignKey(ClusterRegions, models.DO_NOTHING, blank=True, null=True)
    start_time = models.IntegerField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    tower_status_radiant = models.IntegerField(blank=True, null=True)
    tower_status_dire = models.IntegerField(blank=True, null=True)
    barracks_status_radiant = models.IntegerField(blank=True, null=True)
    barracks_status_dire = models.IntegerField(blank=True, null=True)
    first_blood_time = models.IntegerField(blank=True, null=True)
    game_mode = models.IntegerField(blank=True, null=True)
    radiant_win = models.BooleanField(blank=True, null=True)
    negative_votes = models.IntegerField(blank=True, null=True)
    positive_votes = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'matches'


class MatchesPlayersDetails(models.Model):
    id = models.IntegerField(primary_key=True)
    match = models.ForeignKey(Matches, models.DO_NOTHING, blank=True, null=True)
    player = models.ForeignKey(Players, models.DO_NOTHING, blank=True, null=True)
    hero = models.ForeignKey(Heroes, models.DO_NOTHING, blank=True, null=True)
    player_slot = models.IntegerField(blank=True, null=True)
    gold = models.IntegerField(blank=True, null=True)
    gold_spent = models.IntegerField(blank=True, null=True)
    gold_per_min = models.IntegerField(blank=True, null=True)
    xp_per_min = models.IntegerField(blank=True, null=True)
    kills = models.IntegerField(blank=True, null=True)
    deaths = models.IntegerField(blank=True, null=True)
    assists = models.IntegerField(blank=True, null=True)
    denies = models.IntegerField(blank=True, null=True)
    last_hits = models.IntegerField(blank=True, null=True)
    stuns = models.IntegerField(blank=True, null=True)
    hero_damage = models.IntegerField(blank=True, null=True)
    hero_healing = models.IntegerField(blank=True, null=True)
    tower_damage = models.IntegerField(blank=True, null=True)
    item_id_1 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_1', db_column='item_id_1', blank=True, null=True)
    item_id_2 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_2', db_column='item_id_2', blank=True, null=True)
    item_id_3 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_3', db_column='item_id_3', blank=True, null=True)
    item_id_4 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_4', db_column='item_id_4', blank=True, null=True)
    item_id_5 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_5', db_column='item_id_5', blank=True, null=True)
    item_id_6 = models.ForeignKey(Items, models.DO_NOTHING, related_name='item_id_6', db_column='item_id_6', blank=True, null=True)
    level = models.IntegerField(blank=True, null=True)
    leaver_status = models.IntegerField(blank=True, null=True)
    xp_hero = models.IntegerField(blank=True, null=True)
    xp_creep = models.IntegerField(blank=True, null=True)
    xp_roshan = models.IntegerField(blank=True, null=True)
    xp_other = models.IntegerField(blank=True, null=True)
    gold_other = models.IntegerField(blank=True, null=True)
    gold_death = models.IntegerField(blank=True, null=True)
    gold_buyback = models.IntegerField(blank=True, null=True)
    gold_abandon = models.IntegerField(blank=True, null=True)
    gold_sell = models.IntegerField(blank=True, null=True)
    gold_destroying_structure = models.IntegerField(blank=True, null=True)
    gold_killing_heroes = models.IntegerField(blank=True, null=True)
    gold_killing_creeps = models.IntegerField(blank=True, null=True)
    gold_killing_roshan = models.IntegerField(blank=True, null=True)
    gold_killing_couriers = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'matches_players_details'


class Patches(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField()
    release_date = models.DateTimeField()

    class Meta:
        managed = False # Remove if you wish to allow Django to create, modify, and delete the table
        db_table = 'patches'


# class PlayerActions(models.Model):
#     id = models.IntegerField(primary_key=True)
#     unit_order_none = models.IntegerField(blank=True, null=True)
#     unit_order_move_to_position = models.IntegerField(blank=True, null=True)
#     unit_order_move_to_target = models.IntegerField(blank=True, null=True)
#     unit_order_attack_move = models.IntegerField(blank=True, null=True)
#     unit_order_attack_target = models.IntegerField(blank=True, null=True)
#     unit_order_cast_position = models.IntegerField(blank=True, null=True)
#     unit_order_cast_target = models.IntegerField(blank=True, null=True)
#     unit_order_cast_target_tree = models.IntegerField(blank=True, null=True)
#     unit_order_cast_no_target = models.IntegerField(blank=True, null=True)
#     unit_order_cast_toggle = models.IntegerField(blank=True, null=True)
#     unit_order_hold_position = models.IntegerField(blank=True, null=True)
#     unit_order_train_ability = models.IntegerField(blank=True, null=True)
#     unit_order_drop_item = models.IntegerField(blank=True, null=True)
#     unit_order_give_item = models.IntegerField(blank=True, null=True)
#     unit_order_pickup_item = models.IntegerField(blank=True, null=True)
#     unit_order_pickup_rune = models.IntegerField(blank=True, null=True)
#     unit_order_purchase_item = models.IntegerField(blank=True, null=True)
#     unit_order_sell_item = models.IntegerField(blank=True, null=True)
#     unit_order_disassemble_item = models.IntegerField(blank=True, null=True)
#     unit_order_move_item = models.IntegerField(blank=True, null=True)
#     unit_order_cast_toggle_auto = models.IntegerField(blank=True, null=True)
#     unit_order_stop = models.IntegerField(blank=True, null=True)
#     unit_order_buyback = models.IntegerField(blank=True, null=True)
#     unit_order_glyph = models.IntegerField(blank=True, null=True)
#     unit_order_eject_item_from_stash = models.IntegerField(blank=True, null=True)
#     unit_order_cast_rune = models.IntegerField(blank=True, null=True)
#     unit_order_ping_ability = models.IntegerField(blank=True, null=True)
#     unit_order_move_to_direction = models.IntegerField(blank=True, null=True)
#     match_player_detail = models.ForeignKey(MatchesPlayersDetails, models.DO_NOTHING, blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'player_actions'


# class PlayerRatings(models.Model):
#     id = models.IntegerField(primary_key=True)
#     player = models.ForeignKey('Players', models.DO_NOTHING, blank=True, null=True)
#     total_wins = models.IntegerField(blank=True, null=True)
#     total_matches = models.IntegerField(blank=True, null=True)
#     trueskill_mu = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
#     trueskill_sigma = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'player_ratings'


# class PlayerTimes(models.Model):
#     id = models.IntegerField(primary_key=True)
#     match_player_detail = models.ForeignKey(MatchesPlayersDetails, models.DO_NOTHING, blank=True, null=True)
#     time = models.IntegerField(blank=True, null=True)
#     gold = models.IntegerField(blank=True, null=True)
#     lh = models.IntegerField(blank=True, null=True)
#     xp = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'player_times'


# class PurchaseLogs(models.Model):
#     id = models.IntegerField(primary_key=True)
#     match_player_detail = models.ForeignKey(MatchesPlayersDetails, models.DO_NOTHING, blank=True, null=True)
#     item = models.ForeignKey(Items, models.DO_NOTHING, blank=True, null=True)
#     time = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'purchase_logs'


# class Teamfights(models.Model):
#     id = models.IntegerField(primary_key=True)
#     match = models.ForeignKey(Matches, models.DO_NOTHING, blank=True, null=True)
#     start_teamfight = models.IntegerField(blank=True, null=True)
#     end_teamfight = models.IntegerField(blank=True, null=True)
#     last_death = models.IntegerField(blank=True, null=True)
#     deaths = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'teamfights'


# class TeamfightsPlayers(models.Model):
#     id = models.IntegerField(primary_key=True)
#     teamfight = models.ForeignKey(Teamfights, models.DO_NOTHING, blank=True, null=True)
#     match_player_detail = models.ForeignKey(MatchesPlayersDetails, models.DO_NOTHING, blank=True, null=True)
#     buyback = models.IntegerField(blank=True, null=True)
#     damage = models.IntegerField(blank=True, null=True)
#     deaths = models.IntegerField(blank=True, null=True)
#     gold_delta = models.IntegerField(blank=True, null=True)
#     xp_start = models.IntegerField(blank=True, null=True)
#     xp_end = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = False # Remove if you wish to allow Django to create, modify, and delete the table
#         db_table = 'teamfights_players'
