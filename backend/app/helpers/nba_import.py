"""Convert NBA.com hanaV3 events into lineup-attributed possession segments.

This deliberately supports the downloaded NBA.com game-page schema, not arbitrary
liveData feeds. Unrecognized events or ambiguous lineups fail the import. A
possession can contain several segments when players are substituted. Statistics
and elapsed game-clock time belong to the lineup at that event, except free
throws are credited to the lineup at the foul, matching NBA plus/minus accounting.
Only the final segment receives the completed possession. See methodology notes.
"""

from collections import Counter, defaultdict
import re


class NBAImportError(ValueError):
    """Source data cannot be converted without making an unsafe assumption."""


COUNT_FIELDS = (
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


def clock_seconds(clock):
    match = re.fullmatch(r'PT(\d+)M(\d+(?:\.\d+)?)S', clock)

    if not match:
        raise NBAImportError(f'Unsupported game clock: {clock}')

    return int(match[1]) * 60 + float(match[2])


def _require(condition, message):
    if not condition:
        raise NBAImportError(message)


def _rosters(boxscore):
    teams = {}
    players = {}

    for side in ('awayTeam', 'homeTeam'):
        team = boxscore[side]
        team_id = str(team['teamId'])
        teams[team_id] = team

    for team_id, team in teams.items():
        for player in team['players']:
            player_id = str(player['personId'])
            _require(player_id not in players, f'Duplicate player {player_id}')

            players[player_id] = {
                **player,
                'team_id': team_id,
            }

    return teams, players


def _name_id(name, players, team_id=None):
    matches = []

    for player_id, player in players.items():
        if team_id is not None and player['team_id'] != team_id:
            continue

        player_names = {
            player['familyName'].casefold(),
            player.get('nameI', '').casefold(),
            f"{player['firstName']} {player['familyName']}".casefold(),
        }

        if name.casefold() in player_names:
            matches.append(player_id)

    _require(len(matches) == 1, f'Ambiguous or missing player name: {name}')

    return matches[0]


def _substitution(event, players):
    match = re.fullmatch(r'SUB: (.+) FOR (.+)', event['description'])
    _require(
        match is not None,
        f"Unrecognized substitution: {event['description']}",
    )

    team_id = str(event['teamId'])
    outgoing = str(event['personId'])

    _require(
        outgoing in players and players[outgoing]['team_id'] == team_id,
        'Invalid outgoing player',
    )
    _require(
        _name_id(match[2], players, team_id) == outgoing,
        'Substitution ID/name mismatch',
    )

    incoming = _name_id(match[1], players, team_id)

    return team_id, outgoing, incoming


def _find_period_starters(events, teams, players, period):
    starters = {team_id: set() for team_id in teams}
    seen = set()

    for event in events:
        player_id = str(event['personId'])

        if event['actionType'] == 'Substitution':
            team_id, outgoing, incoming = _substitution(event, players)

            if outgoing not in seen:
                starters[team_id].add(outgoing)

            seen.update((outgoing, incoming))

        elif player_id in players:
            if player_id not in seen:
                team_id = players[player_id]['team_id']
                starters[team_id].add(player_id)

            seen.add(player_id)

    for team_id, lineup in starters.items():
        _require(
            len(lineup) == 5,
            f'Cannot infer five starters for period {period}, team {team_id}',
        )

    return starters


def _validate_player_minutes(players, minutes):
    discrepancies = {}

    for player_id, player in players.items():
        recorded_minutes = player['statistics'].get('minutes', '')

        if recorded_minutes:
            parts = recorded_minutes.split(':')
            expected_seconds = int(parts[0]) * 60 + float(parts[1])
            difference = round(minutes[player_id] - expected_seconds, 3)

            _require(
                abs(difference) <= 1,
                f'Minutes mismatch for {player_id}: {difference}s',
            )

            if difference:
                discrepancies[player_id] = difference

        else:
            _require(
                minutes[player_id] == 0,
                f'Nonparticipant {player_id} has reconstructed minutes',
            )

    return discrepancies


def reconstruct_lineups(boxscore, actions):
    """Infer each period's starters, then verify every substitution and actor."""
    teams, players = _rosters(boxscore)
    snapshots = []
    minutes = Counter()
    period_starters = {}
    periods = sorted({event['period'] for event in actions})

    for period in periods:
        events = [event for event in actions if event['period'] == period]
        starters = _find_period_starters(events, teams, players, period)
        period_starters[str(period)] = {}
        lineups = {}

        for team_id, lineup in starters.items():
            period_starters[str(period)][team_id] = sorted(lineup)
            lineups[team_id] = set(lineup)

        last_clock = 720 if period <= 4 else 300

        for event in events:
            clock = clock_seconds(event['clock'])
            _require(
                clock <= last_clock,
                f"Clock moves backwards at action {event['actionId']}",
            )

            for lineup in lineups.values():
                for player_id in lineup:
                    minutes[player_id] += last_clock - clock

            last_clock = clock
            snapshot = {}

            for team_id, lineup in lineups.items():
                snapshot[team_id] = sorted(lineup)

            snapshots.append(snapshot)

            if event['actionType'] == 'Substitution':
                team_id, outgoing, incoming = _substitution(event, players)
                _require(
                    outgoing in lineups[team_id] and incoming not in lineups[team_id],
                    f"Inconsistent substitution at action {event['actionId']}",
                )

                lineups[team_id].remove(outgoing)
                lineups[team_id].add(incoming)

            elif str(event['personId']) in players:
                player_id = str(event['personId'])
                team_id = players[player_id]['team_id']

                _require(
                    player_id in lineups[team_id],
                    f"Off-court player event at action {event['actionId']}",
                )

        _require(last_clock == 0, f'Period {period} is incomplete')

    discrepancies = _validate_player_minutes(players, minutes)

    return snapshots, dict(minutes), period_starters, discrepancies


def _validate_team_totals(
    segments,
    teams,
    team_turnovers,
    team_heaves,
    personal_fouls,
):
    validation = {}

    for team_id, team in teams.items():
        offense_rows = []
        defense_rows = []

        for row in segments:
            if row['offensive_team_id'] == team_id:
                offense_rows.append(row)

            if row['defensive_team_id'] == team_id:
                defense_rows.append(row)

        totals = {}

        for field in COUNT_FIELDS:
            totals[field] = sum(row[field] for row in offense_rows)

        expected = team['statistics']
        comparisons = {
            'points': expected['points'],
            'fg_made': expected['fieldGoalsMade'],
            'fg_attempted': expected['fieldGoalsAttempted'],
            'fg3_made': expected['threePointersMade'],
            'fg3_attempted': expected['threePointersAttempted'],
            'ft_made': expected['freeThrowsMade'],
            'ft_attempted': expected['freeThrowsAttempted'],
            'assists': expected['assists'],
            'rebounds_offense': expected['reboundsOffensive'],
            'turnovers': expected['turnovers'] + team_turnovers[team_id],
        }

        for field, value in comparisons.items():
            _require(
                totals[field] == value,
                f"{team['teamTricode']} {field} mismatch: {totals[field]} != {value}",
            )

        defensive_fields = [
            ('rebounds_defense', 'reboundsDefensive'),
            ('blocks', 'blocks'),
            ('steals', 'steals'),
        ]

        for field, boxscore_field in defensive_fields:
            total = sum(row[field] for row in defense_rows)
            _require(
                total == expected[boxscore_field],
                f'{field} does not reconcile',
            )

        _require(
            personal_fouls[team_id] == expected['foulsPersonal'],
            'Personal foul totals do not reconcile',
        )

        possessions = sum(row['counts_as_possession'] for row in offense_rows)
        validation[team_id] = {
            'points': totals['points'],
            'possessions': possessions,
            'team_only_turnovers': team_turnovers[team_id],
            'team_heaves': team_heaves[team_id],
            'boxscore_totals_reconciled': True,
        }

    return validation


def _validate_segment_players(segments, periods, minutes, players):
    elapsed_seconds = sum(row['seconds'] for row in segments)
    game_seconds = sum(720 if period <= 4 else 300 for period in periods)

    _require(
        abs(elapsed_seconds - game_seconds) < .01,
        'Reconstructed elapsed time does not equal game duration',
    )

    segment_seconds = Counter()
    plus_minus = Counter()

    for row in segments:
        on_court_players = row['offensive_player_ids'] + row['defensive_player_ids']

        for player_id in on_court_players:
            segment_seconds[player_id] += row['seconds']

        for player_id in row['offensive_player_ids']:
            plus_minus[player_id] += row['points']

        for player_id in row['defensive_player_ids']:
            plus_minus[player_id] -= row['points']

    for player_id, seconds in minutes.items():
        _require(
            abs(segment_seconds[player_id] - seconds) < .01,
            f'Lineup time attribution mismatch for {player_id}',
        )
        _require(
            plus_minus[player_id] == players[player_id]['statistics']['plusMinusPoints'],
            f'Player plus/minus does not match source box score for {player_id}',
        )

    return dict(plus_minus)


def _format_result(boxscore, periods, teams, players, segments, validation):
    team_records = []
    player_records = []

    for team_id, team in teams.items():
        team_records.append({
            'source_id': team_id,
            'name': f"{team['teamCity']} {team['teamName']}",
            'abbreviation': team['teamTricode'],
        })

    for player_id, player in players.items():
        player_records.append({
            'source_id': player_id,
            'team_source_id': player['team_id'],
            'name': f"{player['firstName']} {player['familyName']}",
        })

    return {
        'game': {
            'source_id': boxscore['gameId'],
            'date': boxscore['gameCode'].split('/')[0],
            'periods': len(periods),
        },
        'teams': team_records,
        'players': player_records,
        'possessions': segments,
        'validation': validation,
        'methodology': [
            'Statistics and game-clock seconds follow the lineup present at each event; substitutions split a possession into segments.',
            'Free throws are credited to the lineup at the foul, matching NBA box-score plus/minus accounting. Actual substitutions still determine subsequent live-play lineups and minutes.',
            'Each completed possession is counted once, on its ending lineup. Zero-possession segments retain earlier statistics and time.',
            'Player rebound percentages exclude team/dead-ball rebounds from both numerator and denominator.',
            'Turnover rates include team-only shot-clock turnovers in addition to player turnovers.',
            'Separately labeled team heaves are possession events but are excluded from conventional box-score shooting attempts.',
            'Period-ending possessions are counted when the team controlled the ball; no extra possession is created after a buzzer basket.',
        ],
    }


def convert_nba_game(boxscore, playbyplay):
    """Return source-ID teams, players and validated possession segments."""
    _require(boxscore['gameId'] == playbyplay['gameId'], 'Game IDs differ')
    _require(boxscore['gameStatus'] == 3, 'Only completed games can be imported')

    actions = playbyplay['actions']
    _require(bool(actions), 'No play-by-play events')

    action_ids = {event['actionId'] for event in actions}
    _require(len(action_ids) == len(actions), 'Duplicate actionId')

    teams, players = _rosters(boxscore)
    lineups, minutes, starters, rounding = reconstruct_lineups(boxscore, actions)
    periods = sorted({event['period'] for event in actions})

    _require(
        periods == list(range(1, boxscore['period'] + 1)),
        'Missing game periods',
    )

    segments = []
    current = None
    possession_open = False
    offense = None
    period = None
    last_clock = None
    rebound_pending = False
    rebound_totals = defaultdict(lambda: (0, 0))
    event_segments = {}
    team_turnovers = Counter()
    team_heaves = Counter()
    deadball_team_rebounds = 0
    personal_fouls = Counter()
    possession_number = 0

    def other(team_id):
        _require(team_id in teams, f'Unknown team {team_id}')

        return next(team for team in teams if team != team_id)

    def event_team(event):
        team_id = str(event['teamId'])

        if team_id in teams:
            return team_id

        player_id = str(event['personId'])

        if player_id in teams:
            return player_id

        if player_id in players:
            return players[player_id]['team_id']

        return None

    def jump_winner(event):
        match = re.search(r': Tip to (.+)$', event['description'])
        _require(match is not None, 'Jump ball has no identified winner')

        return players[_name_id(match[1], players)]['team_id']

    def initial_offense(start):
        for event in actions[start:]:
            if event['period'] != actions[start]['period']:
                break

            event_type = event['actionType']

            if event_type == 'Jump Ball':
                return jump_winner(event)

            if event_type in ('Made Shot', 'Missed Shot', 'Turnover', 'Free Throw'):
                return event_team(event)

            if event_type == 'Foul':
                if 'Offensive' in event['subType']:
                    return event_team(event)

                return other(event_team(event))

        raise NBAImportError('Cannot identify the first possession of the period')

    def segment(index, lineup_override=None):
        nonlocal current, possession_open

        lineup = lineup_override or lineups[index]

        if current is not None and (
            current['offensive_player_ids'] != lineup[offense]
            or current['defensive_player_ids'] != lineup[other(offense)]
        ):
            current = None

        if current is None:
            _require(offense in teams, 'Cannot attribute event without offensive team')

            current = {
                **{field: 0 for field in COUNT_FIELDS},
                'offensive_team_id': offense,
                'defensive_team_id': other(offense),
                'offensive_player_ids': lineup[offense],
                'defensive_player_ids': lineup[other(offense)],
                'period': actions[index]['period'],
                'seconds': 0.0,
                'counts_as_possession': False,
                'source_sequence': len(segments) + 1,
                'source_start_action_id': actions[index]['actionId'],
                'possession_number': possession_number + 1,
            }
            segments.append(current)
            possession_open = True

        return current

    def finish(index, next_offense=None):
        nonlocal current, offense, possession_number, rebound_pending, possession_open

        # A new team does not receive a phantom possession after a buzzer basket.
        if possession_open:
            ending_row = current if current is not None else segment(index)
            ending_row['counts_as_possession'] = True
            possession_number += 1

        current = None
        possession_open = False
        rebound_pending = False
        offense = next_offense if next_offense is not None else other(offense)

    def assert_offense(team_id, event):
        _require(
            team_id == offense,
            f"Possession mismatch at action {event['actionId']}: {event['description']}",
        )

    def and_one(index):
        shot = actions[index]

        for event in actions[index + 1:]:
            if (
                event['period'] != shot['period']
                or clock_seconds(shot['clock']) - clock_seconds(event['clock']) > 2
            ):
                return False

            if event['actionType'] == 'Free Throw':
                return (
                    event['personId'] == shot['personId']
                    and '1 of 1' in event['subType']
                )

            if event['actionType'] in ('Made Shot', 'Missed Shot', 'Turnover', 'Jump Ball'):
                return False

        return False

    def retained_free_throw(index):
        event = actions[index]
        retained_types = ('technical', 'flagrant', 'clear path', 'take foul')

        for foul_type in retained_types:
            if foul_type in event['subType'].lower():
                return True

        for prior in reversed(actions[:index]):
            if (
                prior['period'] != event['period']
                or clock_seconds(prior['clock']) != clock_seconds(event['clock'])
            ):
                break

            if prior['actionType'] == 'Foul':
                return prior['subType'] in (
                    'Defense 3 Second',
                    'Technical',
                    'Double Technical',
                    'Flagrant',
                    'Clear Path',
                    'Transition Take',
                )

        return False

    def free_throw_lineup(index):
        # NBA plus/minus credits free throws to players on court at the foul,
        # even when substitutions are recorded between the attempts. Keep the
        # physical substitution timeline for minutes and subsequent live events.
        event = actions[index]

        for prior_index in range(index - 1, -1, -1):
            prior = actions[prior_index]

            if prior['period'] != event['period'] or prior['clock'] != event['clock']:
                break

            if prior['actionType'] == 'Foul':
                return lineups[prior_index]

        raise NBAImportError(
            f"Free throw has no identifiable same-clock foul: {event['actionId']}"
        )

    for index, event in enumerate(actions):
        event_type = event['actionType']
        team_id = event_team(event)
        player_id = str(event['personId'])
        clock = clock_seconds(event['clock'])

        if event['period'] != period:
            _require(not possession_open, 'Previous period did not end')
            period = event['period']
            offense = initial_offense(index)
            last_clock = 720 if period <= 4 else 300

        elapsed = last_clock - clock
        _require(elapsed >= 0, 'Events are not in game-clock order')

        if elapsed:
            segment(index)['seconds'] += elapsed

        last_clock = clock

        if event_type == 'period':
            if event['subType'] == 'end':
                if possession_open:
                    finish(index)
            else:
                _require(event['subType'] == 'start', 'Unknown period marker')

            continue

        if event_type == 'Substitution':
            # The next event snapshot has the substituted lineup. Earlier segments
            # remain uncounted until this possession actually ends.
            current = None
            continue

        if event_type == 'Jump Ball':
            winner = jump_winner(event)
            if winner != offense:
                finish(index, winner)

            continue

        if event_type in ('Timeout', 'Instant Replay'):
            continue

        if event_type == 'Violation':
            _require(
                event['subType'] in ('Delay Of Game', 'Defensive Goaltending'),
                f"Unsupported violation: {event['subType']}",
            )

            continue

        if event_type == '':
            linked = event_segments.get(event['actionNumber'])
            _require(linked is not None, 'Unlinked block/steal event')

            if ' BLOCK ' in event['description']:
                linked['blocks'] += 1
            elif ' STEAL ' in event['description']:
                linked['steals'] += 1
            else:
                raise NBAImportError(
                    f"Unsupported auxiliary event: {event['description']}"
                )

            continue

        if event_type in ('Made Shot', 'Missed Shot'):
            assert_offense(team_id, event)

            row = segment(index)
            shot_value = 3 if '3PT' in event['description'] else 2

            row[f'fg{shot_value}_attempted'] += 1
            row['fg_attempted'] += 1
            row['shot_attempts'] += 1
            event_segments[event['actionNumber']] = row

            if event_type == 'Made Shot':
                row[f'fg{shot_value}_made'] += 1
                row['fg_made'] += 1
                row['points'] += shot_value
                row['shot_attempt_points'] += shot_value

                assist = re.search(r'\b\d+ AST\)', event['description'])
                row['assists'] += int(bool(assist))

                if not and_one(index):
                    finish(index)

            else:
                rebound_pending = True

            continue

        if event_type == 'Heave':
            # The source reports this separately from conventional box-score FGA.
            _require(event['subType'] == 'Team Field Goal Attempt', 'Unsupported heave')

            heave_team_matches = False

            for source_team_id, team in teams.items():
                if source_team_id != offense:
                    continue

                description = event['description'].casefold()
                team_name = team['teamName'].casefold()
                heave_team_matches = description.startswith(team_name)
                break

            _require(heave_team_matches, 'Unresolved heave team')

            team_heaves[offense] += 1
            segment(index)
            rebound_pending = False

            continue

        if event_type == 'Turnover':
            assert_offense(team_id, event)

            row = segment(index)
            row['turnovers'] += 1

            if player_id in teams:
                team_turnovers[team_id] += 1

            event_segments[event['actionNumber']] = row
            finish(index)

            continue

        if event_type == 'Free Throw':
            assert_offense(team_id, event)

            match = re.search(r'(\d+) of (\d+)', event['subType'])
            _require(match is not None, 'Unrecognized free-throw sequence')

            number = int(match[1])
            total = int(match[2])
            retained = retained_free_throw(index)
            row = segment(index, lineup_override=free_throw_lineup(index))

            row['ft_attempted'] += 1
            row['ft_potential_points'] += 1

            if number == 1 and total > 1:
                row['shot_attempts'] += 1
                row['shot_attempt_points'] += total

            made = not event['description'].startswith('MISS ')

            if made:
                row['ft_made'] += 1
                row['points'] += 1

            rebound_pending = not made and number == total and not retained

            if number == total and made and not retained:
                finish(index)

            continue

        if event_type == 'Rebound':
            if player_id in players:
                match = re.search(r'\(Off:(\d+) Def:(\d+)\)', event['description'])
                _require(match is not None, 'Missing rebound counters')

                offensive_rebounds = int(match[1])
                defensive_rebounds = int(match[2])
                previous_offensive, previous_defensive = rebound_totals[player_id]
                rebound_change = (
                    offensive_rebounds - previous_offensive,
                    defensive_rebounds - previous_defensive,
                )

                _require(
                    rebound_change in ((1, 0), (0, 1)),
                    'Invalid rebound counter increment',
                )
                _require(
                    rebound_pending,
                    f"Player rebound has no live miss: {event['actionId']}",
                )

                offensive = offensive_rebounds > previous_offensive

                _require(
                    (team_id == offense) == offensive,
                    'Rebound possession attribution disagrees with source',
                )

                rebound_totals[player_id] = (
                    offensive_rebounds,
                    defensive_rebounds,
                )
                row = segment(index)
                row['rebound_opportunities'] += 1
                row['rebounds_offense' if offensive else 'rebounds_defense'] += 1
                rebound_pending = False

                if not offensive:
                    finish(index, team_id)

            elif team_id in teams:
                # Team/dead-ball rebounds are retained for possession transitions,
                # but excluded from the player-rebound percentage denominator.
                deadball_team_rebounds += 1

                if rebound_pending and team_id != offense:
                    segment(index)
                    finish(index, team_id)

                rebound_pending = False

            else:
                raise NBAImportError('Unresolved rebound team')

            continue

        if event_type == 'Foul':
            subtype = event['subType']

            if subtype in ('Defense 3 Second', 'Technical', 'Double Technical'):
                continue

            row = segment(index)
            personal_fouls[team_id] += 1

            if 'Offensive' in subtype:
                assert_offense(team_id, event)
                row['offensive_fouls'] += 1

            else:
                _require(
                    team_id == other(offense),
                    f"Unexpected foul attribution at {event['actionId']}",
                )

                row['defensive_fouls'] += 1
                row['shooting_fouls'] += int(subtype == 'Shooting')
                row['transition_take_fouls'] += int(subtype == 'Transition Take')

            continue

        raise NBAImportError(f'Unsupported event type: {event_type}')

    _require(not possession_open, 'Game ended with an unfinished possession')

    for row in segments:
        row['seconds'] = round(row['seconds'], 3)

    validation = {
        'teams': {},
        'player_seconds': minutes,
        'minute_rounding_differences': rounding,
        'period_starters': starters,
        'raw_events': len(actions),
        'segments': len(segments),
    }

    validation['teams'] = _validate_team_totals(
        segments,
        teams,
        team_turnovers,
        team_heaves,
        personal_fouls,
    )
    validation['player_plus_minus'] = _validate_segment_players(
        segments,
        periods,
        minutes,
        players,
    )
    validation['player_plus_minus_reconciled'] = True

    return _format_result(
        boxscore,
        periods,
        teams,
        players,
        segments,
        validation,
    )
