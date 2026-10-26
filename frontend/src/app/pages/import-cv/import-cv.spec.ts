import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ImportCvComponent } from './import-cv';

describe('ImportCvComponent', () => {
  let component: ImportCvComponent;
  let fixture: ComponentFixture<ImportCvComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImportCvComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ImportCvComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
