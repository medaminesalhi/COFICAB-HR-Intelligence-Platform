import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-import-cv',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './import-cv.html',
  styleUrls: ['./import-cv.css']
})
export class ImportCvComponent {
  fileName: string = '';
  pdfUrl: string = '';
  safePdfUrl!: SafeResourceUrl;
  cvData: any = null;
  selectedFile!: File;
  formulaireVisible = false;
  resultatIa: any = null;

  // ✅ Formulaire IA
  critere = {
    poste: '',
    skills: '',
    location: '',
    exp_candidat: 0,
    experience: 0
  };

  metiers = [
    { label: "Data Scientist", value: "data_scientist" },
    { label: "Data Analyst", value: "data_analyst" },
    { label: "Data Engineer", value: "data_engineer" },
    { label: "ML Engineer", value: "ml_engineer" },
    { label: "DevOps Engineer", value: "devops_engineer" },
    { label: "Backend Developer", value: "backend_dev" },
    { label: "Frontend Developer", value: "frontend_dev" },
    { label: "Full Stack Developer", value: "fullstack_dev" },
    { label: "Cloud Engineer", value: "cloud_engineer" },
    { label: "BI Analyst", value: "bi_analyst" },
    { label: "QA Engineer", value: "qa_engineer" },
    { label: "Scrum Master", value: "scrum_master" },
    { label: "Architecte Logiciel", value: "software_architect" },
    { label: "Admin Systèmes & Réseaux", value: "sysadmin" },
    { label: "Ingénieur Sécurité", value: "cybersecurity_engineer" }
  ];

  competenceParPoste: { [key: string]: string[] } = {
    data_scientist: ["python", "pandas", "scikit-learn", "matplotlib", "sql"],
    data_analyst: ["sql", "excel", "power bi", "tableau", "python"],
    data_engineer: ["spark", "hadoop", "airflow", "python", "etl"],
    ml_engineer: ["tensorflow", "keras", "scikit-learn", "mlflow", "python"],
    devops_engineer: ["docker", "kubernetes", "ansible", "jenkins", "terraform"],
    backend_dev: ["java", "python", "node.js", "sql", "spring boot"],
    frontend_dev: ["html", "css", "javascript", "react", "vue.js"],
    fullstack_dev: ["javascript", "node.js", "react", "sql", "mongodb"],
    cloud_engineer: ["aws", "azure", "gcp", "terraform", "devops"],
    bi_analyst: ["power bi", "tableau", "sql", "dashboards", "etl"],
    qa_engineer: ["selenium", "cypress", "postman", "jira", "test automation"],
    scrum_master: ["agile", "scrum", "kanban", "jira", "planning"],
    software_architect: ["uml", "microservices", "architecture logicielle", "design patterns", "java"],
    sysadmin: ["linux", "windows server", "bash", "ssh", "networking"],
    cybersecurity_engineer: ["nmap", "firewall", "kali linux", "wireshark", "encryption"]
  };

  competencesAssociees: string[] = [];

  constructor(private http: HttpClient, private sanitizer: DomSanitizer) {}

  // 📄 Gestion du fichier CV
  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (!file) return;

    this.fileName = file.name;
    this.selectedFile = file;
    this.pdfUrl = URL.createObjectURL(file);
    this.safePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.pdfUrl);
    console.log("📄 URL du PDF :", this.pdfUrl);
  }

  resetFichier() {
    this.fileName = '';
    this.pdfUrl = '';
    this.safePdfUrl = '' as any;
    this.cvData = null;
    this.selectedFile = undefined!;
  }

  // 🔍 Scraper contenu du CV
  scraperCv() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('cv', this.selectedFile);

    this.http.post<any>('http://localhost:5000/api/scrape_cv', formData).subscribe({
      next: (res) => {
        console.log("✅ Données scrappées :", res);
        this.cvData = res;
      },
      error: (err) => {
        console.error("❌ Erreur scraping :", err);
      }
    });
  }

  // 💾 Enregistrement profil
  enregistrerProfil() {
    this.http.post('http://localhost:5000/api/save_profile', this.cvData).subscribe({
      next: () => {
        alert("✅ Profil enregistré !");
        this.formulaireVisible = true;
      },
      error: (err) => console.error("❌ Erreur d'enregistrement :", err)
    });
  }

  // 🧠 Tester le profil par IA
  testerIaProfil() {
    let competences_cleaned = this.cvData.competences;
    if (typeof competences_cleaned === 'string') {
      competences_cleaned = competences_cleaned
        .split(/[,;\n]/)
        .map(c => c.trim())
        .filter(c => c.length > 1);
    }

    const payload = {
      candidat: {
        ...this.cvData,
        competences: competences_cleaned,
        experience: this.critere.exp_candidat  // 👈 injecte l’expérience réelle ici
      },
      criteres: {
        poste: this.critere.poste,
        skills: this.critere.skills,
        location: this.critere.location,
        experience: this.critere.experience
      }
    };

    this.http.post<any>('http://localhost:5000/api/predict_match', payload).subscribe({
      next: (res) => {
        this.resultatIa = res;
      },
      error: (err) => {
        console.error("❌ Erreur IA :", err);
        alert("Erreur lors de l'évaluation IA.");
      }
    });
  }

  // 🔁 Quand le recruteur change de poste
  mettreAJourCompetences() {
    this.competencesAssociees = this.competenceParPoste[this.critere.poste] || [];
    this.critere.skills = "";
  }

  // 🔘 Gestion des cases à cocher des compétences
  mettreAJourSkills(event: any) {
    const value = event.target.value;
    if (event.target.checked) {
      this.critere.skills += value + ", ";
    } else {
      this.critere.skills = this.critere.skills.replace(value + ", ", "");
    }
  }
}
