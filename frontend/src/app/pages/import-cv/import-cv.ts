import { Component, afterNextRender, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { API_BASE_URL } from '../../core/api-url';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-import-cv',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './import-cv.html',
  styleUrls: ['./import-cv.css']
})
export class ImportCvComponent implements OnDestroy {
  readonly isBrowser = signal(false);

  nomUtilisateur = '';
  fileName = '';
  pdfUrl = '';
  safePdfUrl: SafeResourceUrl | null = null;
  cvData: any = null;
  selectedFile?: File;
  formulaireVisible = false;
  resultatIa: any = null;

  isScraping = false;
  isSaving = false;
  isEvaluating = false;
  errorMessage = '';
  successMessage = '';

  critere = {
    poste: '',
    skills: '',
    location: '',
    exp_candidat: 0,
    experience: 0
  };

  metiers = [
    { label: 'Data Scientist', value: 'data_scientist' },
    { label: 'Data Analyst', value: 'data_analyst' },
    { label: 'Data Engineer', value: 'data_engineer' },
    { label: 'ML Engineer', value: 'ml_engineer' },
    { label: 'DevOps Engineer', value: 'devops_engineer' },
    { label: 'Backend Developer', value: 'backend_dev' },
    { label: 'Frontend Developer', value: 'frontend_dev' },
    { label: 'Full Stack Developer', value: 'fullstack_dev' },
    { label: 'Cloud Engineer', value: 'cloud_engineer' },
    { label: 'BI Analyst', value: 'bi_analyst' },
    { label: 'QA Engineer', value: 'qa_engineer' },
    { label: 'Scrum Master', value: 'scrum_master' },
    { label: 'Architecte Logiciel', value: 'software_architect' },
    { label: 'Admin Systèmes & Réseaux', value: 'sysadmin' },
    { label: 'Ingénieur Sécurité', value: 'cybersecurity_engineer' }
  ];

  competenceParPoste: { [key: string]: string[] } = {
    data_scientist: ['python', 'pandas', 'scikit-learn', 'matplotlib', 'sql'],
    data_analyst: ['sql', 'excel', 'power bi', 'tableau', 'python'],
    data_engineer: ['spark', 'hadoop', 'airflow', 'python', 'etl'],
    ml_engineer: ['tensorflow', 'keras', 'scikit-learn', 'mlflow', 'python'],
    devops_engineer: ['docker', 'kubernetes', 'ansible', 'jenkins', 'terraform'],
    backend_dev: ['java', 'python', 'node.js', 'sql', 'spring boot'],
    frontend_dev: ['html', 'css', 'javascript', 'react', 'vue.js'],
    fullstack_dev: ['javascript', 'node.js', 'react', 'sql', 'mongodb'],
    cloud_engineer: ['aws', 'azure', 'gcp', 'terraform', 'devops'],
    bi_analyst: ['power bi', 'tableau', 'sql', 'dashboards', 'etl'],
    qa_engineer: ['selenium', 'cypress', 'postman', 'jira', 'test automation'],
    scrum_master: ['agile', 'scrum', 'kanban', 'jira', 'planning'],
    software_architect: ['uml', 'microservices', 'architecture logicielle', 'design patterns', 'java'],
    sysadmin: ['linux', 'windows server', 'bash', 'ssh', 'networking'],
    cybersecurity_engineer: ['nmap', 'firewall', 'kali linux', 'wireshark', 'encryption']
  };

  competencesAssociees: string[] = [];

  get initialeUtilisateur(): string {
    const nom = this.nomUtilisateur.trim();
    return nom ? nom.charAt(0).toUpperCase() : 'U';
  }

  get isPdfSelected(): boolean {
    return !!this.selectedFile && this.selectedFile.name.toLowerCase().endsWith('.pdf');
  }

  constructor(
    private readonly http: HttpClient,
    private readonly sanitizer: DomSanitizer,
    private readonly router: Router
  ) {
    // Accès au stockage uniquement dans le navigateur, jamais pendant le SSR.
    afterNextRender(() => {
      this.isBrowser.set(true);
      this.nomUtilisateur = localStorage.getItem('user_nom') || '';
    });
  }

  ngOnDestroy(): void {
    this.releasePdfUrl();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.pdf')) {
      this.releasePdfUrl();
      this.selectedFile = undefined;
      this.fileName = '';
      this.cvData = null;
      this.formulaireVisible = false;
      this.resultatIa = null;
      this.successMessage = '';
      this.safePdfUrl = null;
      this.errorMessage = 'Format non pris en charge. Sélectionnez un fichier PDF.';
      input.value = '';
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.releasePdfUrl();
      this.selectedFile = undefined;
      this.fileName = '';
      this.cvData = null;
      this.formulaireVisible = false;
      this.resultatIa = null;
      this.successMessage = '';
      this.safePdfUrl = null;
      this.errorMessage = 'Le fichier dépasse la limite de 10 Mo.';
      input.value = '';
      return;
    }

