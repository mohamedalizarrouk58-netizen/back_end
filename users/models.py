from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('receptioniste','Receptioniste'),
        ('manager','Manager'),
        ('technicien','Technicien'),
        ('chefstock','ChefStock'),
        ('admin','Administrateur'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    telephone = models.CharField(max_length=20, null=True, blank=True)

    # Override the groups and user_permissions to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

class Client(models.Model):
    nom_prenom = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20)
    adresse = models.TextField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom_prenom

class Materiel(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100)
    numero_serie = models.CharField(max_length=100)
    etat = models.CharField(max_length=100, default="Reçu")
    date_reception = models.DateTimeField(auto_now_add=True)


class DemandeMaintenance(models.Model):
    materiel = models.ForeignKey(Materiel, on_delete=models.CASCADE)
    receptioniste = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    manager = models.ForeignKey(User, related_name="manager_demande", on_delete=models.SET_NULL, null=True)
    priorite = models.CharField(max_length=50)
    statut = models.CharField(max_length=100, default="En attente")
    date_creation = models.DateTimeField(auto_now_add=True)

class Intervention(models.Model):
    demande = models.OneToOneField(DemandeMaintenance, on_delete=models.CASCADE)
    technicien = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=100, default="Diagnostic")

class FicheReparation(models.Model):
    intervention = models.OneToOneField(Intervention, on_delete=models.CASCADE)
    description_panne = models.TextField()
    solution = models.TextField(null=True, blank=True)
    cout_main_oeuvre = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valide_manager = models.BooleanField(default=False)

class Piece(models.Model):
    nom = models.CharField(max_length=200)
    quantite_stock = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

class DemandePiece(models.Model):
    fiche = models.ForeignKey(FicheReparation, on_delete=models.CASCADE)
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE)
    quantite = models.IntegerField()
    statut = models.CharField(max_length=100, default="Demandée")
    date_demande = models.DateTimeField(auto_now_add=True)

class Facture(models.Model):
    intervention = models.OneToOneField(Intervention, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_facture = models.DateTimeField(auto_now_add=True)

class Paiement(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mode_paiement = models.CharField(max_length=50)
    date_paiement = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
