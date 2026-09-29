def safe_percentage(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


def add_lineup_metrics(page):

    # total possessions
    page["total_possessions"] = page.get("offensive_possessions", 0) + page.get("defensive_possessions", 0)

    # field goal percentages
    page["offensive_fg_pct"] = safe_percentage(page.get("offensive_fg_made", 0), page.get("offensive_fg_attempted", 0)) * 100
    page["offensive_fg2_pct"] = safe_percentage(page.get("offensive_fg2_made", 0), page.get("offensive_fg2_attempted", 0)) * 100
    page["offensive_fg3_pct"] = safe_percentage(page.get("offensive_fg3_made", 0), page.get("offensive_fg3_attempted", 0)) * 100
    page["defensive_fg_pct"] = safe_percentage(page.get("defensive_fg_made", 0), page.get("defensive_fg_attempted", 0)) * 100
    page["defensive_fg2_pct"] = safe_percentage(page.get("defensive_fg2_made", 0), page.get("defensive_fg2_attempted", 0)) * 100
    page["defensive_fg3_pct"] = safe_percentage(page.get("defensive_fg3_made", 0), page.get("defensive_fg3_attempted", 0)) * 100

    # ratings
    page["offensive_rating"] = safe_percentage(page.get("offensive_points", 0), page.get("offensive_possessions", 0)) * 100
    page["defensive_rating"] = safe_percentage(page.get("defensive_points", 0), page.get("defensive_possessions", 0)) * 100
    page["net_rating"] = page.get("offensive_rating", 0) - page.get("defensive_rating", 0)

    # rebounding
    page["offensive_rebound_percentage"] = safe_percentage(page.get("offensive_rebounds_offense", 0), page.get("offensive_rebound_opportunities", 0)) * 100
    page["defensive_rebound_percentage"] = safe_percentage(page.get("defensive_rebounds_defense", 0), page.get("defensive_rebound_opportunities", 0)) * 100

    # turnover rate
    page["turnover_rate"] = safe_percentage(page.get("offensive_turnovers", 0), page.get("offensive_possessions", 0)) * 100

    # true shooting
    page["offensive_ts_pct"] = safe_percentage(page.get("offensive_points", 0), 2 * (page.get("offensive_fg_attempted", 0) + 0.44 * page.get("offensive_ft_attempted", 0))) * 100
    page["defensive_ts_pct"] = safe_percentage(page.get("defensive_points", 0), 2 * (page.get("defensive_fg_attempted", 0) + 0.44 * page.get("defensive_ft_attempted", 0))) * 100

    # play style metrics
    page["three_point_attempt_rate"] = safe_percentage(page.get("offensive_fg3_attempted", 0), page.get("offensive_fg_attempted", 0)) * 100
    page["two_point_attempt_rate"] = safe_percentage(page.get("offensive_fg2_attempted", 0), page.get("offensive_fg_attempted", 0)) * 100
    page["free_throw_rate"] = safe_percentage(page.get("offensive_ft_attempted", 0), page.get("offensive_fg_attempted", 0)) * 100
    page["assist_rate"] = safe_percentage(page.get("offensive_assists", 0), page.get("offensive_fg_made", 0)) * 100
    page["average_offensive_possession_seconds"] = safe_percentage(page.get("offensive_seconds", 0), page.get("offensive_possessions", 0))
    page["average_defensive_possession_seconds"] = safe_percentage(page.get("defensive_seconds", 0), page.get("defensive_possessions", 0))

    # fourth quarter
    page["q4_offensive_rating"] = safe_percentage(page.get("q4_offensive_points", 0), page.get("q4_offensive_possessions", 0)) * 100
    page["q4_defensive_rating"] = safe_percentage(page.get("q4_defensive_points", 0), page.get("q4_defensive_possessions", 0)) * 100
    page["q4_net_rating"] = page.get("q4_offensive_rating", 0) - page.get("q4_defensive_rating", 0)
    page["q4_ts_pct"] = safe_percentage(page.get("q4_offensive_points", 0), 2 * (page.get("q4_offensive_fg_attempted", 0) + 0.44 * page.get("q4_offensive_ft_attempted", 0))) * 100

    # play style - speed and tempo
    page["total_possession_seconds"] = page.get("offensive_seconds", 0) + page.get("defensive_seconds", 0)
    page["pace"] = safe_percentage(page.get("total_possessions", 0) * 1440, page.get("total_possession_seconds", 0))
    page["average_possession_length"] = safe_percentage(page.get("offensive_seconds", 0), page.get("offensive_possessions", 0))

    # play style - ball movement vs isolation
    page["assist_percentage"] = safe_percentage(page.get("offensive_assists", 0), page.get("offensive_fg_made", 0)) * 100
    page["assist_to_turnover_ratio"] = safe_percentage(page.get("offensive_assists", 0), page.get("offensive_turnovers", 0))

    # play style - shot profile and aggression
    page["three_point_attempt_rate"] = safe_percentage(page.get("offensive_fg3_attempted", 0), page.get("offensive_fg_attempted", 0)) * 100
    page["free_throw_rate"] = safe_percentage(page.get("offensive_ft_attempted", 0), page.get("offensive_fg_attempted", 0)) * 100

    # play style - second chances
    page["offensive_rebound_percentage"] = safe_percentage(page.get("offensive_rebounds_offense", 0), page.get("offensive_rebound_opportunities", 0)) * 100

    return page