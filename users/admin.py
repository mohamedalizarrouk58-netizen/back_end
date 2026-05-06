from django.contrib import admin
from .models import (User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, 
                     Piece, DemandePiece, Facture, Paiement, Message, Department, 
                     Administrateur, Manager, Technicien, ChefStock, Receptioniste)

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
