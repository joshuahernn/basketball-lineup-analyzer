# -*- coding: utf-8 -*-
from rest_framework.response import Response
from rest_framework.views import APIView
from uuid import UUID

from app.helpers.lineups import (get_lineup_league_summary_stats,
                                 get_team_game_ids,get_team_summary_stats, get_player_impact_stats)


class LineupsLeagueSummary(APIView):
    def get(self, request):
        lineup_size = int(request.query_params.get("n", 5))

        team_id = request.query_params.get("team_id")
        game_id = request.query_params.get("game_id")

        if team_id:
            team_id = UUID(team_id)

        if game_id:
            game_id = UUID(game_id)

        results = get_lineup_league_summary_stats(
            lineup_size=lineup_size,
            team_id=team_id,
            game_id=game_id,
        )


        return Response(results)


class TeamGames(APIView):
    def get(self, request):
        team_id = request.query_params.get("team_id")

        if not team_id:
            return Response([])

        team_id = UUID(team_id)

        games = get_team_game_ids(team_id)

        return Response(games)


class TeamSummary(APIView):
    def get(self, request):
        team_id = request.query_params.get("team_id")
        game_id = request.query_params.get("game_id")

        if not team_id:
            return Response({})

        team_id = UUID(team_id)

        if game_id:
            game_id = UUID(game_id)

        summary = get_team_summary_stats(
            team_id,
            game_id,
        )

        return Response(summary)


class PlayerImpact(APIView):

    def get(self, request):
        results = get_player_impact_stats()

        return Response(results)
