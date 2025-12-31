import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Dashboard } from './dashboard/dashboard'; // Check path

@Component({
  selector: 'app-root',
  standalone: true, // <--- CRITICAL: Must be true
  imports: [CommonModule, Dashboard], // Import your Dashboard here
  template: `
    <app-dashboard></app-dashboard>
  `,
  styleUrls: ['./app.css']
})
export class AppComponent {
  title = 'S4_Dashboard';
}