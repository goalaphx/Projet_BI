import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) { }

  getYearStats(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/stats/years`);
  }

  getCountryStats(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/stats/countries`);
  }

  // --- NEW METHODS ---
  getQuartileStats(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/stats/quartiles`);
  }

  getKeywordStats(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/stats/keywords`);
  }
}