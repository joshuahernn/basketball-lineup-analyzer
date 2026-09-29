import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { LineupsService } from '../_services/lineups.service';
import { AgCharts } from 'ag-charts-angular';
import { AgChartOptions, AllCommunityModule, ModuleRegistry } from 'ag-charts-community';
import { MatButtonToggleModule } from '@angular/material/button-toggle';

ModuleRegistry.registerModules([AllCommunityModule]);

interface ButtonOption {
  label: string;
  value: string;
}

interface Player {
  player_id: string;
  name: string;
}

interface TeamSummary {
  offensive_rating: number;
  defensive_rating: number;
  net_rating: number;
  offensive_fg_pct: number;
  offensive_fg2_pct: number;
  offensive_fg3_pct: number;
  offensive_ts_pct: number;
  turnover_rate: number;
  offensive_rebound_percentage: number;
  defensive_rebound_percentage: number;
  three_point_attempt_rate: number;
  free_throw_rate: number;
  assist_percentage: number;
  pace: number;
  average_possession_length: number;
  q4_offensive_rating: number;
  q4_defensive_rating: number;
  q4_net_rating: number;
  two_point_attempt_rate: number;
  assist_to_turnover_ratio: number;
  q4_ts_pct: number;
  opponent_team_id: string;
  team_score: number;
  opponent_score: number;
}

interface PlayerImpact {
  player_id: string;
  name: string;
  offensive_rating: number;
  defensive_rating: number;
  net_rating: number;
}

interface Lineup {
  team_id: string;
  players: Player[];
  team_roster: Player[];

  offensive_possessions: number;
  defensive_possessions: number;

  offensive_rating: number;
  defensive_rating: number;
  net_rating: number;

  offensive_rebound_percentage: number;
  defensive_rebound_percentage: number;
}

@Component({
  selector: 'lineups-summary-component',
  imports: [AgCharts, MatButtonToggleModule],
  templateUrl: './lineups-summary.component.html',
  styleUrl: './lineups-summary.component.scss',
})
export class LineupsSummaryComponent implements OnInit {
  teamOptions: ButtonOption[] = [
    {
      label: 'Justice League',
      value: '3c700625-848c-5afd-88c1-5cb60b0d5834',
    },
    {
      label: 'The Avengers',
      value: '36e29cdb-520a-58bb-9608-6bf9522decb6',
    },
    {
      label: 'Tune Squad',
      value: '11c7d162-14cb-5371-aeac-0c06dcdd6418',
    },
  ];

  selectedTeam: string = '';
  selectedTeamPlayers: Player[] = [];
  lineups: Lineup[] = [];
  allLineups: Lineup[] = [];
  gameIds: string[] = [];
  selectedGame: string = '';
  teamSummary: TeamSummary | null = null;
  ratingsChartOptions: AgChartOptions = {};
  comparisonTeams: {
    teamId: string;
    teamName: string;
    summary: TeamSummary;
  }[] = [];
  activeGamePlayerIds: Set<string> = new Set();
  playerImpact: PlayerImpact[] = [];

  get comparisonTeamIds(): string[] {
    return this.comparisonTeams.map((team) => team.teamId);
  }

  private readonly lineupsService = inject(LineupsService);
  private readonly cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    this.lineupsService.getLineupsLeagueSummary().subscribe({
      next: (data) => {
        this.lineups = data.apiResponse as Lineup[];
        this.allLineups = data.apiResponse as Lineup[];

        this.cdr.markForCheck();
      },
    });

