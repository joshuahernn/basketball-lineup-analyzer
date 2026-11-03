"""Regression checks against the locally saved NBA game, never a network call."""

from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase

from app.helpers.nba_import import NBAImportError, clock_seconds, convert_nba_game


DATA_DIR = Path(__file__).resolve().parents[2] / "raw_data/nba/2026-27/0022600002"


class NBAImportTests(TestCase):

    @classmethod
    def setUpClass(cls):
        boxscore_file = DATA_DIR / "boxscore.json"
        playbyplay_file = DATA_DIR / "playbyplay.json"

        cls.boxscore = json.loads(boxscore_file.read_text(encoding="utf-8"))
        cls.playbyplay = json.loads(playbyplay_file.read_text(encoding="utf-8"))

        cls.result = convert_nba_game(cls.boxscore, cls.playbyplay)


    def row_at(self, action_id):
        return next(
            row
            for row in reversed(self.result["possessions"])
            if row["source_start_action_id"] <= action_id
        )


    def test_final_scores_and_player_boxscore_totals_reconcile(self):
        validation = self.result["validation"]["teams"]
        all_teams_reconciled = all(
            team["boxscore_totals_reconciled"] for team in validation.values()
        )

        self.assertEqual(validation["1610612755"]["points"], 106)
        self.assertEqual(validation["1610612752"]["points"], 100)
        self.assertTrue(all_teams_reconciled)

        # Team-only turnovers are valid source events absent from player totals.
        self.assertEqual(validation["1610612755"]["team_only_turnovers"], 2)
        self.assertEqual(validation["1610612752"]["team_only_turnovers"], 1)


    def test_each_possession_is_counted_once_even_with_substitutions(self):
        possession_groups = defaultdict(list)

        for row in self.result["possessions"]:
            possession_groups[row["possession_number"]].append(row)

            self.assertEqual(len(set(row["offensive_player_ids"])), 5)
            self.assertEqual(len(set(row["defensive_player_ids"])), 5)

        has_split_possession = any(
            len(rows) > 1 for rows in possession_groups.values()
        )
        self.assertTrue(has_split_possession)

        for rows in possession_groups.values():
            completed_possessions = sum(row["counts_as_possession"] for row in rows)
            offensive_teams = {row["offensive_team_id"] for row in rows}

            self.assertEqual(completed_possessions, 1)
            self.assertTrue(rows[-1]["counts_as_possession"])
            self.assertEqual(len(offensive_teams), 1)


    def test_rotations_preserve_all_game_time_and_player_minutes(self):
        rows = self.result["possessions"]
        game_seconds = sum(row["seconds"] for row in rows)

        self.assertAlmostEqual(game_seconds, 48 * 60)

        player_seconds = Counter()

        for row in rows:
            player_ids = row["offensive_player_ids"] + row["defensive_player_ids"]

            for player_id in player_ids:
                player_seconds[player_id] += row["seconds"]

        for side in ("awayTeam", "homeTeam"):
            for player in self.boxscore[side]["players"]:
                player_id = str(player["personId"])
                raw_minutes = player["statistics"]["minutes"]
                expected_seconds = 0

                if raw_minutes:
                    expected_seconds = sum(
                        float(value) * multiplier
                        for value, multiplier in zip(raw_minutes.split(":"), (60, 1))
                    )

                difference = abs(player_seconds[player_id] - expected_seconds)

                self.assertLessEqual(difference, 1)


    def test_and_one_basket_and_free_throw_share_one_possession(self):
        # Hart's made basket (56) and one free throw (59) are one possession.
        basket = self.row_at(56)
        free_throw = self.row_at(59)

        self.assertEqual(basket["possession_number"], free_throw["possession_number"])

        rows = [
            row
            for row in self.result["possessions"]
            if row["possession_number"] == basket["possession_number"]
        ]

        self.assertEqual(sum(row["points"] for row in rows), 3)
        self.assertEqual(sum(row["counts_as_possession"] for row in rows), 1)


    def test_defensive_three_second_free_throw_does_not_end_possession(self):
        technical_free_throw = self.row_at(293)
        next_shot = self.row_at(294)

        self.assertEqual(
            technical_free_throw["possession_number"],
            next_shot["possession_number"],
        )


    def test_free_throws_use_foul_lineup_and_substitutions_apply_to_next_live_play(self):
        first_free_throw = self.row_at(193)
        second_free_throw = self.row_at(197)

        self.assertEqual(
            first_free_throw["possession_number"],
            second_free_throw["possession_number"],
        )

        # Three Knicks substitutes enter during the free throws. NBA +/- still
        # credits both free throws to the lineup that committed the foul.
        self.assertEqual(
            first_free_throw["defensive_player_ids"],
            second_free_throw["defensive_player_ids"],
        )

        next_play = self.row_at(198)

        self.assertNotEqual(
            second_free_throw["defensive_player_ids"],
            next_play["offensive_player_ids"],
        )
        self.assertFalse(first_free_throw["counts_as_possession"])
        self.assertTrue(second_free_throw["counts_as_possession"])


    def test_every_player_plus_minus_matches_official_boxscore(self):
        self.assertTrue(self.result["validation"]["player_plus_minus_reconciled"])

        player_plus_minus = Counter()

        for row in self.result["possessions"]:
            for player_id in row["offensive_player_ids"]:
                player_plus_minus[player_id] += row["points"]

            for player_id in row["defensive_player_ids"]:
                player_plus_minus[player_id] -= row["points"]

        for side in ("awayTeam", "homeTeam"):
            for player in self.boxscore[side]["players"]:
                player_id = str(player["personId"])
                expected_plus_minus = player["statistics"]["plusMinusPoints"]

                self.assertEqual(player_plus_minus[player_id], expected_plus_minus)


    def test_unverified_player_attribution_fails_import(self):
        invalid_boxscore = deepcopy(self.boxscore)
        invalid_boxscore["awayTeam"]["players"][0]["statistics"]["plusMinusPoints"] += 1

        with self.assertRaisesRegex(NBAImportError, "Player plus/minus"):
            convert_nba_game(invalid_boxscore, self.playbyplay)


    def test_missing_substitution_fails_instead_of_guessing(self):
        invalid_playbyplay = deepcopy(self.playbyplay)
        invalid_playbyplay["actions"] = [
            event
            for event in invalid_playbyplay["actions"]
            if event["actionId"] != 38
        ]

        with self.assertRaises(NBAImportError):
            convert_nba_game(self.boxscore, invalid_playbyplay)


    def test_inconsistent_boxscore_fails_instead_of_importing(self):
        invalid_boxscore = deepcopy(self.boxscore)
        invalid_boxscore["awayTeam"]["statistics"]["points"] += 1

        with self.assertRaisesRegex(NBAImportError, "points mismatch"):
            convert_nba_game(invalid_boxscore, self.playbyplay)


    def test_unknown_event_type_fails_instead_of_dropping_data(self):
        invalid_playbyplay = deepcopy(self.playbyplay)
        timeout_event = next(
            event
            for event in invalid_playbyplay["actions"]
            if event["actionType"] == "Timeout"
        )
        timeout_event["actionType"] = "Unknown Event"

        with self.assertRaisesRegex(NBAImportError, "Unsupported event type"):
            convert_nba_game(self.boxscore, invalid_playbyplay)


    def test_duplicate_action_ids_are_rejected_but_linked_action_numbers_work(self):
        # NBA uses shared actionNumbers for a shot/block or turnover/steal pair.
        events = self.playbyplay["actions"]
        action_numbers = {event["actionNumber"] for event in events}

        self.assertLess(len(action_numbers), len(events))
        self.assertEqual(self.result["validation"]["raw_events"], len(events))

        invalid_playbyplay = deepcopy(self.playbyplay)
        first_action_id = invalid_playbyplay["actions"][0]["actionId"]
        invalid_playbyplay["actions"][1]["actionId"] = first_action_id

        with self.assertRaisesRegex(NBAImportError, "Duplicate actionId"):
            convert_nba_game(self.boxscore, invalid_playbyplay)


    def test_fractional_game_clocks(self):
        self.assertEqual(clock_seconds("PT01M23.50S"), 83.5)

        with self.assertRaises(NBAImportError):
            clock_seconds("not a clock")
