import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard'; // <--- 1. Import it

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, DashboardComponent], // <--- 2. Add it here
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'S4_Dashboard';
}