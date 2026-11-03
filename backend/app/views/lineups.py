# -*- coding: utf-8 -*-
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from uuid import UUID

from app.dbmodels.models import Game, Team
from app.helpers.lineups import (
    get_lineup_league_summary_stats,
    get_team_game_ids,
    get_team_summary_stats,
    get_player_impact_stats,
)


DATASET_NAMES = {"demo": "Fictional demo", "nba-2026-27": "NBA · 2026–27"}


def selected_dataset(request):
    dataset = request.query_params.get("dataset", "demo")
    if dataset not in DATASET_NAMES:
        raise ValidationError({"dataset": "Choose an available dataset."})
    return dataset


def optional_uuid(request, name):
    value = request.query_params.get(name)
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        raise ValidationError({name: "Expected a valid UUID."})


class LineupsLeagueSummary(APIView):
    def get(self, request):
        try:
            lineup_size = int(request.query_params.get("n", 5))
        except (ValueError, TypeError):
            raise ValidationError({"n": "Lineup size must be an integer from 1 to 5."})

        if not 1 <= lineup_size <= 5:
            raise ValidationError({"n": "Lineup size must be between 1 and 5."})

        team_id = optional_uuid(request, "team_id")
        game_id = optional_uuid(request, "game_id")
        dataset = selected_dataset(request)

        results = get_lineup_league_summary_stats(
            lineup_size=lineup_size,
            team_id=team_id,
            game_id=game_id,
            dataset=dataset,
        )

        return Response(results)


class TeamGames(APIView):
    def get(self, request):
        team_id = optional_uuid(request, "team_id")
        dataset = selected_dataset(request)

        if not team_id:
            return Response([])

        games = get_team_game_ids(team_id, dataset=dataset)

        return Response(games)


class TeamSummary(APIView):
    def get(self, request):
        team_id = optional_uuid(request, "team_id")
        game_id = optional_uuid(request, "game_id")
        dataset = selected_dataset(request)

        if not team_id:
            return Response({})

        summary = get_team_summary_stats(
            team_id,
            game_id,
            dataset=dataset,
        )

        return Response(summary)


class PlayerImpact(APIView):

    def get(self, request):
        dataset = selected_dataset(request)
        results = get_player_impact_stats(dataset=dataset)

        return Response(results)


class Datasets(APIView):
    def get(self, request):
        available = set(Game.objects.values_list("dataset", flat=True).distinct())

        results = [
            {"id": key, "name": name}
            for key, name in DATASET_NAMES.items() if key in available
        ]

        return Response(results)


class Teams(APIView):
    def get(self, request):
        dataset = selected_dataset(request)
        teams = (
            Team.objects.filter(dataset=dataset)
            .prefetch_related("player_set")
            .order_by("name")
        )

        results = [
            {
                "team_id": team.id,
                "name": team.name,
                "players": [
                    {"player_id": player.id, "name": player.name}
                    for player in sorted(team.player_set.all(), key=lambda player: player.name)
                ],
            }
            for team in teams
        ]

        return Response(results)


class Games(APIView):
    def get(self, request):
        dataset = selected_dataset(request)
        team_id = optional_uuid(request, "team_id")
        games = Game.objects.filter(dataset=dataset).select_related("home_team", "away_team")

        if team_id:
            games = games.filter(id__in=get_team_game_ids(team_id, dataset=dataset))

        results = [
            {
                "game_id": game.id,
                "date": game.date,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_team_name": game.home_team.name if game.home_team else None,
                "away_team_name": game.away_team.name if game.away_team else None,
            }
            for game in games.order_by("date", "id")
        ]

        return Response(results)
