import { Component, afterNextRender, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-recherche',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './recherche.html',
  styleUrls: ['./recherche.css']
})
export class RechercheComponent {
  readonly isBrowser = signal(false);

  nomUtilisateur = '';
  isSearching = false;
  errorMessage = '';
  infoMessage = '';

  filtre = {
    nom: '',
    jobtitle: '',
    location: '',
    schooldegree: '',
    score: 0,
    recommande: false,
    skills: [] as string[]
  };

  resultats: any[] = [];
  metiers: string[] = [];
  diplomes: string[] = [];
  competencesDispo: string[] = [];

  readonly skillsMap: { [job: string]: string[] } = {
    'AI Engineer': ['Deep Learning', 'ML Models', 'MLOps', 'NLP', 'Python', 'TensorFlow', 'Transformers'],
    'BI Analyst': ['Data Modeling', 'Data Warehouse', 'DAX', 'ETL', 'Excel', 'Power BI', 'SQL', 'Tableau'],
    'Backend Developer': ['Docker', 'Go', 'Java', 'Node.js', 'PostgreSQL', 'Python', 'Spring Boot'],
    'Chargé RH': ['Communication', 'Droit du Travail', 'Gestion Administrative', 'Onboarding', 'Recrutement', 'Reporting RH'],
    'Cloud Engineer': ['AWS', 'Azure', 'Docker', 'GCP', 'Kubernetes', 'Linux', 'Networking', 'Terraform'],
    'Consultant RH': ['Analyse de Besoins', 'Audit RH', 'Coaching', 'Formation', 'Gestion du Changement', 'SIRH'],
    'Cybersecurity Analyst': ['Firewalls', 'ISO27001', 'Penetration Testing', 'Python', 'SIEM', 'SOC'],
    'Data Analyst': ['Data Cleaning', 'Data Viz', 'Excel', 'Power BI', 'Python', 'SQL', 'Tableau'],
    'Data Engineer': ['Airflow', 'AWS', 'BigQuery', 'Docker', 'ETL', 'Kafka', 'Linux', 'Python', 'SQL', 'Spark'],
    'Data Scientist': ['Deep Learning', 'MLflow', 'NLP', 'Pandas', 'Python', 'R', 'SQL', 'TensorFlow'],
    'DevOps Engineer': ['AWS', 'CI/CD', 'Docker', 'Git', 'Jenkins', 'Kubernetes', 'Linux', 'Prometheus', 'Terraform'],
    'Frontend Developer': ['Bootstrap', 'CSS', 'Figma', 'HTML', 'JavaScript', 'React', 'UI/UX', 'Vue.js'],
    'Full Stack Developer': ['CSS', 'Docker', 'Express.js', 'HTML', 'JavaScript', 'MongoDB', 'Node.js', 'React', 'TypeScript'],
    'IT Support Specialist': ['Active Directory', 'Help Desk', 'ITIL', 'Networking', 'Windows Server'],
    'Machine Learning Engineer': ['Docker', 'GCP', 'ML Pipelines', 'MLOps', 'Python', 'PyTorch', 'Sklearn', 'TensorFlow'],
    'Mobile Developer': ['Dart', 'Firebase', 'Flutter', 'Git', 'Kotlin', 'React Native', 'Swift'],
    'Responsable Recrutement': ['ATS', 'Entretien Structuré', 'Marque Employeur', 'Onboarding', 'Stratégie Sourcing'],
    'Responsable formation': ['Animation', 'Gestion de Budget', 'LMS', 'Plan de Formation', 'Évaluation'],
    'Software Tester': ['Bug Tracking', 'CI/CD', 'JIRA', 'JUnit', 'Postman', 'Selenium', 'Test Automation'],
    'Stagiaire RH': ['Entretiens', 'Excel', 'Sourcing', 'Suivi de Dossiers', 'Support Administratif']
  };

  get initialeUtilisateur(): string {
    const nom = this.nomUtilisateur.trim();
    return nom ? nom.charAt(0).toUpperCase() : 'U';
  }

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router
  ) {
    // Le stockage navigateur et les appels API sont lancés après le rendu client.
    afterNextRender(() => {
      this.isBrowser.set(true);
      this.nomUtilisateur = localStorage.getItem('user_nom') || '';
      this.chargerMetiers();
      this.chargerDiplomes();
    });
  }

  rechercher(): void {
    if (this.isSearching) return;

    this.errorMessage = '';
    this.infoMessage = '';
    this.isSearching = true;

    const headers = this.getAuthHeaders();
    this.http.post<any>(
      'http://localhost:5000/api/recherche-profils',
      this.filtre,
      { headers }
    ).subscribe({
      next: (response) => {
        const profils = Array.isArray(response?.profils) ? response.profils : [];
        this.resultats = profils.map((profil: any) => {
          const rawSkills = profil?.competences ?? profil?.skills ?? [];
          const competences = Array.isArray(rawSkills)
            ? rawSkills
            : typeof rawSkills === 'string'
              ? rawSkills.split(/[,;\n]/).map((s: string) => s.trim()).filter(Boolean)
              : [];
          return { ...profil, competences };
        });
        if (!this.resultats.length) {
          this.infoMessage = 'Aucun profil ne correspond aux critères sélectionnés.';
        }
        this.isSearching = false;
      },
      error: (err) => {
        console.error('Erreur lors de la recherche des profils :', err);
        this.errorMessage = err?.error?.message || 'La recherche a échoué. Vérifiez votre connexion au serveur.';
        this.isSearching = false;
      }
    });
  }

  reset(): void {
    this.filtre = {
      nom: '',
      jobtitle: '',
      location: '',
      schooldegree: '',
      score: 0,
      recommande: false,
      skills: []
    };
    this.resultats = [];
    this.competencesDispo = [];
    this.errorMessage = '';
    this.infoMessage = '';
  }

  chargerMetiers(): void {
    this.http.get<any>(
      'http://localhost:5000/api/metiers',
      { headers: this.getAuthHeaders() }
    ).subscribe({
      next: (data) => {
        this.metiers = Array.isArray(data?.metiers) ? data.metiers : [];
      },
      error: (err) => {
        console.error('Erreur lors du chargement des métiers :', err);
      }
    });
  }

  chargerDiplomes(): void {
    this.http.get<any>(
      'http://localhost:5000/api/diplomes',
      { headers: this.getAuthHeaders() }
    ).subscribe({
      next: (data) => {
        this.diplomes = Array.isArray(data?.diplomes) ? data.diplomes : [];
      },
      error: (err) => {
        console.error('Erreur lors du chargement des diplômes :', err);
      }
    });
  }

  onJobChange(): void {
    this.competencesDispo = this.skillsMap[this.filtre.jobtitle] || [];
    this.filtre.skills = [];
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  mettreAJourSkills(event: Event, skill: string): void {
    const checkbox = event.target as HTMLInputElement;
    if (checkbox.checked) {
      if (!this.filtre.skills.includes(skill)) {
        this.filtre.skills = [...this.filtre.skills, skill];
      }
    } else {
      this.filtre.skills = this.filtre.skills.filter((item) => item !== skill);
    }
  }

  deconnexion(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user_nom');
    void this.router.navigate(['/login']);
  }
}
