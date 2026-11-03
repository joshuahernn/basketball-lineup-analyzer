from django.conf import settings
from django.test import TestCase

from app.dbmodels.models import Game, Possession, Team
from app.helpers.nba_storage import import_nba_snapshot
from scripts.ingest_raw_data import (
    ingest_games,
    ingest_players,
    ingest_possessions,
    ingest_teams,
)


class NbaIntegrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        ingest_teams()
        ingest_games()
        ingest_players()
        ingest_possessions()

        cls.snapshot = settings.BASE_DIR / "raw_data/nba/2026-27/0022600002"
        cls.import_result = import_nba_snapshot(cls.snapshot)

        cls.philly = Team.objects.get(name="Philadelphia 76ers")
        cls.nba_game = Game.objects.get(source_id="0022600002")


    def test_datasets_and_teams_are_isolated(self):
        datasets = self.client.get("/api/v1/datasets").json()
        dataset_ids = {item["id"] for item in datasets}

        self.assertEqual(dataset_ids, {"demo", "nba-2026-27"})

        nba_teams = self.client.get(
            "/api/v1/teams",
            {"dataset": "nba-2026-27"},
        ).json()
        demo_teams = self.client.get(
            "/api/v1/teams",
            {"dataset": "demo"},
        ).json()
        nba_team_names = {team["name"] for team in nba_teams}

        self.assertEqual(nba_team_names, {"Philadelphia 76ers", "New York Knicks"})
        self.assertEqual(len(demo_teams), 3)

        demo_lineups = self.client.get("/api/v1/lineups").json()

        self.assertEqual(len(demo_lineups), 227)

        nba_players = self.client.get(
            "/api/v1/player-impact",
            {"dataset": "nba-2026-27"},
        ).json()

        self.assertEqual(len(nba_players), 19)


    def test_scores_and_game_metadata_reconcile(self):
        params = {"dataset": "nba-2026-27", "team_id": str(self.philly.id)}
        summary = self.client.get("/api/v1/team-summary", params).json()

        self.assertEqual(summary["team_score"], 106)
        self.assertEqual(summary["opponent_score"], 100)
        self.assertEqual(summary["game_date"], "2026-10-20")

        self.assertGreater(summary["offensive_possessions"], 0)
        self.assertEqual(summary["offensive_fg_made"], 37)
        self.assertEqual(summary["offensive_fg_attempted"], 89)
        self.assertEqual(summary["offensive_ft_made"], 21)

        games = self.client.get("/api/v1/games", params).json()

        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["home_team_name"], "New York Knicks")
        self.assertEqual(games[0]["away_team_name"], "Philadelphia 76ers")


    def test_reimport_is_idempotent_and_preserves_demo(self):
        before = list(
            Possession.objects.filter(game=self.nba_game).order_by("id").values()
        )

        import_nba_snapshot(self.snapshot)

        after = list(
            Possession.objects.filter(game=self.nba_game).order_by("id").values()
        )

        self.assertEqual(before, after)

        demo_possession_count = Possession.objects.filter(game__dataset="demo").count()

        self.assertEqual(demo_possession_count, 1348)
        self.assertEqual(Game.objects.count(), 8)


    def test_dataset_filter_cannot_mix_nba_into_demo(self):
        params = {"dataset": "demo", "team_id": str(self.philly.id)}
        lineups = self.client.get("/api/v1/lineups", params).json()

        self.assertEqual(lineups, [])

        games = self.client.get("/api/v1/team-games", params).json()

        self.assertEqual(games, [])


    def test_invalid_filter_returns_400(self):
        invalid_lineup_size = self.client.get("/api/v1/lineups", {"n": "0"})

        self.assertEqual(invalid_lineup_size.status_code, 400)

        invalid_team_id = self.client.get(
            "/api/v1/team-summary",
            {"team_id": "invalid"},
        )

        self.assertEqual(invalid_team_id.status_code, 400)

        invalid_dataset = self.client.get("/api/v1/teams", {"dataset": "missing"})

        self.assertEqual(invalid_dataset.status_code, 400)
