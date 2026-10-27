import { isPlatformBrowser } from '@angular/common';
import { inject, PLATFORM_ID } from '@angular/core';
import { HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { API_BASE_URL } from './api-url';

/** Ajoute le JWT aux appels API et redirige en cas de session expirée. */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const platformId = inject(PLATFORM_ID);
  const router = inject(Router);
  const isBrowser = isPlatformBrowser(platformId);
  const isApiRequest = request.url.startsWith(API_BASE_URL + '/');
  const isLoginRequest = request.url === `${API_BASE_URL}/login`;

  const token = isBrowser && isApiRequest && !isLoginRequest
    ? localStorage.getItem('token')
    : null;

  const outgoingRequest = token
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  return next(outgoingRequest).pipe(
    catchError((error: unknown) => {
      const status = (error as { status?: number })?.status;
      if (isBrowser && isApiRequest && !isLoginRequest && status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user_nom');
        void router.navigate(['/login']);
      }
      return throwError(() => error);
    }),
  );
};
