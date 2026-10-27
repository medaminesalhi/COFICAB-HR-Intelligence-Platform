import { isPlatformBrowser } from '@angular/common';
import { inject, PLATFORM_ID } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

/** Protège les pages RH côté navigateur sans lire localStorage pendant le SSR. */
export const authGuard: CanActivateFn = () => {
  const platformId = inject(PLATFORM_ID);
  const router = inject(Router);

  // Le serveur rend la coquille de page ; les appels métiers sont déclenchés côté navigateur.
  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  return localStorage.getItem('token')
    ? true
    : router.createUrlTree(['/login']);
};