    this.lineupsService.getPlayerImpact().subscribe({
      next: (data) => {
        this.playerImpact = data as PlayerImpact[];

        this.cdr.markForCheck();
      },
    });
  }

  onTeamChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.selectedTeam = select.value;
    this.selectedGame = '';
    this.gameIds = [];
    this.activeGamePlayerIds.clear();

    const teamLineup = this.allLineups.find((lineup) => lineup.team_id === this.selectedTeam);

    if (teamLineup) {
      this.selectedTeamPlayers = teamLineup.team_roster;
    } else {
      this.selectedTeamPlayers = [];
    }

    if (!this.selectedTeam) {
      return;
    }

    this.selectAllGames();

    this.lineupsService.getTeamGames(this.selectedTeam).subscribe({
      next: (games) => {
        this.gameIds = games;
        this.cdr.markForCheck();
      },
    });
  }

  loadTeamSummary(teamId: string, gameId: string = ''): void {
    this.lineupsService.getTeamSummary(teamId, gameId).subscribe({
      next: (data) => {
        this.teamSummary = data as TeamSummary;

        this.comparisonTeams = [];

        this.buildRatingsChart();

        this.cdr.markForCheck();
      },
    });
  }

  getTeamName(teamId: string): string {
    return this.teamOptions.find((team) => team.value === teamId)?.label ?? 'Team';
  }

  selectGame(gameId: string): void {
    this.selectedGame = gameId;

    this.loadTeamSummary(this.selectedTeam, gameId);

    this.lineupsService.getLineupsLeagueSummary(5, this.selectedTeam, gameId).subscribe({
      next: (data) => {
        this.lineups = data.apiResponse as Lineup[];

        this.activeGamePlayerIds = new Set(
          this.lineups.flatMap((lineup) => lineup.players.map((player) => player.player_id)),
        );

        this.cdr.markForCheck();
      },
    });
  }

  selectAllGames(): void {
    this.selectedGame = '';
    this.loadTeamSummary(this.selectedTeam);

    this.lineupsService.getLineupsLeagueSummary(5, this.selectedTeam).subscribe({
      next: (data) => {
        this.lineups = data.apiResponse as Lineup[];

        this.activeGamePlayerIds = new Set(
          this.lineups.flatMap((lineup) => lineup.players.map((player) => player.player_id)),
        );

        this.cdr.markForCheck();
      },
    });
  }

  buildRatingsChart(): void {
    if (!this.teamSummary) {
      return;
    }

    const teams = [
      {
        teamName: this.getTeamName(this.selectedTeam),
        summary: this.teamSummary,
      },
      ...this.comparisonTeams,
    ];

    const data: Record<string, string | number>[] = [
      {
        stat: 'Offensive Rating',
      },
      {
        stat: 'Defensive Rating',
      },
      {
        stat: 'Net Rating',
      },
    ];

    teams.forEach((team, index) => {
      const key = `team${index}`;

      data[0][key] = team.summary.offensive_rating;
      data[1][key] = team.summary.defensive_rating;
      data[2][key] = team.summary.net_rating;
    });

    this.ratingsChartOptions = {
      title: {
        text: 'Team Ratings',
      },
      subtitle: {
        text: '',
      },
      data: data,
      series: teams.map((team, index) => ({
        type: 'bar' as const,
        direction: 'vertical' as const,
        xKey: 'stat',
        yKey: `team${index}`,
        yName: team.teamName,
      })),
      axes: {
        y: {
          type: 'number',
          min: -20,
          max: 140,
        },
      },
    };
  }

  onGameToggleChange(gameId: string): void {
    if (gameId === '') {
      this.selectAllGames();
    } else {
      this.selectGame(gameId);
    }
  }

  onComparisonTeamsChange(teamIds: string[]): void {
    if (teamIds.length > 2) {
      return;
    }

    const removedTeams = this.comparisonTeams.filter((team) => !teamIds.includes(team.teamId));

    if (removedTeams.length > 0) {
      this.comparisonTeams = this.comparisonTeams.filter((team) => teamIds.includes(team.teamId));

      this.buildRatingsChart();
    }

    const newTeamId = teamIds.find(
      (teamId) => !this.comparisonTeams.some((team) => team.teamId === teamId),
    );

    if (!newTeamId) {
      return;
    }

    this.lineupsService.getTeamSummary(newTeamId).subscribe({
      next: (data) => {
        this.comparisonTeams.push({
          teamId: newTeamId,
          teamName: this.getTeamName(newTeamId),
          summary: data as TeamSummary,
        });

        this.buildRatingsChart();
        this.cdr.markForCheck();
      },
    });
  }

  viewOpponentStats(): void {
    if (!this.teamSummary || !this.selectedGame) {
      return;
    }

    const opponentTeamId = this.teamSummary.opponent_team_id;
    const gameId = this.selectedGame;

    this.selectedTeam = opponentTeamId;

    const teamLineup = this.allLineups.find((lineup) => lineup.team_id === opponentTeamId);

    if (teamLineup) {
      this.selectedTeamPlayers = teamLineup.team_roster;
    } else {
      this.selectedTeamPlayers = [];
    }

    this.loadTeamSummary(opponentTeamId, gameId);

    this.lineupsService.getLineupsLeagueSummary(5, opponentTeamId, gameId).subscribe({
      next: (data) => {
        this.lineups = data.apiResponse as Lineup[];

        this.activeGamePlayerIds = new Set(
          this.lineups.flatMap((lineup) => lineup.players.map((player) => player.player_id)),
        );

        this.cdr.markForCheck();
      },
    });

    this.lineupsService.getTeamGames(opponentTeamId).subscribe({
      next: (games) => {
        this.gameIds = games;
        this.cdr.markForCheck();
      },
    });
  }

  get lineupRecommendations(): {
    title: string;
    reason: string;
    lineup: Lineup;
  }[] {
    const lineups = this.lineups.filter(
      (lineup) =>
        lineup.team_id === this.selectedTeam &&
        lineup.offensive_possessions > 0 &&
        lineup.defensive_possessions > 0,
    );

    if (lineups.length === 0) {
      return [];
    }

    let rebounding = lineups[0];
    let scoring = lineups[0];
    let overall = lineups[0];

    for (const lineup of lineups) {
      const lineupRebounding =
        lineup.offensive_rebound_percentage + lineup.defensive_rebound_percentage;

      const bestRebounding =
        rebounding.offensive_rebound_percentage + rebounding.defensive_rebound_percentage;

      if (
        lineupRebounding > bestRebounding ||
        (lineupRebounding === bestRebounding && lineup.net_rating > rebounding.net_rating)
      ) {
        rebounding = lineup;
      }

      if (lineup.offensive_rating > scoring.offensive_rating) {
        scoring = lineup;
      }

      if (lineup.net_rating > overall.net_rating) {
        overall = lineup;
      }
    }

    return [
      {
        title: 'Rebounding:',
        reason: 'Control the boards.',
        lineup: rebounding,
      },
      {
        title: 'Scoring',
        reason: 'Maximize offensive output.',
        lineup: scoring,
      },
      {
        title: 'Best Overall',
        reason: 'Best two-way performance.',
        lineup: overall,
      },
    ];
  }
}
