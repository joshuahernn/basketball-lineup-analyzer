from __future__ import annotations

"""Helpers for the lineup summary API."""

from typing import Any

from app.dbmodels.models import Game, Player
from app.dbmodels.models import Possession
from itertools import combinations
from app.helpers.lineup_metrics import add_lineup_metrics
from django.db.models import Q

LineupRecord = dict[str, Any]

STAT_FIELDS = [
    ("points", "points"),
    ("shot_attempts", "shot_attempts"),
    ("fg2_made", "fg2_made"),
    ("fg2_attempted", "fg2_attempted"),
    ("fg3_made", "fg3_made"),
    ("fg3_attempted", "fg3_attempted"),
    ("fg_made", "fg_made"),
    ("fg_attempted", "fg_attempted"),
    ("ft_made", "ft_made"),
    ("ft_attempted", "ft_attempted"),
    ("rebounds_offense", "rebounds_offense"),
    ("rebounds_defense", "rebounds_defense"),
    ("rebound_opportunities", "rebound_opportunities"),
    ("assists", "assists"),
    ("steals", "steals"),
    ("turnovers", "turnovers"),
    ("blocks", "blocks"),
    ("offensive_fouls", "offensive_fouls"),
    ("defensive_fouls", "defensive_fouls"),
    ("shooting_fouls", "shooting_fouls"),
    ("shot_attempt_points", "shot_attempt_points"),
    ("ft_potential_points", "ft_potential_points"),
    ("transition_take_fouls", "transition_take_fouls"),
    ("seconds", "seconds"),
]


def validate_and_key(player_ids, team_id, player_map, lineup_size):
    if not player_ids:
        return []

    for pid in player_ids:
        if pid not in player_map:
            return []

        player_team_id, _ = player_map[pid]

        if player_team_id != team_id:
            return []

    keys = []

    for combo in combinations(player_ids, lineup_size):
        keys.append((team_id, tuple(sorted(combo))))

    return keys


def ensure(
    linemap, key, prefix, field_map
):  # make sure that the lineup has a key, and if it doesn't create one.
    if key in linemap:
        return None

    linemap[key] = {f"{prefix}possessions": 0}

    for raw_field, output_field in field_map:
        linemap[key][f"{prefix}{output_field}"] = 0


def add_stats(entry, possession, prefix, field_map):
    entry[f"{prefix}possessions"] += int(possession.counts_as_possession)
    for raw_field, output_field in field_map:
        entry[f"{prefix}{output_field}"] += getattr(possession, raw_field)


def add_fourth_quarter_stats(
    possession, off_keys, def_keys, q4_offensive_linemap, q4_defensive_linemap
):

    if possession.period != 4:
        return

    # offensive fourth quarter stats
    for off_key in off_keys:
        ensure(
            q4_offensive_linemap, off_key, prefix="q4_offensive_", field_map=STAT_FIELDS
        )
        add_stats(
            q4_offensive_linemap[off_key],
            possession,
            prefix="q4_offensive_",
            field_map=STAT_FIELDS,
        )

    # defensive fourth quarter stats
    for def_key in def_keys:
        ensure(
            q4_defensive_linemap, def_key, prefix="q4_defensive_", field_map=STAT_FIELDS
        )
        add_stats(
            q4_defensive_linemap[def_key],
            possession,
            prefix="q4_defensive_",
            field_map=STAT_FIELDS,
        )


def get_team_game_ids(team_id, dataset="demo"):
    games = (
        Possession.objects.filter(
            Q(offensive_team_id=team_id) | Q(defensive_team_id=team_id),
            game__dataset=dataset,
        )
        .values_list("game_id", flat=True)
        .distinct()
        .order_by("game_id")
    )

    return list(games)


