import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, forkJoin } from 'rxjs';
import { DatasetOption, GameOption, LineupsService } from '../_services/lineups.service';
import { AgCharts } from 'ag-charts-angular';
import { AgChartOptions, AllCommunityModule, ModuleRegistry } from 'ag-charts-community';
import { MatButtonToggleModule } from '@angular/material/button-toggle';

ModuleRegistry.registerModules([AllCommunityModule]);

interface ButtonOption {
  label: string;
  value: string;
  players: Player[];
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
  game_date?: string;
  offensive_possessions: number;
  defensive_possessions: number;
}

interface PlayerImpact {
  player_id: string;
  name: string;
  offensive_possessions: number;
  defensive_possessions: number;
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
  imports: [AgCharts, MatButtonToggleModule, DatePipe, FormsModule],
  templateUrl: './lineups-summary.component.html',
  styleUrl: './lineups-summary.component.scss',
})
export class LineupsSummaryComponent implements OnInit, OnDestroy {
  datasets: DatasetOption[] = [];
  selectedDataset: string = '';
  teamOptions: ButtonOption[] = [];

  selectedTeam: string = '';
  selectedTeamPlayers: Player[] = [];
  lineups: Lineup[] = [];
  games: GameOption[] = [];
  selectedGame: string = '';
  teamSummary: TeamSummary | null = null;
  ratingsChartOptions: AgChartOptions = {};
  comparisonTeams: {
    teamId: string;
    teamName: string;
    summary: TeamSummary;
  }[] = [];
  comparisonTeamIds: string[] = [];
  activeGamePlayerIds: Set<string> = new Set();
  playerImpact: PlayerImpact[] = [];
  minimumPossessions = 1;
  loading = true;
  errorMessage = '';

  private datasetsRequest?: Subscription;
  private datasetRequest?: Subscription;
  private gamesRequest?: Subscription;
  private statsRequest?: Subscription;
  private comparisonRequest?: Subscription;

  private readonly lineupsService = inject(LineupsService);
  private readonly cdr = inject(ChangeDetectorRef);

  get isNbaDataset(): boolean {
    return this.selectedDataset.startsWith('nba-');
  }

  ngOnInit(): void {
    this.datasetsRequest = this.lineupsService.getDatasets().subscribe({
      next: (datasets) => {
        this.datasets = datasets;

        const initial = datasets.find((dataset) => dataset.id.startsWith('nba-')) ?? datasets[0];

        if (initial) {
          this.loadDataset(initial.id);
        } else {
          this.loading = false;
          this.errorMessage = 'No datasets are available yet.';
          this.cdr.markForCheck();
        }
      },
      error: () => this.showError('Could not load datasets. Check that the local API is running.'),
    });
  }

  ngOnDestroy(): void {
    this.datasetsRequest?.unsubscribe();
    this.datasetRequest?.unsubscribe();
    this.cancelTeamRequests();
  }

  onDatasetChange(dataset: string): void {
    this.loadDataset(dataset);
  }

  private loadDataset(dataset: string): void {
    this.datasetRequest?.unsubscribe();
    this.cancelTeamRequests();
    this.selectedDataset = dataset;
    this.selectedTeam = '';
    this.teamOptions = [];
    this.playerImpact = [];
    this.resetTeamState();
    this.minimumPossessions = this.isNbaDataset ? 5 : 1;
    this.loading = true;
    this.errorMessage = '';

    this.datasetRequest = forkJoin({
      teams: this.lineupsService.getTeams(dataset),
      impact: this.lineupsService.getPlayerImpact(dataset),
    }).subscribe({
      next: ({ teams, impact }) => {
        this.teamOptions = teams.map((team) => ({
          label: team.name,
          value: team.team_id,
          players: team.players,
        }));
        this.playerImpact = (impact as PlayerImpact[]).filter(
          (player) => player.offensive_possessions > 0 && player.defensive_possessions > 0,
        );
        this.loading = false;

        if (this.isNbaDataset && teams.length) {
          const team = teams.find((item) => item.name.includes('Philadelphia')) ?? teams[0];
          this.selectTeam(team.team_id);
        }

        this.cdr.markForCheck();
      },
      error: () => this.showError('Could not load this dataset. Please try selecting it again.'),
    });
  }

  private cancelTeamRequests(): void {
    this.gamesRequest?.unsubscribe();
    this.statsRequest?.unsubscribe();
    this.comparisonRequest?.unsubscribe();
  }

