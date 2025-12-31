import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

// Define Types for API responses to ensure type safety
export interface FilterOptions {
  years: string[];
  countries: string[];
}

export interface KPIData {
  total_pubs: number;
  total_citations: number;
  avg_impact: number;
  total_authors: number;
}

export interface DataPoint {
  _id: string | number;
  count?: number;
  value?: number;
  text?: string;
  weight?: number;
}

export interface NetworkData {
  nodes: Array<{ id: string, value: number }>;
  links: Array<{ source: string, target: string }>;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) { }

  private getParams(year: string, country: string): HttpParams {
    let params = new HttpParams();
    if (year && year !== 'All') params = params.set('year', year);
    if (country && country !== 'All') params = params.set('country', country);
    return params;
  }

  getFilterOptions(): Observable<FilterOptions> {
    return this.http.get<FilterOptions>(`${this.baseUrl}/filters/options`);
  }

  getSummaryKPI(year: string = 'All', country: string = 'All'): Observable<KPIData> {
    return this.http.get<KPIData>(`${this.baseUrl}/kpi/summary`, { params: this.getParams(year, country) });
  }

  getTimeStats(year: string, country: string): Observable<DataPoint[]> {
    return this.http.get<DataPoint[]>(`${this.baseUrl}/olap/time_distribution`, { params: this.getParams(year, country) });
  }

  getGeoStats(year: string, country: string): Observable<DataPoint[]> {
    return this.http.get<DataPoint[]>(`${this.baseUrl}/olap/geo_distribution`, { params: this.getParams(year, country) });
  }

  getQuartileStats(year: string, country: string): Observable<DataPoint[]> {
    return this.http.get<DataPoint[]>(`${this.baseUrl}/olap/quality_quartile`, { params: this.getParams(year, country) });
  }

  getKeywordStats(year: string, country: string): Observable<DataPoint[]> {
    return this.http.get<DataPoint[]>(`${this.baseUrl}/olap/keywords`, { params: this.getParams(year, country) });
  }

  getCoAuthorNetwork(year: string, country: string): Observable<NetworkData> {
    return this.http.get<NetworkData>(`${this.baseUrl}/olap/network`, { params: this.getParams(year, country) });
  }

  getTopAuthors(year: string, country: string): Observable<DataPoint[]> {
    return this.http.get<DataPoint[]>(`${this.baseUrl}/olap/authors`, { params: this.getParams(year, country) });
  }
}