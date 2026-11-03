import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { BaseService } from './base.service';

export interface DatasetOption {
  id: string;
  name: string;
}

export interface RosterPlayer {
  player_id: string;
  name: string;
}

export interface TeamOption {
  team_id: string;
  name: string;
  players: RosterPlayer[];
}

export interface GameOption {
  game_id: string;
  date: string;
  home_team_id: string | null;
  away_team_id: string | null;
  home_team_name: string | null;
  away_team_name: string | null;
}

@Injectable({ providedIn: 'root' })
export class LineupsService extends BaseService {
  constructor(protected override http: HttpClient) {
    super(http);
  }

  private buildQueryParams(queryParams: Record<string, string | number>): HttpParams {
    return Object.entries(queryParams).reduce(
      (params, [key, value]) => params.set(key, String(value)),
      new HttpParams(),
    );
  }

  private buildDisplayedEndpointWithParams(
    endpoint: string,
    queryParams: Record<string, string | number>,
  ): string {
    const queryString = new URLSearchParams(
      Object.entries(queryParams).map(([key, value]) => [key, String(value)]),
    ).toString();
    return queryString ? `${endpoint}?${queryString}` : endpoint;
  }

  getLineupsLeagueSummary(
    lineupSize: number = 5,
    teamId?: string,
    gameId?: string,
    dataset: string = 'demo',
  ): Observable<{
    endpoint: string;
    apiResponse: unknown;
  }> {
    const endpoint = `${this.baseUrl}/lineups`;

    const queryParams: Record<string, string | number> = {
      n: lineupSize,
      dataset: dataset,
    };

    if (teamId) {
      queryParams['team_id'] = teamId;
    }

    if (gameId) {
      queryParams['game_id'] = gameId;
    }

    const params = this.buildQueryParams(queryParams);

    const displayedEndpointWithParams =
      this.buildDisplayedEndpointWithParams(endpoint, queryParams);

    return this.get(endpoint, params).pipe(
      map((data) => ({
        endpoint: displayedEndpointWithParams,
        apiResponse: data,
      })),
    );
  }

  getGames(teamId: string, dataset: string): Observable<GameOption[]> {
    const endpoint = `${this.baseUrl}/games`;

    const queryParams = {
      team_id: teamId,
      dataset: dataset,
    };

    const params = this.buildQueryParams(queryParams);

    return this.get(endpoint, params).pipe(
      map((data) => data as GameOption[]),
    );
  }

  getTeamSummary(teamId: string, gameId: string = '', dataset: string = 'demo'): Observable<unknown> {
    const endpoint = `${this.baseUrl}/team-summary`;
    const queryParams: Record<string, string> = { team_id: teamId, dataset };

    if (gameId) {
      queryParams['game_id'] = gameId;
    }

    const params = this.buildQueryParams(queryParams);

    return this.get(endpoint, params);
  }

  getPlayerImpact(dataset: string = 'demo'): Observable<unknown> {
    const endpoint = `${this.baseUrl}/player-impact`;
    const params = this.buildQueryParams({ dataset });

    return this.get(endpoint, params);
  }

  getDatasets(): Observable<DatasetOption[]> {
    const endpoint = `${this.baseUrl}/datasets`;

    return this.get(endpoint).pipe(
      map((data) => data as DatasetOption[]),
    );
  }

  getTeams(dataset: string): Observable<TeamOption[]> {
    const endpoint = `${this.baseUrl}/teams`;
    const params = this.buildQueryParams({ dataset });

    return this.get(endpoint, params).pipe(
      map((data) => data as TeamOption[]),
    );
  }
}