def get_team_summary_stats(team_id, game_id=None, dataset="demo"):
    possessions = Possession.objects.filter(
        Q(offensive_team_id=team_id) | Q(defensive_team_id=team_id),
        game__dataset=dataset,
    )

    if game_id:
        possessions = possessions.filter(game_id=game_id)

    offensive_stats = {}
    defensive_stats = {}
    q4_offensive_stats = {}
    q4_defensive_stats = {}

    for possession in possessions:
        if possession.offensive_team_id == team_id:
            ensure(
                offensive_stats,
                team_id,
                prefix="offensive_",
                field_map=STAT_FIELDS,
            )

            add_stats(
                offensive_stats[team_id],
                possession,
                prefix="offensive_",
                field_map=STAT_FIELDS,
            )

            if possession.period == 4:
                ensure(
                    q4_offensive_stats,
                    team_id,
                    prefix="q4_offensive_",
                    field_map=STAT_FIELDS,
                )

                add_stats(
                    q4_offensive_stats[team_id],
                    possession,
                    prefix="q4_offensive_",
                    field_map=STAT_FIELDS,
                )

        if possession.defensive_team_id == team_id:
            ensure(
                defensive_stats,
                team_id,
                prefix="defensive_",
                field_map=STAT_FIELDS,
            )

            add_stats(
                defensive_stats[team_id],
                possession,
                prefix="defensive_",
                field_map=STAT_FIELDS,
            )

            if possession.period == 4:
                ensure(
                    q4_defensive_stats,
                    team_id,
                    prefix="q4_defensive_",
                    field_map=STAT_FIELDS,
                )

                add_stats(
                    q4_defensive_stats[team_id],
                    possession,
                    prefix="q4_defensive_",
                    field_map=STAT_FIELDS,
                )

    page = {}

    page.update(offensive_stats.get(team_id, {}))
    page.update(defensive_stats.get(team_id, {}))
    page.update(q4_offensive_stats.get(team_id, {}))
    page.update(q4_defensive_stats.get(team_id, {}))

    add_lineup_metrics(page)

    page["team_id"] = team_id
    page["dataset"] = dataset
    matching_games = list(Game.objects.filter(
        id__in=possessions.values_list("game_id", flat=True).distinct(),
    ).order_by("date", "id")[:2])
    if len(matching_games) == 1:
        game_id = matching_games[0].id
        page["game_date"] = matching_games[0].date
        page["source_game_id"] = matching_games[0].source_id

    if game_id:
        first_possession = possessions.first()

        if first_possession:
            if first_possession.offensive_team_id == team_id:
                opponent_team_id = first_possession.defensive_team_id
            else:
                opponent_team_id = first_possession.offensive_team_id

            team_score = page.get("offensive_points", 0)
            opponent_score = page.get("defensive_points", 0)

            page["game_id"] = game_id
            page["opponent_team_id"] = opponent_team_id
            page["team_score"] = team_score
            page["opponent_score"] = opponent_score

    return page


def get_player_impact_stats(dataset="demo"):

    offensive_player_stats = {}
    defensive_player_stats = {}

    player_map = {}

    for player in Player.objects.filter(team__dataset=dataset):
        player_map[player.id] = {
            "name": player.name,
            "team_id": player.team_id,
        }

    possessions = Possession.objects.filter(game__dataset=dataset)

    for possession in possessions:

        offensive_player_ids = possession.offensive_player_ids
        defensive_player_ids = possession.defensive_player_ids

        for player_id in offensive_player_ids:

            if player_id not in player_map:
                continue

            ensure(
                offensive_player_stats,
                player_id,
                prefix="offensive_",
                field_map=STAT_FIELDS,
            )

            add_stats(
                offensive_player_stats[player_id],
                possession,
                prefix="offensive_",
                field_map=STAT_FIELDS,
            )

        for player_id in defensive_player_ids:

            if player_id not in player_map:
                continue

            ensure(
                defensive_player_stats,
                player_id,
                prefix="defensive_",
                field_map=STAT_FIELDS,
            )

            add_stats(
                defensive_player_stats[player_id],
                possession,
                prefix="defensive_",
                field_map=STAT_FIELDS,
            )

    all_player_ids = set(offensive_player_stats) | set(defensive_player_stats)

    results = []

    for player_id in all_player_ids:

        page = {}

        page.update(offensive_player_stats.get(player_id, {}))

        page.update(defensive_player_stats.get(player_id, {}))

        add_lineup_metrics(page)

        page["player_id"] = player_id
        page["name"] = player_map[player_id]["name"]
        page["team_id"] = player_map[player_id]["team_id"]

        results.append(page)

    results.sort(
        key=lambda player: player.get("net_rating", 0),
        reverse=True,
    )

    return results

    # next: accumulate the possession for every player
    # who was on offense and every player who was on defense


