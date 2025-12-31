import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app'; // Make sure this path is correct
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(), // FIX: Provides HttpClient for your ApiService
    provideAnimations()  // FIX: Helps with amCharts animations
  ]
}).catch(err => console.error(err));