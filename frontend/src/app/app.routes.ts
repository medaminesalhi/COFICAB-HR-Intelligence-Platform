import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login'; // ✅ ligne corrigée
import { DashboardComponent } from './pages/dashboard/dashboard';
import { RechercheComponent } from './pages/recherche/recherche';
import { ImportCvComponent } from './pages/import-cv/import-cv'; // ✅ ligne à ajouter


export const routes: Routes = [
  { path: 'login', component: LoginComponent },
   { path: 'dashboard', component: DashboardComponent },
   { path: 'recherche', component: RechercheComponent },
   { path: 'import-cv', component: ImportCvComponent },
  { path: '**', redirectTo: 'login' }
];
