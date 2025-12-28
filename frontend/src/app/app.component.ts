import { Component, OnInit } from '@angular/core';
import {
  AppService,
  SummaryResponse,
  AccountInsights,
  PaginatedRecordsResponse,
  HealthByStatusItem,
  NotificationsOverTimeItem
} from './app.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  // Dashboard title displayed in the UI header
  title = 'Customer Insights Dashboard';

  // ---------------- Summary state ----------------
  // Holds aggregated KPI values for the top summary cards
  summary?: SummaryResponse;

  // Loading and error flags for summary API call
  loadingSummary = false;
  summaryError?: string;

  // ---------------- Records & filters ----------------
  // Paginated account-level records shown in the table
  records: AccountInsights[] = [];

  // Loading and error flags for records API call
  recordsLoading = false;
  recordsError?: string;

  // Pagination state
  page = 1;
  pageSize = 5;
  totalPages = 1;

  // Filter inputs bound to the UI controls
  filterStatus: string = '';
  filterMinHealth?: number;
  filterSearch: string = '';

  // ---------------- Charts ----------------

  // Active vs Inactive
  pieLabels: string[] = ['Active', 'Inactive'];
  pieData: number[] = [0, 0];

  // Health by status
  healthBarLabels: string[] = [];
  healthBarDatasets: { data: number[]; label: string }[] = [
    { data: [], label: 'Accounts' }
  ];
  healthBarOptions: any = { responsive: true };

  // Notifications billed over time
  notificationsLineLabels: string[] = [];
  notificationsLineDatasets: { data: number[]; label: string }[] = [
    { data: [], label: 'Notifications Billed' }
  ];
  notificationsLineOptions: any = { responsive: true };

  // Top accounts by notifications billed
  topAccountsBarLabels: string[] = [];
  topAccountsBarDatasets: { data: number[]; label: string }[] = [
    { data: [], label: 'Notifications Billed' }
  ];
  topAccountsBarOptions: any = { responsive: true };
  // Inject AppService for all API communication
  constructor(private appService: AppService) {}

  ngOnInit(): void {
    // Load all dashboard data on initial component mount
    this.loadSummary();
    this.loadRecords();
    this.loadHealthByStatus();
    this.loadNotificationsOverTime();
  }

  // ---------------- Summary ----------------
  /**
   * Fetch high-level KPIs for the summary cards
   * Also updates the Active vs Inactive pie chart
   */
  loadSummary(): void {
    this.loadingSummary = true;
    this.summaryError = undefined;

    this.appService.getSummary().subscribe({
      next: (data) => {
        this.summary = data;
        this.loadingSummary = false;

        // Sync pie chart values with summary data
        this.pieData = [data.active_accounts, data.inactive_accounts];
      },
      error: (err) => {
        console.error('Error loading summary', err);
        this.summaryError = 'Could not load summary data';
        this.loadingSummary = false;
      }
    });
  }

  // ---------------- Records & filters ----------------
  /**
   * Fetch paginated account records using the current
   * filter and pagination state
   */
  loadRecords(): void {
    this.recordsLoading = true;
    this.recordsError = undefined;

    // Convert empty filters to undefined for cleaner API calls
    const status = this.filterStatus || undefined;
    const minHealth = this.filterMinHealth != null ? this.filterMinHealth : undefined;
    const search = this.filterSearch || undefined;

    this.appService
      .getRecords(this.page, this.pageSize, status, minHealth, search)
      .subscribe({
        next: (resp: PaginatedRecordsResponse) => {
          this.records = resp.items;
          this.totalPages = resp.total_pages;
          this.recordsLoading = false;

          // Update dependent chart after records load
          this.updateTopAccountsChart();
        },
        error: (err) => {
          console.error('Error loading records', err);
          this.recordsError = 'Could not load account records';
          this.recordsLoading = false;
        }
      });
  }
  
  /**
   * Apply current filters and reset pagination
   */
  applyFilters(): void {
    this.page = 1;
    this.loadRecords();
  }

  /**
   * Reset all filters back to default values
   */
  clearFilters(): void {
    this.filterStatus = '';
    this.filterMinHealth = undefined;
    this.filterSearch = '';
    this.page = 1;
    this.loadRecords();
  }

  /**
   * Navigate to the next page of records
   */
  nextPage(): void {
    if (this.page < this.totalPages) {
      this.page++;
      this.loadRecords();
    }
  }

  /**
   * Navigate to the previous page of records
   */
  prevPage(): void {
    if (this.page > 1) {
      this.page--;
      this.loadRecords();
    }
  }

  // ---------------- Charts: health by status ----------------
  /**
   * Load aggregated account counts grouped by health status
   * Used for the health distribution bar chart
   */
  loadHealthByStatus(): void {
    this.appService.getHealthByStatus().subscribe({
      next: (items: HealthByStatusItem[]) => {
        this.healthBarLabels = items.map(i => i.status);
        this.healthBarDatasets = [
          { data: items.map(i => i.account_count), label: 'Accounts' }
        ];
      },
      error: (err) => console.error('Error loading health-by-status', err)
    });
  }

  // ---------------- Charts: notifications over time ----------------
  /**
   * Load time-series data for notifications billed
   * Used for trend analysis in the line chart
   */
  loadNotificationsOverTime(): void {
    this.appService.getNotificationsOverTime().subscribe({
      next: (items: NotificationsOverTimeItem[]) => {
        this.notificationsLineLabels = items.map(i => i.date);
        this.notificationsLineDatasets = [
          { data: items.map(i => i.total_notifications_billed), label: 'Notifications Billed' }
        ];
      },
      error: (err) => console.error('Error loading notifications-over-time', err)
    });
  }

  // ---------------- Charts: top accounts by notifications billed ----------------
  /**
   * Derive the top 5 accounts (current page)
   * sorted by notifications billed
   */
  updateTopAccountsChart(): void {
    const sorted = [...this.records]
      .sort((a, b) => b.notifications_billed - a.notifications_billed)
      .slice(0, 5);

    this.topAccountsBarLabels = sorted.map(r => r.account_label);
    this.topAccountsBarDatasets = [
      { data: sorted.map(r => r.notifications_billed), label: 'Notifications Billed' }
    ];
  }
}
