import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms'; // ⬅️ Ajouté ici !

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    FormsModule // ⬅️ Nécessaire pour ngModel
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'projet';
}
