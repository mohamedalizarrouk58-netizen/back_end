from django.contrib import admin
from .models import (User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, 
                     Piece, DemandePiece, Facture, Paiement, Message, Department, 
                     Administrateur, Manager, Technicien, ChefStock, Receptioniste,
                     Fournisseur, CommandePiece, LigneCommandePiece, PrixFournisseur)

admin.site.register(User)
admin.site.register(Client)
admin.site.register(CategorieMateriel)


@admin.register(Materiel)
class MaterielAdmin(admin.ModelAdmin):
    list_display = ('numero_serie', 'type', 'marque', 'modele', 'client', 'etat', 'is_deleted')
    list_filter = ('etat', 'is_deleted', 'date_reception')
    search_fields = ('numero_serie', 'type', 'marque', 'modele')


admin.site.register(DemandeMaintenance)
admin.site.register(Intervention)
admin.site.register(FicheReparation)
@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'quantite_stock', 'prix_unitaire')
    list_filter = ('categorie',)
    search_fields = ('nom', 'categorie__nom')

admin.site.register(DemandePiece)
admin.site.register(Facture)
admin.site.register(Paiement)
admin.site.register(Message)
admin.site.register(Department)

# Role-based proxy model registrations
admin.site.register(Administrateur)
admin.site.register(Manager)
admin.site.register(Technicien)
admin.site.register(ChefStock)
admin.site.register(Receptioniste)


# ===== MODULE D'ACHAT DE PIECES =====

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone', 'ville', 'est_actif', 'date_creation')
    list_filter = ('est_actif', 'pays', 'date_creation')
    search_fields = ('nom', 'email', 'telephone', 'ville')
    ordering = ('-date_creation',)


class LigneCommandePieceInline(admin.TabularInline):
    """Inline admin pour les lignes de commande"""
    model = LigneCommandePiece
    extra = 1
    fields = ('piece', 'quantite', 'prix_unitaire', 'sous_total')
    readonly_fields = ('sous_total',)


@admin.register(CommandePiece)
class CommandePieceAdmin(admin.ModelAdmin):
    list_display = ('numero_commande', 'fournisseur', 'statut', 'montant_total', 'date_commande', 'date_livraison_prevue')
    list_filter = ('statut', 'date_commande', 'fournisseur')
    search_fields = ('numero_commande', 'fournisseur__nom')
    readonly_fields = ('numero_commande', 'montant_total', 'date_commande')
    inlines = [LigneCommandePieceInline]
    fieldsets = (
        ('Informations Commande', {
            'fields': ('numero_commande', 'fournisseur', 'chef_stock', 'statut')
        }),
        ('Dates', {
            'fields': ('date_commande', 'date_livraison_prevue', 'date_livraison_reelle')
        }),
        ('Montants', {
            'fields': ('montant_total',)
        }),
        ('Observations', {
            'fields': ('remarques',)
        }),
        ('Suppression', {
            'fields': ('is_deleted',)
        }),
    )


@admin.register(PrixFournisseur)
class PrixFournisseurAdmin(admin.ModelAdmin):
    list_display = ('piece', 'fournisseur', 'prix', 'delai_livraison_jours', 'quantite_minimum', 'est_actif')
    list_filter = ('fournisseur', 'est_actif', 'date_mise_a_jour')
    search_fields = ('piece__nom', 'fournisseur__nom')
    ordering = ('piece', 'prix')