  private resetTeamState(): void {
    this.selectedGame = '';
    this.games = [];
    this.selectedTeamPlayers = [];
    this.lineups = [];
    this.teamSummary = null;
    this.comparisonTeams = [];
    this.comparisonTeamIds = [];
    this.activeGamePlayerIds = new Set();
    this.ratingsChartOptions = {};
  }

  private showError(message: string): void {
    this.loading = false;
    this.errorMessage = message;
    this.cdr.markForCheck();
  }

  onTeamChange(teamId: string): void {
    this.selectTeam(teamId);
  }

  private selectTeam(teamId: string, gameId: string = ''): void {
    this.cancelTeamRequests();
    this.resetTeamState();
    this.selectedTeam = teamId;
    this.errorMessage = '';
    this.loading = false;

    if (!teamId) {
      return;
    }

    this.selectedTeamPlayers = this.teamOptions.find((team) => team.value === teamId)?.players ?? [];

    this.gamesRequest = this.lineupsService.getGames(teamId, this.selectedDataset).subscribe({
      next: (games) => {
        this.games = games;
        this.cdr.markForCheck();
      },
      error: () => this.showError('Could not load the game list.'),
    });

    this.onGameToggleChange(gameId);
  }

  getTeamName(teamId: string): string {
    return this.teamOptions.find((team) => team.value === teamId)?.label ?? 'Team';
  }

  gameOpponent(game: GameOption): string | null {
    if (game.home_team_id === this.selectedTeam) {
      return game.away_team_name;
    }

    if (game.away_team_id === this.selectedTeam) {
      return game.home_team_name;
    }

    return null;
  }

  selectGame(gameId: string): void {
    this.statsRequest?.unsubscribe();
    this.comparisonRequest?.unsubscribe();
    this.selectedGame = gameId;
    this.teamSummary = null;
    this.lineups = [];
    this.comparisonTeams = [];
    this.comparisonTeamIds = [];
    this.activeGamePlayerIds = new Set();
    this.loading = true;
    this.errorMessage = '';

    this.statsRequest = forkJoin({
      summary: this.lineupsService.getTeamSummary(this.selectedTeam, gameId, this.selectedDataset),
      lineups: this.lineupsService.getLineupsLeagueSummary(
        5,
        this.selectedTeam,
        gameId,
        this.selectedDataset,
      ),
    }).subscribe({
      next: ({ summary, lineups }) => {
        this.teamSummary = summary as TeamSummary;
        this.lineups = lineups.apiResponse as Lineup[];

        this.activeGamePlayerIds = new Set(
          this.lineups.flatMap((lineup) => lineup.players.map((player) => player.player_id)),
        );
        this.loading = false;

        this.buildRatingsChart();

        this.cdr.markForCheck();
      },
      error: () => this.showError('Could not load team statistics. Please try selecting the team again.'),
    });
  }

  selectAllGames(): void {
    this.selectGame('');
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
    this.comparisonRequest?.unsubscribe();
    this.comparisonTeamIds = teamIds.slice(0, 2);
    this.comparisonTeams = [];
    this.buildRatingsChart();

    if (!this.comparisonTeamIds.length) {
      return;
    }

    const requestedIds = [...this.comparisonTeamIds];

    this.comparisonRequest = forkJoin(
      requestedIds.map((teamId) =>
        this.lineupsService.getTeamSummary(teamId, '', this.selectedDataset),
      ),
    ).subscribe({
      next: (summaries) => {
        this.comparisonTeams = requestedIds.map((teamId, index) => ({
          teamId,
          teamName: this.getTeamName(teamId),
          summary: summaries[index] as TeamSummary,
        }));

        this.buildRatingsChart();
        this.cdr.markForCheck();
      },
      error: () => {
        this.comparisonTeamIds = [];
        this.showError('Could not load comparison statistics.');
      },
    });
  }

  viewOpponentStats(): void {
    if (!this.teamSummary?.opponent_team_id || !this.selectedGame) {
      return;
    }

    const opponentTeamId = this.teamSummary.opponent_team_id;
    const gameId = this.selectedGame;

    this.selectTeam(opponentTeamId, gameId);
  }

  onMinimumPossessionsChange(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    this.minimumPossessions = Number.isFinite(value) ? Math.max(1, Math.floor(value)) : 1;
  }

  get lineupRecommendations(): {
    title: string;
    reason: string;
    lineup: Lineup;
  }[] {
    const lineups = this.lineups.filter(
      (lineup) =>
        lineup.team_id === this.selectedTeam &&
        lineup.offensive_possessions >= this.minimumPossessions &&
        lineup.defensive_possessions >= this.minimumPossessions,
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
