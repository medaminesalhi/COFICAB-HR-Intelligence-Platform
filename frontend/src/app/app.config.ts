
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection
} from '@angular/core';

import { provideRouter } from '@angular/router';

import {
  provideClientHydration,
  withEventReplay
} from '@angular/platform-browser';

import {
  provideHttpClient,
  withFetch,
  withInterceptors
} from '@angular/common/http';

import {
  provideCharts,
  withDefaultRegisterables
} from 'ng2-charts';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),

    provideZonelessChangeDetection(),

    provideRouter(routes),

    provideClientHydration(
      withEventReplay()
    ),

    provideHttpClient(
      withFetch(),
      withInterceptors([authInterceptor])
    ),

    provideCharts(
      withDefaultRegisterables()
    )
  ]
};
