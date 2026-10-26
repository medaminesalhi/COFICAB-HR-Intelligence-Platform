import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-recherche',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    RouterModule
  ],
  templateUrl: './recherche.html',
  styleUrls: ['./recherche.css']
})
export class RechercheComponent implements OnInit {

  // ✅ Formulaire de filtre
  filtre = {
    nom: '',
    jobtitle: '',
    location: '',
    schooldegree: '',
    score: 0,
    recommande: false,
    skills: [] as string[]  // ✅ Compétences cochées
  };

  resultats: any[] = [];
  metiers: string[] = [];
  diplomes: string[] = [];

  // ✅ Liste de compétences dynamiques selon le métier
  competencesDispo: string[] = [];

  // ✅ Dictionnaire des métiers → compétences
  skillsMap: { [job: string]: string[] } = {
  "AI Engineer": ["Deep Learning", "ML Models", "MLOps", "NLP", "Python", "TensorFlow", "Transformers"],
  "BI Analyst": ["Data Modeling", "Data Warehouse", "DAX", "ETL", "Excel", "Power BI", "SQL", "Tableau"],
  "Backend Developer": ["Docker", "Go", "Java", "Node.js", "PostgreSQL", "Python", "Spring Boot"],
  "Chargé RH": ["Communication", "Droit du Travail", "Gestion Administrative", "Onboarding", "Recrutement", "Reporting RH"],
  "Cloud Engineer": ["AWS", "Azure", "Docker", "GCP", "Kubernetes", "Linux", "Networking", "Terraform"],
  "Consultant RH": ["Analyse de Besoins", "Audit RH", "Coaching", "Formation", "Gestion du Changement", "SIRH"],
  "Cybersecurity Analyst": ["Firewalls", "ISO27001", "Penetration Testing", "Python", "SIEM", "SOC"],
  "Data Analyst": ["Data Cleaning", "Data Viz", "Excel", "Power BI", "Python", "SQL", "Tableau"],
  "Data Engineer": ["Airflow", "AWS", "BigQuery", "Docker", "ETL", "Kafka", "Linux", "Python", "SQL", "Spark"],
  "Data Scientist": ["Deep Learning", "MLflow", "NLP", "Pandas", "Python", "R", "SQL", "TensorFlow"],
  "DevOps Engineer": ["AWS", "CI/CD", "Docker", "Git", "Jenkins", "Kubernetes", "Linux", "Prometheus", "Terraform"],
  "Frontend Developer": ["Bootstrap", "CSS", "Figma", "HTML", "JavaScript", "React", "UI/UX", "Vue.js"],
  "Full Stack Developer": ["CSS", "Docker", "Express.js", "HTML", "JavaScript", "MongoDB", "Node.js", "React", "TypeScript"],
  "IT Support Specialist": ["Active Directory", "Help Desk", "ITIL", "Networking", "Windows Server"],
  "Machine Learning Engineer": ["Docker", "GCP", "ML Pipelines", "MLOps", "Python", "PyTorch", "Sklearn", "TensorFlow"],
  "Mobile Developer": ["Dart", "Firebase", "Flutter", "Git", "Kotlin", "React Native", "Swift"],
  "Responsable Recrutement": ["ATS", "Entretien Structuré", "Marque Employeur", "Onboarding", "Stratégie Sourcing"],
  "Responsable formation": ["Animation", "Gestion de Budget", "LMS", "Plan de Formation", "Évaluation"],
  "Software Tester": ["Bug Tracking", "CI/CD", "JIRA", "JUnit", "Postman", "Selenium", "Test Automation"],
  "Stagiaire RH": ["Entretiens", "Excel", "Sourcing", "Suivi de Dossiers", "Support Administratif"]
};

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.chargerMetiers();
    this.chargerDiplomes();
  }

  // 🔎 Recherche
  rechercher(): void {
    const headers = this.getAuthHeaders();
    this.http.post<any>('http://localhost:5000/api/recherche-profils', this.filtre, { headers }).subscribe({
      next: (response) => {
        this.resultats = response.profils;
      },
      error: (err) => {
        console.error('❌ Erreur lors de la recherche', err);
      }
    });
  }

  // ♻️ Réinitialisation
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
  }

  // 📥 Charger métiers depuis backend
  chargerMetiers(): void {
    const headers = this.getAuthHeaders();
    this.http.get<any>('http://localhost:5000/api/metiers', { headers }).subscribe({
      next: (data) => this.metiers = data.metiers || [],
      error: (err) => console.error('❌ Erreur chargement métiers', err)
    });
  }
  

  // 📥 Charger diplômes depuis backend
  chargerDiplomes(): void {
    const headers = this.getAuthHeaders();
    this.http.get<any>('http://localhost:5000/api/diplomes', { headers }).subscribe({
      next: (data) => this.diplomes = data.diplomes || [],
      error: (err) => console.error('❌ Erreur chargement diplômes', err)
    });
  }

  // 🔁 Mise à jour des compétences selon le métier sélectionné
  onJobChange(): void {
    this.competencesDispo = this.skillsMap[this.filtre.jobtitle] || [];
    this.filtre.skills = [];
  }

  // 🔐 Auth headers
  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      Authorization: `Bearer ${token}`
    });
  }
  // 🔘 Gestion manuelle des checkbox de skills
mettreAJourSkills(event: any, skill: string): void {
  if (event.target.checked) {
    if (!this.filtre.skills.includes(skill)) {
      this.filtre.skills.push(skill);
    }
  } else {
    this.filtre.skills = this.filtre.skills.filter(s => s !== skill);
  }
}

}
