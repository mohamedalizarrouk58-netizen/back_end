from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models import Sum, F, DecimalField

class Department(models.Model):
    nom_dept = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom_dept

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['nom_dept']

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
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    is_deleted = models.BooleanField(default=False)  # Soft delete

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

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

# Proxy models for role-based access
class Administrateur(User):
    class Meta:
        proxy = True
        verbose_name = 'Administrateur'
        verbose_name_plural = 'Administrateurs'

    def save(self, *args, **kwargs):
        self.role = 'admin'
        super().save(*args, **kwargs)

class Manager(User):
    class Meta:
        proxy = True
        verbose_name = 'Manager'
        verbose_name_plural = 'Managers'

    def save(self, *args, **kwargs):
        self.role = 'manager'
        super().save(*args, **kwargs)

class Technicien(User):
    class Meta:
        proxy = True
        verbose_name = 'Technicien'
        verbose_name_plural = 'Techniciens'

    def save(self, *args, **kwargs):
        self.role = 'technicien'
        super().save(*args, **kwargs)

class ChefStock(User):
    class Meta:
        proxy = True
        verbose_name = 'Chef Stock'
        verbose_name_plural = 'Chefs Stock'

    def save(self, *args, **kwargs):
        self.role = 'chefstock'
        super().save(*args, **kwargs)

class Receptioniste(User):
    class Meta:
        proxy = True
        verbose_name = 'Receptioniste'
        verbose_name_plural = 'Receptionistes'

    def save(self, *args, **kwargs):
        self.role = 'receptioniste'
        super().save(*args, **kwargs)

class Client(models.Model):
    nom_complet = models.CharField(max_length=200, blank=False)
    email = models.EmailField(unique=True, blank=True, null=True)
    telephone = models.CharField(max_length=20)
    adresse = models.TextField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    def __str__(self):
        return self.nom_complet

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['nom_complet']


class CategorieMateriel(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = 'Categorie materiel'
        verbose_name_plural = 'Categories materiel'
        ordering = ['nom']

class Materiel(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='materiels')
    type = models.CharField(max_length=100)
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100)
    numero_serie = models.CharField(max_length=100, unique=True)
    etat = models.CharField(max_length=100, default="Reçu")
    date_reception = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    def __str__(self):
        return f"{self.type} {self.marque} {self.modele} ({self.numero_serie})"

    class Meta:
        verbose_name = 'Materiel'
        verbose_name_plural = 'Materiels'
        ordering = ['-date_reception']


class DemandeMaintenance(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('refuse', 'Refusé'),
    ]
    PRIORITES = [
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute'),
    ]

    materiel = models.ForeignKey(Materiel, on_delete=models.CASCADE, related_name='demandes')
    receptioniste = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='demandes_reception')
    manager = models.ForeignKey(User, related_name='demandes_manager', on_delete=models.SET_NULL, null=True)
    priorite = models.CharField(max_length=20, choices=PRIORITES, default='moyenne')
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DM-{self.id} [{self.get_statut_display()}]"

    class Meta:
        verbose_name = 'Demande de maintenance'
        verbose_name_plural = 'Demandes de maintenance'
        ordering = ['-date_creation']

class Intervention(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('refuse', 'Refusé'),
    ]

    demande = models.OneToOneField(DemandeMaintenance, on_delete=models.CASCADE, related_name='intervention')
    technicien = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='interventions')
    diagnostic = models.TextField(null=True, blank=True)
    solution_proposee = models.TextField(null=True, blank=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')

    def __str__(self):
        return f"Intervention {self.id} - {self.demande}"

    class Meta:
        verbose_name = 'Intervention'
        verbose_name_plural = 'Interventions'
        ordering = ['-date_debut']

class FicheReparation(models.Model):
    intervention = models.OneToOneField(Intervention, on_delete=models.CASCADE, related_name='fiche_reparation')
    description_panne = models.TextField()
    solution = models.TextField(null=True, blank=True)
    cout_main_oeuvre = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    confirmation = models.BooleanField(default=False)
    valide_manager = models.BooleanField(default=False)

    def __str__(self):
        return f"Fiche {self.id} - Interv {self.intervention.id}"

    def cout_pieces(self):
        """Calculate total cost of parts used in this repair"""
        return self.demandes_pieces.aggregate(
            total=Sum(F('piece__prix_unitaire') * F('quantite'), output_field=DecimalField())
        )['total'] or 0

    class Meta:
        verbose_name = 'Fiche de réparation'
        verbose_name_plural = 'Fiches de réparation'

class Piece(models.Model):
    nom = models.CharField(max_length=200)
    categorie = models.ForeignKey(
        CategorieMateriel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces'
    )
    quantite_stock = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = 'Piece'
        verbose_name_plural = 'Pieces'

class DemandePiece(models.Model):
    STATUTS = [
        ('demandee', 'Demandée'),
        ('approuvee', 'Approuvée'),
        ('livree', 'Livrée'),
    ]
    fiche = models.ForeignKey(FicheReparation, on_delete=models.CASCADE, related_name='demandes_pieces')
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name='demandes')
    quantite = models.IntegerField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='demandee')
    date_demande = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DP-{self.id} [{self.piece.nom}] - {self.get_statut_display()}"

    class Meta:
        verbose_name = 'Demande de piece'
        verbose_name_plural = 'Demandes de pieces'

class Facture(models.Model):
    intervention = models.OneToOneField(Intervention, on_delete=models.CASCADE, related_name='facture')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='factures')
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_facture = models.DateTimeField(auto_now_add=True)
    est_payee = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    def __str__(self):
        return f"Facture {self.id} - {self.client.nom_complet} - {self.montant_total}"

    class Meta:
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'

class Paiement(models.Model):
    MODES = [
        ('especes', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement'),
    ]
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mode_paiement = models.CharField(max_length=20, choices=MODES, default='especes')
    date_paiement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Paiement {self.id} - {self.montant}"

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'


class Message(models.Model):
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_envoyes')
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_recus')
    objet = models.CharField(max_length=200, blank=True)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.id} de {self.expediteur.username} à {self.destinataire.username}"
