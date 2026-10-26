
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

  // Le rendu des graphiques est réservé au navigateur.
  readonly isBrowser = signal(false);

  nomUtilisateur = '';
  donneesChargees = false;

  totalProfils = 0;
  nbRecommandes = 0;
  moyenneScore = 0;

  nouveauxProfils: any[] = [];

  // Initiale affichée dans l'avatar de la barre supérieure.
  get initialeUtilisateur(): string {
    const nom = this.nomUtilisateur.trim();

    return nom ? nom.charAt(0).toUpperCase() : 'U';
  }

  // Palette cohérente avec l'identité visuelle COFICAB.
  private readonly palette = [
    '#2589C3',
    '#2DA88A',
    '#E9AD43',
    '#7662C9',
    '#E66D70',
    '#5BABC7',
    '#83B86B',
    '#D58D55',
    '#5276A5',
    '#A2B4C3'
  ];

  // 1. Top métiers
  topMetiersChartData: ChartData<'bar'> = {
    labels: [],
    datasets: []
  };

  topMetiersOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          maxRotation: 35,
          minRotation: 0
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: '#edf1f5'
        },
        ticks: {
          precision: 0
        }
      }
    }
  };

  // 2. Répartition géographique
  villesChartData: ChartData<'pie'> = {
    labels: [],
    datasets: []
  };

  villesOptions: ChartOptions<'pie'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 10,
          padding: 12,
          usePointStyle: true
        }
      }
    }
  };

  // 3. Niveau d'études
  etudesChartData: ChartData<'doughnut'> = {
    labels: [],
    datasets: []
  };

  etudesOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 10,
          padding: 10,
          usePointStyle: true
        }
      }
    }
  };

  // 4. Top compétences
  skillsData: ChartData<'bar'> = {
    labels: [],
    datasets: []
  };

  skillsOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: '#edf1f5'
        },
        ticks: {
          precision: 0
        }
      }
    }
  };

  // 5. Compétences par métier
  skillsPerJobData: ChartData<'bar'> = {
    labels: [],
    datasets: []
  };

  skillsPerJobOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        display: false
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        grid: {
          color: '#edf1f5'
        },
        ticks: {
          precision: 0
        }
      },
      y: {
        grid: {
          display: false
        }
      }
    }
  };

  constructor(
    private readonly http: HttpClient,
    private readonly cdr: ChangeDetectorRef
  ) {
    // Exécuté après le rendu initial dans le navigateur,
    // pas pendant le rendu serveur.
    afterNextRender(() => {
      this.isBrowser.set(true);
      this.chargerDashboard();
    });
  }

  private chargerDashboard(): void {
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
        console.log('Données du dashboard reçues :', res);
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
    // Indicateurs principaux
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

    // Sécurisation des données reçues du backend
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
    this.topMetiersChartData = {
      labels: topMetiers.map(
        (m: any) => String(m?.jobtitle ?? 'Non renseigné')
      ),
      datasets: [
        {
          label: 'Profils',
          data: topMetiers.map(
            (m: any) => Number(m?.total ?? 0)
          ),
          backgroundColor: this.generateColors(topMetiers.length),
          borderRadius: 6,
          borderSkipped: false
        }
      ]
    };

    // 2. Répartition géographique
    this.villesChartData = {
      labels: villes.map(
        (v: any) => String(v?.location ?? 'Non renseigné')
      ),
      datasets: [
        {
          label: 'Profils par ville',
          data: villes.map(
            (v: any) => Number(v?.total ?? 0)
          ),
          backgroundColor: this.generateColors(villes.length),
          borderColor: '#ffffff',
          borderWidth: 2
        }
      ]
    };

    // 3. Niveau d'études
    this.etudesChartData = {
      labels: etudes.map(
        (e: any) => String(e?.schooldegree ?? 'Non renseigné')
      ),
      datasets: [
        {
          label: 'Profils par niveau d’études',
          data: etudes.map(
            (e: any) => Number(e?.total ?? 0)
          ),
          backgroundColor: this.generateColors(etudes.length),
          borderColor: '#ffffff',
          borderWidth: 2
        }
      ]
    };

    // 4. Top compétences
    this.skillsData = {
      labels: topSkills.map(
        (s: any) => String(s?.skill ?? 'Non renseigné')
      ),
      datasets: [
        {
          label: 'Occurrences',
          data: topSkills.map(
            (s: any) => Number(s?.count ?? 0)
          ),
          backgroundColor: this.generateColors(topSkills.length),
          borderRadius: 5,
          borderSkipped: false
        }
      ]
    };

    // 5. Compétences par métier
    const skillsEntries = skillsPerJob.flatMap(
      (job: any) => {
        const skills = Array.isArray(job?.skills)
          ? job.skills
          : [];

        return skills.map((skill: any) => ({
          label: `${job?.job ?? 'Métier'} — ${
            skill?.skill ?? 'Compétence'
          }`,
          count: Number(skill?.count ?? 0)
        }));
      }
    );

    this.skillsPerJobData = {
      labels: skillsEntries.map(
        (entry: any) => entry.label
      ),
      datasets: [
        {
          label: 'Occurrences',
          data: skillsEntries.map(
            (entry: any) => entry.count
          ),
          backgroundColor: this.generateColors(
            skillsEntries.length
          ),
          borderRadius: 4,
          borderSkipped: false
        }
      ]
    };

    this.donneesChargees = true;
    this.cdr.markForCheck();
  }

  private generateColors(n: number): string[] {
    return Array.from(
      { length: n },
      (_, index) => this.palette[index % this.palette.length]
    );
  }

  deconnexion(): void {
    localStorage.clear();
    window.location.href = '/login';
  }
}
