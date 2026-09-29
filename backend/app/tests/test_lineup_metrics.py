from django.test import SimpleTestCase
from app.helpers.lineup_metrics import add_lineup_metrics, safe_percentage


class LineupMetricsTests(SimpleTestCase):

    def setUp(self):

        self.page = {
            "offensive_possessions": 100,
            "defensive_possessions": 100,

            "offensive_points": 120,
            "defensive_points": 110,

            "offensive_fg_made": 40,
            "offensive_fg_attempted": 80,
            "offensive_fg2_made": 25,
            "offensive_fg2_attempted": 40,
            "offensive_fg3_made": 15,
            "offensive_fg3_attempted": 40,

            "defensive_fg_made": 42,
            "defensive_fg_attempted": 84,
            "defensive_fg2_made": 30,
            "defensive_fg2_attempted": 48,
            "defensive_fg3_made": 12,
            "defensive_fg3_attempted": 36,

            "offensive_ft_made": 25,
            "offensive_ft_attempted": 30,
            "defensive_ft_made": 14,
            "defensive_ft_attempted": 20,

            "offensive_rebounds_offense": 15,
            "offensive_rebound_opportunities": 50,

            "defensive_rebounds_defense": 35,
            "defensive_rebound_opportunities": 50,

            "offensive_assists": 28,
            "offensive_turnovers": 12,

            "offensive_seconds": 1400,
            "defensive_seconds": 1500,

            "q4_offensive_points": 30,
            "q4_offensive_possessions": 25,
            "q4_defensive_points": 24,
            "q4_defensive_possessions": 25,
            "q4_offensive_fg_attempted": 20,
            "q4_offensive_ft_attempted": 8,
        }

        self.result = add_lineup_metrics(self.page.copy())


    # safe percentage
    def test_safe_percentage(self):
        self.assertEqual(safe_percentage(10, 20), 0.5)
        self.assertEqual(safe_percentage(10, 0), 0)


    # total possessions
    def test_total_possessions(self):
        self.assertEqual(self.result["total_possessions"], 200)


    # field goal percentages
    def test_field_goal_percentages(self):
        self.assertAlmostEqual(self.result["offensive_fg_pct"], 50)
        self.assertAlmostEqual(self.result["offensive_fg2_pct"], 62.5)
        self.assertAlmostEqual(self.result["offensive_fg3_pct"], 37.5)

        self.assertAlmostEqual(self.result["defensive_fg_pct"], 50)
        self.assertAlmostEqual(self.result["defensive_fg2_pct"], 62.5)
        self.assertAlmostEqual(self.result["defensive_fg3_pct"], (12 / 36) * 100)


    # offensive and defensive ratings
    def test_ratings(self):
        self.assertAlmostEqual(self.result["offensive_rating"], 120)
        self.assertAlmostEqual(self.result["defensive_rating"], 110)
        self.assertAlmostEqual(self.result["net_rating"], 10)


    # rebounding
    def test_rebound_percentages(self):
        self.assertAlmostEqual(self.result["offensive_rebound_percentage"], 30)
        self.assertAlmostEqual(self.result["defensive_rebound_percentage"], 70)


    # turnovers
    def test_turnover_rate(self):
        self.assertAlmostEqual(self.result["turnover_rate"], 12)


    # true shooting
    def test_true_shooting_percentage(self):
        expected_offensive = 120 / (2 * (80 + 0.44 * 30)) * 100
        expected_defensive = 110 / (2 * (84 + 0.44 * 20)) * 100

        self.assertAlmostEqual(self.result["offensive_ts_pct"], expected_offensive)
        self.assertAlmostEqual(self.result["defensive_ts_pct"], expected_defensive)


    # speed and tempo
    def test_speed_and_tempo(self):
        expected_pace = (200 * 1440) / 2900

        self.assertEqual(self.result["total_possession_seconds"], 2900)
        self.assertAlmostEqual(self.result["pace"], expected_pace)
        self.assertAlmostEqual(self.result["average_possession_length"], 14)


    # ball movement
    def test_ball_movement(self):
        self.assertAlmostEqual(self.result["assist_percentage"], 70)
        self.assertAlmostEqual(self.result["assist_to_turnover_ratio"], 28 / 12)


    # shot profile
    def test_shot_profile(self):
        self.assertAlmostEqual(self.result["three_point_attempt_rate"], 50)
        self.assertAlmostEqual(self.result["free_throw_rate"], 37.5)


    # fourth quarter
    def test_fourth_quarter(self):
        expected_ts = 30 / (2 * (20 + 0.44 * 8)) * 100

        self.assertAlmostEqual(self.result["q4_offensive_rating"], 120)
        self.assertAlmostEqual(self.result["q4_defensive_rating"], 96)
        self.assertAlmostEqual(self.result["q4_net_rating"], 24)
        self.assertAlmostEqual(self.result["q4_ts_pct"], expected_ts)


    # zero values
    def test_empty_page(self):
        result = add_lineup_metrics({})

        self.assertEqual(result["total_possessions"], 0)
        self.assertEqual(result["offensive_rating"], 0)
        self.assertEqual(result["defensive_rating"], 0)
        self.assertEqual(result["net_rating"], 0)
        self.assertEqual(result["offensive_rebound_percentage"], 0)
        self.assertEqual(result["defensive_rebound_percentage"], 0)
        self.assertEqual(result["turnover_rate"], 0)
        self.assertEqual(result["offensive_ts_pct"], 0)
        self.assertEqual(result["defensive_ts_pct"], 0)
        self.assertEqual(result["pace"], 0)
        self.assertEqual(result["average_possession_length"], 0)
        self.assertEqual(result["assist_percentage"], 0)
        self.assertEqual(result["assist_to_turnover_ratio"], 0)
        self.assertEqual(result["three_point_attempt_rate"], 0)
        self.assertEqual(result["free_throw_rate"], 0)
        self.assertEqual(result["q4_offensive_rating"], 0)
        self.assertEqual(result["q4_defensive_rating"], 0)
        self.assertEqual(result["q4_net_rating"], 0)
        self.assertEqual(result["q4_ts_pct"], 0)
