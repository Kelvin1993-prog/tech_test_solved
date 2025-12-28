import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SummaryResponse {
  total_accounts: number;
  active_accounts: number;
  inactive_accounts: number;
  total_notifications_billed: number;
  avg_notifications_billed_per_active: number;
  total_messages_processed: number;
  avg_messages_per_account: number;
  avg_health_score: number;
  at_risk_accounts: number;
  churned_accounts: number;
}

export interface AccountInsights {
  account_label: string;
  subscription_status: string;
  health_score: number;
  automation_count: number;
  total_records: number;
  messages_processed: number;
  notifications_billed: number;
  churn_risk: string;
}

export interface PaginatedRecordsResponse {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  items: AccountInsights[];
}

export interface HealthByStatusItem {
  status: string;
  account_count: number;
}

export interface NotificationsOverTimeItem {
  date: string;
  total_notifications_billed: number;
}

@Injectable({
  providedIn: 'root'
})
export class AppService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getSummary(): Observable<SummaryResponse> {
    return this.http.get<SummaryResponse>(`${this.baseUrl}/summary`);
  }

  getRecords(
    page: number,
    pageSize: number,
    status?: string,
    minHealth?: number,
    search?: string
  ): Observable<PaginatedRecordsResponse> {
    let params = new HttpParams()
      .set('page', page)
      .set('page_size', pageSize);

    if (status) params = params.set('status', status);
    if (minHealth != null) params = params.set('min_health', minHealth);
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedRecordsResponse>(`${this.baseUrl}/records`, { params });
  }

  getHealthByStatus(): Observable<HealthByStatusItem[]> {
    return this.http.get<HealthByStatusItem[]>(`${this.baseUrl}/analytics/health-by-status`);
  }

  getNotificationsOverTime(): Observable<NotificationsOverTimeItem[]> {
    return this.http.get<NotificationsOverTimeItem[]>(`${this.baseUrl}/analytics/notifications-over-time`);
  }
}
