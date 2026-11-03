import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { DatasetOption, LineupsService } from '../_services/lineups.service';

interface LineupSizeOption {
  value: number;
  label: string;
}

@Component({
  selector: 'lineups-summary-response-component',
  imports: [FormsModule, MatFormFieldModule, MatSelectModule],
  templateUrl: './lineups-summary-response.component.html',
  styleUrl: './lineups-summary-response.component.scss',
})
export class LineupsSummaryResponseComponent implements OnInit, OnDestroy {
  private readonly lineupsService = inject(LineupsService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly lineupSizes: LineupSizeOption[] = [
    { value: 5, label: '5 players' },
    { value: 4, label: '4 players' },
    { value: 3, label: '3 players' },
    { value: 2, label: '2 players' },
    { value: 1, label: '1 player' },
  ];

  datasets: DatasetOption[] = [];
  selectedDataset = '';
  private datasetRequest?: Subscription;
  private responseRequest?: Subscription;

  leagueLineupSize = 5;
  leagueEndpoint = '';
  leagueApiResponse = '';

  ngOnInit(): void {
    this.datasetRequest = this.lineupsService.getDatasets().subscribe({
      next: (datasets) => {
        this.datasets = datasets;
        this.selectedDataset = datasets.find((dataset) => dataset.id.startsWith('nba-'))?.id ?? datasets[0]?.id ?? '';
        if (this.selectedDataset) {
          this.fetchLeagueApiResponse();
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.leagueApiResponse = 'Could not load datasets. Check that the local API is running.';
        this.cdr.markForCheck();
      },
    });
  }

  ngOnDestroy(): void {
    this.datasetRequest?.unsubscribe();
    this.responseRequest?.unsubscribe();
  }

  changeDataset(): void {
    this.fetchLeagueApiResponse();
  }

  changeLeagueLineupSize(): void {
    this.fetchLeagueApiResponse();
  }

  private fetchLeagueApiResponse(): void {
    this.responseRequest?.unsubscribe();
    this.leagueApiResponse = 'Loading…';
    this.responseRequest = this.lineupsService.getLineupsLeagueSummary(this.leagueLineupSize, undefined, undefined, this.selectedDataset).subscribe({
      next: (data) => {
        this.leagueEndpoint = data.endpoint;
        this.leagueApiResponse = JSON.stringify(data.apiResponse, null, 2);
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.leagueEndpoint = 'error';
        this.leagueApiResponse = JSON.stringify(err, null, 2);
        this.cdr.detectChanges();
      },
    });
  }
}
