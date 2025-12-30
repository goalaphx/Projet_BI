// src/main.ts

import 'zone.js';  // <--- ADD THIS LINE AT THE TOP!
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app'; // Or './app/app.component' depending on your naming

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));