    this.releasePdfUrl();
    this.selectedFile = file;
    this.fileName = file.name;
    this.cvData = null;
    this.formulaireVisible = false;
    this.resultatIa = null;
    this.errorMessage = '';
    this.successMessage = '';

    if (lowerName.endsWith('.pdf')) {
      this.pdfUrl = URL.createObjectURL(file);
      this.safePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.pdfUrl);
    }
  }

  resetFichier(fileInput?: HTMLInputElement): void {
    this.releasePdfUrl();
    this.fileName = '';
    this.selectedFile = undefined;
    this.cvData = null;
    this.formulaireVisible = false;
    this.resultatIa = null;
    this.errorMessage = '';
    this.successMessage = '';
    this.safePdfUrl = null;
    if (fileInput) fileInput.value = '';
  }

  private releasePdfUrl(): void {
    if (this.pdfUrl) URL.revokeObjectURL(this.pdfUrl);
    this.pdfUrl = '';
    this.safePdfUrl = null;
  }

  scraperCv(): void {
    if (!this.selectedFile || this.isScraping) return;

    this.errorMessage = '';
    this.successMessage = '';
    this.isScraping = true;

    const formData = new FormData();
    formData.append('cv', this.selectedFile);

    this.http.post<any>(`${API_BASE_URL}/scrape_cv`, formData).subscribe({
      next: (res) => {
        this.isScraping = false;
        this.cvData = res ?? {};
        if (Array.isArray(this.cvData.competences)) {
          this.cvData.competences = this.cvData.competences.join(', ');
        }
        this.successMessage = 'Extraction terminée. Vérifiez les informations avant de les enregistrer.';
      },
      error: (err) => {
        console.error('Erreur lors de l’extraction du CV :', err);
        this.isScraping = false;
        this.errorMessage = err?.error?.message || 'L’extraction a échoué. Vérifiez que le backend est démarré et réessayez.';
      }
    });
  }

  enregistrerProfil(): void {
    if (!this.cvData || this.isSaving) return;

    this.errorMessage = '';
    this.successMessage = '';
    this.isSaving = true;

    this.http.post<any>(`${API_BASE_URL}/save_profile`, this.cvData).subscribe({
      next: () => {
        this.isSaving = false;
        this.successMessage = 'Profil enregistré avec succès. Vous pouvez maintenant lancer l’évaluation IA.';
        this.formulaireVisible = true;
      },
      error: (err) => {
        console.error('Erreur lors de l’enregistrement du profil :', err);
        this.isSaving = false;
        this.errorMessage = err?.error?.message || 'Impossible d’enregistrer le profil. Vérifiez le backend.';
      }
    });
  }

  testerIaProfil(): void {
    if (!this.cvData || this.isEvaluating) return;

    this.errorMessage = '';
    this.successMessage = '';
    this.resultatIa = null;
    this.isEvaluating = true;

    let competencesCleaned: string[] = [];
    if (Array.isArray(this.cvData.competences)) {
      competencesCleaned = this.cvData.competences;
    } else if (typeof this.cvData.competences === 'string') {
      competencesCleaned = this.cvData.competences
        .split(/[,;\n]/)
        .map((competence: string) => competence.trim())
        .filter((competence: string) => competence.length > 1);
    }

    const payload = {
      candidat: {
        ...this.cvData,
        competences: competencesCleaned,
        experience: this.critere.exp_candidat
      },
      criteres: {
        poste: this.critere.poste,
        skills: this.critere.skills,
        location: this.critere.location,
        experience: this.critere.experience
      }
    };

    this.http.post<any>(`${API_BASE_URL}/predict_match`, payload).subscribe({
      next: (res) => {
        this.isEvaluating = false;
        this.resultatIa = res;
      },
      error: (err) => {
        console.error('Erreur lors de l’évaluation IA :', err);
        this.isEvaluating = false;
        this.errorMessage = err?.error?.message || 'L’évaluation IA a échoué. Vérifiez que le service est disponible.';
      }
    });
  }

  isSkillSelected(skill: string): boolean {
    return this.critere.skills.split(',').map((item) => item.trim()).includes(skill);
  }

  mettreAJourCompetences(): void {
    this.competencesAssociees = this.competenceParPoste[this.critere.poste] || [];
    this.critere.skills = '';
  }

  mettreAJourSkills(event: Event): void {
    const checkbox = event.target as HTMLInputElement;
    const value = checkbox.value;
    const selected = this.critere.skills
      .split(',')
      .map((skill) => skill.trim())
      .filter(Boolean);

    if (checkbox.checked && !selected.includes(value)) {
      selected.push(value);
    } else if (!checkbox.checked) {
      const index = selected.indexOf(value);
      if (index >= 0) selected.splice(index, 1);
    }

    this.critere.skills = selected.join(', ');
  }

  deconnexion(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user_nom');
    void this.router.navigate(['/login']);
  }
}
