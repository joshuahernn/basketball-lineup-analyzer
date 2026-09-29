import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { BaseService } from './base.service';

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
  gameId?: string
): Observable<{
  endpoint: string;
  apiResponse: unknown;
}> {
  const endpoint = `${this.baseUrl}/lineups`;

  const queryParams: Record<string, string | number> = {
    n: lineupSize,
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

getTeamGames(teamId: string): Observable<string[]> {
  const endpoint = `${this.baseUrl}/team-games`;

  const queryParams = {
    team_id: teamId,
  };

  const params = this.buildQueryParams(queryParams);

  return this.get(endpoint, params).pipe(
    map((data) => data as string[])
  );
}

 getTeamSummary(teamId: string, gameId: string = ''): Observable<unknown> {
  const endpoint = `${this.baseUrl}/team-summary`;
  const queryParams: Record<string, string> = { team_id: teamId };

  if (gameId) {
    queryParams['game_id'] = gameId;
  }

  const params = this.buildQueryParams(queryParams);

  return this.get(endpoint, params);
}


getPlayerImpact(): Observable<unknown> {
  const endpoint = `${this.baseUrl}/player-impact`;

  return this.get(endpoint);
}


}
