"""Persist a validated NBA snapshot without replacing the fictional dataset."""

import json
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from django.db import transaction

from app.dbmodels.models import Game, Player, Possession, Team
from app.helpers.nba_import import convert_nba_game


POSSESSION_COUNTING_FIELDS = (
    'period',
    'seconds',
    'counts_as_possession',
    'fg2_made',
    'fg2_attempted',
    'fg3_made',
    'fg3_attempted',
    'fg_made',
    'fg_attempted',
    'ft_made',
    'ft_attempted',
    'rebounds_offense',
    'rebounds_defense',
    'rebound_opportunities',
    'assists',
    'steals',
    'turnovers',
    'blocks',
    'offensive_fouls',
    'defensive_fouls',
    'shooting_fouls',
    'points',
    'shot_attempts',
    'shot_attempt_points',
    'ft_potential_points',
    'transition_take_fouls',
)


def source_uuid(kind, identifier):
    return uuid5(NAMESPACE_URL, f'https://nba.com/{kind}/{identifier}')


def load_json(directory, filename):
    with open(directory / filename, encoding='utf-8') as raw_file:
        return json.load(raw_file)


def ingest_teams(boxscore, dataset):
    team_map = {}

    for side in ('homeTeam', 'awayTeam'):
        raw_team = boxscore[side]
        source_team = str(raw_team['teamId'])

        team, _ = Team.objects.update_or_create(
            id=source_uuid('team', f'{dataset}/{source_team}'),
            defaults={
                'name': f"{raw_team['teamCity']} {raw_team['teamName']}",
                'dataset': dataset,
            },
        )

        team_map[source_team] = team

    return team_map


def ingest_players(boxscore, dataset, team_map):
    player_map = {}

    for side in ('homeTeam', 'awayTeam'):
        raw_team = boxscore[side]
        source_team = str(raw_team['teamId'])
        team = team_map[source_team]

        for raw_player in raw_team['players']:
            source_player = str(raw_player['personId'])
            player_name = f"{raw_player['firstName']} {raw_player['familyName']}".strip()

            # A player-team identity preserves earlier games after a trade.
            player, _ = Player.objects.update_or_create(
                id=source_uuid('player', f'{dataset}/{source_team}/{source_player}'),
                defaults={
                    'team': team,
                    'name': player_name,
                },
            )

            player_map[(source_team, source_player)] = player.id

    return player_map


def ingest_game(boxscore, dataset, game_date, team_map):
    game_id = str(boxscore['gameId'])
    home_team_id = str(boxscore['homeTeam']['teamId'])
    away_team_id = str(boxscore['awayTeam']['teamId'])

    game, _ = Game.objects.update_or_create(
        id=source_uuid('game', game_id),
        defaults={
            'date': game_date,
            'dataset': dataset,
            'source_id': game_id,
            'home_team': team_map[home_team_id],
            'away_team': team_map[away_team_id],
        },
    )

    Game.objects.select_for_update().get(id=game.id)

    return game


def ingest_possessions(game, segments, team_map, player_map):
    possessions = []

    for index, segment in enumerate(segments):
        offensive_team_id = str(segment['offensive_team_id'])
        defensive_team_id = str(segment['defensive_team_id'])

        offensive_player_ids = []
        defensive_player_ids = []

        for player_id in segment['offensive_player_ids']:
            player_key = (offensive_team_id, str(player_id))
            offensive_player_ids.append(player_map[player_key])

        for player_id in segment['defensive_player_ids']:
            player_key = (defensive_team_id, str(player_id))
            defensive_player_ids.append(player_map[player_key])

        counting_stats = {
            field: segment[field] for field in POSSESSION_COUNTING_FIELDS
        }

        possession = Possession(
            id=source_uuid('segment', f'{game.source_id}/{index}'),
            game=game,
            offensive_team=team_map[offensive_team_id],
            defensive_team=team_map[defensive_team_id],
            offensive_player_ids=offensive_player_ids,
            defensive_player_ids=defensive_player_ids,
            **counting_stats,
        )

        possessions.append(possession)

    # Replace only this game's previous import, atomically and repeatably.
    Possession.objects.filter(game=game).delete()
    Possession.objects.bulk_create(possessions)

    return possessions


def import_nba_snapshot(directory):
    directory = Path(directory)
    boxscore = load_json(directory, 'boxscore.json')
    playbyplay = load_json(directory, 'playbyplay.json')

    # Parsing and validation finish before the database is changed.
    converted = convert_nba_game(boxscore, playbyplay)
    game_id = str(boxscore['gameId'])
    game_date = date.fromisoformat(boxscore['gameEt'][:10])

    season_start = game_date.year

    if game_date.month < 7:
        season_start -= 1

    season_end = str(season_start + 1)[-2:]
    dataset = f'nba-{season_start}-{season_end}'

    with transaction.atomic():
        team_map = ingest_teams(boxscore, dataset)
        player_map = ingest_players(boxscore, dataset, team_map)
        game = ingest_game(boxscore, dataset, game_date, team_map)
        possessions = ingest_possessions(
            game,
            converted['possessions'],
            team_map,
            player_map,
        )

    completed_possessions = sum(
        possession.counts_as_possession for possession in possessions
    )

    return {
        'game_id': str(game.id),
        'source_game_id': game_id,
        'dataset': dataset,
        'segments': len(possessions),
        'completed_possessions': completed_possessions,
        'validation': converted['validation'],
        'methodology': converted['methodology'],
    }
