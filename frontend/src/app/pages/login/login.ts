import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { API_BASE_URL } from '../../core/api-url';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  email = '';
  password = '';
  errorMessage = '';
  isLoading = false;

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router
  ) {}

  login(): void {
    if (this.isLoading) return;

    const email = this.email.trim();
    if (!email || !this.password) {
      this.errorMessage = 'Veuillez renseigner votre adresse e-mail et votre mot de passe.';
      return;
    }

    this.errorMessage = '';
    this.isLoading = true;

    this.http.post<any>(`${API_BASE_URL}/login`, {
      email,
      password: this.password
    }).subscribe({
      next: (res) => {
        this.isLoading = false;

        if (res?.success && res?.token) {
          localStorage.setItem('token', res.token);
          if (res.user?.nom) {
            localStorage.setItem('user_nom', res.user.nom);
          }
          void this.router.navigate(['/dashboard']);
          return;
        }

        this.errorMessage = res?.message || 'Identifiants incorrects. Vérifiez vos informations.';
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Erreur API de connexion :', {
          status: err?.status,
          error: err?.error
        });

        if (err?.status === 0) {
          this.errorMessage = 'Le backend est inaccessible. Vérifiez que le serveur Flask fonctionne sur le port 5000.';
        } else if (err?.status >= 500) {
          this.errorMessage = 'Le serveur RH a rencontré une erreur. Consultez le terminal Flask pour identifier la cause.';
        } else if (err?.status === 401) {
          this.errorMessage = 'Adresse e-mail ou mot de passe incorrect.';
        } else {
          const apiMessage = typeof err?.error === 'object'
            ? err.error?.message
            : null;
          this.errorMessage = apiMessage || `Échec de la connexion (HTTP ${err?.status ?? 'inconnu'}).`;
        }
      }
    });
  }
}
