"""Modèles SQLAlchemy correspondant au schéma PostgreSQL existant."""
from passlib.hash import bcrypt
from extensions import db


class Recruteur(db.Model):
    __tablename__ = "recruteurs"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(255))
    role = db.Column(db.String(100))
    created_at = db.Column(db.DateTime)

    def verify_password(self, password: str) -> bool:
        """Vérifie un hash bcrypt sans exposer les détails du hash au client."""
        if not isinstance(password, str) or not self.mot_de_passe:
            return False
        try:
            return bool(bcrypt.verify(password, self.mot_de_passe))
        except (ValueError, TypeError):
            return False
