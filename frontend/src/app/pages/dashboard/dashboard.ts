
import {
  Component,
  ChangeDetectorRef,
  afterNextRender,
  signal
} from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';

import type {
  ChartData,
  ChartDataset,
  ChartOptions
} from 'chart.js';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    BaseChartDirective
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent {

  // Le canvas sera créé uniquement dans le navigateur.
  readonly isBrowser = signal(false);

  nomUtilisateur = '';
  donneesChargees = false;

  totalProfils = 0;
  nbRecommandes = 0;
  moyenneScore = 0;
  nouveauxProfils: any[] = [];

  // Graphique : top métiers
  topMetiersLabels: string[] = [];
  topMetiersData: ChartDataset<'bar'>[] = [];

  // Graphique : répartition des villes
  villesLabels: string[] = [];
  villesData: ChartDataset<'pie'>[] = [];

  // Graphique : niveau d'études
  etudesLabels: string[] = [];
  etudesData: ChartDataset<'doughnut'>[] = [];

  // Graphique : top compétences
  skillsData: ChartData<'bar'> = {
    datasets: [],
    labels: []
  };

  skillsOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top'
      }
    }
  };

  // Graphique : compétences par métier
  skillsPerJobData: ChartData<'bar'> = {
    datasets: [],
    labels: []
  };

  skillsPerJobOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        position: 'top'
      }
    }
  };

  constructor(
    private readonly http: HttpClient,
    private readonly cdr: ChangeDetectorRef
  ) {
    // Ce callback ne s'exécute pas pendant le SSR.
    afterNextRender(() => {
      this.isBrowser.set(true);
      this.chargerDashboard();
    });
  }

  private chargerDashboard(): void {
    // localStorage est utilisé uniquement côté navigateur.
    const nom = localStorage.getItem('user_nom');

    if (nom) {
      this.nomUtilisateur = nom;
    }

    const token = localStorage.getItem('token');

    if (!token) {
      this.donneesChargees = true;
      this.cdr.markForCheck();
      return;
    }

    this.http.get<any>(
      'http://localhost:5000/api/dashboard',
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    ).subscribe({
      next: (res) => {
        console.log('Données reçues du backend :', res);

        this.injecterDonnees(res ?? {});
      },
      error: (err) => {
        console.error('Erreur dashboard :', err);

        this.donneesChargees = true;
        this.cdr.markForCheck();
      }
    });
  }

  private injecterDonnees(data: any): void {

    this.totalProfils = Number(
      data?.totalProfils ?? 0
    );

    this.nbRecommandes = Number(
      data?.nbRecommandes ?? 0
    );

    this.moyenneScore = Math.round(
      Number(data?.moyenneScore ?? 0) * 100
    );

    this.nouveauxProfils = Array.isArray(
      data?.nouveauxProfils
    )
      ? data.nouveauxProfils
      : [];

    const topMetiers = Array.isArray(data?.topMetiers)
      ? data.topMetiers
      : [];

    const villes = Array.isArray(data?.repartitionVilles)
      ? data.repartitionVilles
      : [];

    const etudes = Array.isArray(data?.niveauEtude)
      ? data.niveauEtude
      : [];

    const topSkills = Array.isArray(data?.topSkills)
      ? data.topSkills
      : [];

    const skillsPerJob = Array.isArray(data?.skillsPerJob)
      ? data.skillsPerJob
      : [];

    // 1. Top métiers
    this.topMetiersLabels = topMetiers.map(
      (m: any) => String(m?.jobtitle ?? 'Non renseigné')
    );

    this.topMetiersData = [
      {
        data: topMetiers.map(
          (m: any) => Number(m?.total ?? 0)
        ),
        label: 'Métiers',
        backgroundColor: this.generateColors(topMetiers.length)
      }
    ];

    // 2. Répartition géographique
    this.villesLabels = villes.map(
      (v: any) => String(v?.location ?? 'Non renseigné')
    );

    this.villesData = [
      {
        data: villes.map(
          (v: any) => Number(v?.total ?? 0)
        ),
        label: 'Villes',
        backgroundColor: this.generateColors(villes.length)
      }
    ];

    // 3. Niveau d'études
    this.etudesLabels = etudes.map(
      (e: any) => String(e?.schooldegree ?? 'Non renseigné')
    );

    this.etudesData = [
      {
        data: etudes.map(
          (e: any) => Number(e?.total ?? 0)
        ),
        label: 'Diplômes',
        backgroundColor: this.generateColors(etudes.length)
      }
    ];

    // 4. Top compétences
    this.skillsData = {
      labels: topSkills.map(
        (s: any) => String(s?.skill ?? 'Non renseigné')
      ),
      datasets: [
        {
          data: topSkills.map(
            (s: any) => Number(s?.count ?? 0)
          ),
          label: 'Compétences',
          backgroundColor: this.generateColors(topSkills.length)
        }
      ]
    };

    // 5. Compétences par métier
    const skillsEntries = skillsPerJob.flatMap(
      (job: any) => {
        const skills = Array.isArray(job?.skills)
          ? job.skills
          : [];

        return skills.map((s: any) => ({
          label: `${job?.job ?? 'Métier'} → ${
            s?.skill ?? 'Compétence'
          }`,
          count: Number(s?.count ?? 0)
        }));
      }
    );

    this.skillsPerJobData = {
      labels: skillsEntries.map(
        (entry: any) => entry.label
      ),
      datasets: [
        {
          data: skillsEntries.map(
            (entry: any) => entry.count
          ),
          label: 'Compétences/Métier',
          backgroundColor: this.generateColors(
            skillsEntries.length
          )
        }
      ]
    };

    this.donneesChargees = true;
    this.cdr.markForCheck();
  }

  private generateColors(n: number): string[] {
    return Array.from({ length: n }, () =>
      '#' + Math.floor(Math.random() * 16777215)
        .toString(16)
        .padStart(6, '0')
    );
  }

  deconnexion(): void {
    localStorage.clear();
    window.location.href = '/login';
  }
}