def get_lineup_league_summary_stats(
    lineup_size: int = 5, team_id: str | None = None, game_id: str | None = None,
    dataset: str = "demo",
) -> list[LineupRecord]:
    """Return lineup summaries across the entire league."""

    offensive_linemap = {}
    defensive_linemap = {}
    q4_offensive_linemap = {}
    q4_defensive_linemap = {}

    # 1. build player_id -> (team_id, name) map once
    player_map = {}
    team_rosters = {}

    for p in Player.objects.filter(team__dataset=dataset):
        player_map[p.id] = (p.team_id, p.name)

        if p.team_id not in team_rosters:
            team_rosters[p.team_id] = []

        team_rosters[p.team_id].append(
            {
                "player_id": p.id,
                "name": p.name,
            }
        )

    # 2. iterate possessions
    #    2a. build offensive lineup key + validate
    #    2b. build defensive lineup key + validate
    #    2c. add raw fields to offense accumulator under key
    #    2d. add raw fields to defense accumulator under key

    # added: filtered possessions.
    possessions = Possession.objects.filter(game__dataset=dataset)
    if team_id:
        possessions = possessions.filter(
            Q(offensive_team_id=team_id) | Q(defensive_team_id=team_id)
        )
    if game_id:
        possessions = possessions.filter(game_id=game_id)

    for possession in possessions:
        off_ids = possession.offensive_player_ids
        def_ids = possession.defensive_player_ids

        off_keys = validate_and_key(
            off_ids, possession.offensive_team_id, player_map, lineup_size
        )
        def_keys = validate_and_key(
            def_ids, possession.defensive_team_id, player_map, lineup_size
        )

        if team_id:
            if possession.offensive_team_id != team_id:
                off_keys = []

            if possession.defensive_team_id != team_id:
                def_keys = []

        for off_key in off_keys:
            ensure(
                offensive_linemap, off_key, prefix="offensive_", field_map=STAT_FIELDS
            )
            add_stats(
                offensive_linemap[off_key],
                possession,
                prefix="offensive_",
                field_map=STAT_FIELDS,
            )

        for def_key in def_keys:
            ensure(
                defensive_linemap, def_key, prefix="defensive_", field_map=STAT_FIELDS
            )
            add_stats(
                defensive_linemap[def_key],
                possession,
                prefix="defensive_",
                field_map=STAT_FIELDS,
            )

            # fourth quarter stats
        add_fourth_quarter_stats(
            possession, off_keys, def_keys, q4_offensive_linemap, q4_defensive_linemap
        )

    # 3. merge offense + defense accumulators into one dict per key
    all_keys = set(offensive_linemap) | set(defensive_linemap)

    merged = {}

    for key in all_keys:
        page = {}

        page.update(offensive_linemap.get(key, {}))
        page.update(defensive_linemap.get(key, {}))
        page.update(q4_offensive_linemap.get(key, {}))
        page.update(q4_defensive_linemap.get(key, {}))

        merged[key] = page

    # 4. compute percentages, total_possessions
    results = []

    for key, page in merged.items():

        add_lineup_metrics(page)

        player_ids = list(key[1])

        page["team_id"] = key[0]
        page["player_ids"] = player_ids

        page["team_roster"] = team_rosters.get(key[0], [])

        players = []

        for player_id in player_ids:
            name = player_map[player_id][1]

            players.append({"player_id": player_id, "name": name})

        page["players"] = players

        results.append(page)

    return results
