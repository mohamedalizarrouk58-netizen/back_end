from django.contrib import admin
from .models import User,Client,Materiel,DemandeMaintenance,Intervention,FicheReparation,Piece,DemandePiece,Facture,Paiement

admin.site.register(User)
admin.site.register(Client)
admin.site.register(Materiel)
admin.site.register(DemandeMaintenance)
admin.site.register(Intervention)
admin.site.register(FicheReparation)
admin.site.register(Piece)
admin.site.register(DemandePiece)
admin.site.register(Facture)
admin.site.register(Paiement)
