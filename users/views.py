from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import JsonResponse
from .models import (User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, 
                     Piece, DemandePiece, Facture, Paiement, Message, Department,
                     Fournisseur, CommandePiece, LigneCommandePiece, PrixFournisseur, FactureFournisseur)
from .serializers import (
    UserSerializer, ClientSerializer, CategorieMaterielSerializer, MaterielSerializer, DemandeMaintenanceSerializer,
    InterventionSerializer, FicheReparationSerializer, PieceSerializer, DemandePieceSerializer,
    FactureSerializer, PaiementSerializer, MessageSerializer, DepartmentSerializer,
    FournisseurSerializer, CommandePieceSerializer, LigneCommandePieceSerializer, PrixFournisseurSerializer,
    FactureFournisseurSerializer
)
from .permissions import IsChefStockOrAdmin
from rest_framework.permissions import AllowAny

# Create your views here.

@api_view(['GET'])
def hello(request):
    return JsonResponse({"response": "hello"})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'], url_path='register-fournisseur', permission_classes=[AllowAny])
    def register_fournisseur(self, request):
        """Self-registration endpoint for suppliers"""
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        nom_fournisseur = request.data.get('nom_fournisseur')
        telephone = request.data.get('telephone', '')
        adresse = request.data.get('adresse', '')
        ville = request.data.get('ville', '')
        contact_principal = request.data.get('contact_principal', '')

        if not all([username, password, email, nom_fournisseur]):
            return Response(
                {'detail': 'username, password, email, and nom_fournisseur are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'detail': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if Fournisseur.objects.filter(nom=nom_fournisseur).exists():
            return Response({'detail': 'Supplier name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role='fournisseur'
        )

        fournisseur = Fournisseur.objects.create(
            utilisateur=user,
            nom=nom_fournisseur,
            email=email,
            telephone=telephone,
            adresse=adresse,
            ville=ville,
            contact_principal=contact_principal,
            est_actif=True
        )

        return Response(
            {
                'user_id': user.id,
                'username': user.username,
                'fournisseur_id': fournisseur.id,
                'nom_fournisseur': fournisseur.nom,
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class CategorieMaterielViewSet(viewsets.ModelViewSet):
    queryset = CategorieMateriel.objects.all()
    serializer_class = CategorieMaterielSerializer
    permission_classes = [IsAuthenticated, IsChefStockOrAdmin]

class MaterielViewSet(viewsets.ModelViewSet):
    queryset = Materiel.objects.all()
    serializer_class = MaterielSerializer

class DemandeMaintenanceViewSet(viewsets.ModelViewSet):
    queryset = DemandeMaintenance.objects.all()
    serializer_class = DemandeMaintenanceSerializer

    def perform_create(self, serializer):
        # Enforce server-side ownership: ignore frontend receptioniste value.
        serializer.save(receptioniste=self.request.user)

    @action(detail=False, methods=['get'], url_path='me')
    def my_demandes(self, request):
        queryset = self.get_queryset().filter(receptioniste=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class InterventionViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer

    @action(detail=False, methods=['get'], url_path='me')
    def my_interventions(self, request):
        queryset = self.get_queryset().filter(technicien=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class FicheReparationViewSet(viewsets.ModelViewSet):
    queryset = FicheReparation.objects.all()
    serializer_class = FicheReparationSerializer

class PieceViewSet(viewsets.ModelViewSet):
    queryset = Piece.objects.all()
    serializer_class = PieceSerializer

class DemandePieceViewSet(viewsets.ModelViewSet):
    queryset = DemandePiece.objects.all()
    serializer_class = DemandePieceSerializer

    def perform_create(self, serializer):
        piece = serializer.validated_data['piece']
        quantite = serializer.validated_data.get('quantite', 0)
        missing_qty = max(quantite - piece.quantite_stock, 0)

        data = {
            'demandeur_stock': self.request.user if getattr(self.request.user, 'role', None) == 'chefstock' else None,
            'quantite_manquante': missing_qty,
        }

        if missing_qty > 0:
            data['statut'] = 'en_attente_fournisseur'

        serializer.save(**data)

    @action(detail=True, methods=['post'], url_path='assigner-fournisseur')
    def assigner_fournisseur(self, request, pk=None):
        demande = self.get_object()
        fournisseur_id = request.data.get('fournisseur_id')

        if not fournisseur_id:
            return Response({'detail': 'fournisseur_id est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fournisseur = Fournisseur.objects.get(pk=fournisseur_id, est_actif=True)
        except Fournisseur.DoesNotExist:
            return Response({'detail': 'Fournisseur introuvable ou inactif.'}, status=status.HTTP_404_NOT_FOUND)

        quantite_manquante = demande.quantite_manquante or max(demande.quantite - demande.piece.quantite_stock, 0)
        if quantite_manquante <= 0:
            return Response(
                {'detail': 'Aucune quantité manquante. Cette demande ne nécessite pas de fournisseur.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        was_refused = demande.statut == 'refusee_fournisseur'
        demande.fournisseur = fournisseur
        demande.demandeur_stock = request.user if getattr(request.user, 'role', None) == 'chefstock' else demande.demandeur_stock
        demande.quantite_manquante = quantite_manquante
        demande.statut = 'reaffectee' if was_refused else 'en_attente_fournisseur'
        demande.motif_refus_fournisseur = None
        demande.date_reponse_fournisseur = None

        numero = f"CMD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        commande = CommandePiece.objects.create(
            numero_commande=numero,
            fournisseur=fournisseur,
            chef_stock=request.user if getattr(request.user, 'role', None) == 'chefstock' else None,
            statut='en_attente_fournisseur',
            remarques=f"Commande générée pour demande pièce #{demande.id}",
        )

        prix_ref = PrixFournisseur.objects.filter(piece=demande.piece, fournisseur=fournisseur, est_actif=True).first()
        prix = prix_ref.prix if prix_ref else demande.piece.prix_unitaire
        LigneCommandePiece.objects.create(
            commande=commande,
            piece=demande.piece,
            quantite=quantite_manquante,
            prix_unitaire=prix,
        )

        demande.commande = commande
        demande.save()

        serializer = self.get_serializer(demande)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reponse-fournisseur')
    def reponse_fournisseur(self, request, pk=None):
        demande = self.get_object()
        
        if getattr(request.user, 'role', None) != 'fournisseur':
            return Response({'detail': 'Only suppliers can respond to piece demands.'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.fournisseur and demande.fournisseur.utilisateur != request.user:
            return Response({'detail': 'You can only respond to demands assigned to your supplier account.'}, status=status.HTTP_403_FORBIDDEN)
        
        decision = request.data.get('decision')

        if decision not in ('accepter', 'refuser'):
            return Response({'detail': "decision doit etre 'accepter' ou 'refuser'."}, status=status.HTTP_400_BAD_REQUEST)

        if not demande.fournisseur or not demande.commande:
            return Response({'detail': 'Aucun fournisseur/commande assigné à cette demande.'}, status=status.HTTP_400_BAD_REQUEST)

        demande.date_reponse_fournisseur = timezone.now()
        demande.commande.date_reponse_fournisseur = timezone.now()

        if decision == 'refuser':
            motif = request.data.get('motif_refus', '')
            demande.statut = 'refusee_fournisseur'
            demande.motif_refus_fournisseur = motif
            demande.commande.statut = 'refusee_fournisseur'
            demande.commande.motif_refus_fournisseur = motif
            demande.commande.save()
            demande.save()
            return Response(self.get_serializer(demande).data, status=status.HTTP_200_OK)

        prix = request.data.get('prix')
        try:
            prix_decimal = Decimal(str(prix))
            if prix_decimal <= 0:
                raise ValueError
        except Exception:
            return Response({'detail': 'prix doit être un nombre positif.'}, status=status.HTTP_400_BAD_REQUEST)

        demande.statut = 'acceptee_fournisseur'
        demande.prix_propose_fournisseur = prix_decimal
        demande.motif_refus_fournisseur = None
        demande.commande.statut = 'acceptee_fournisseur'
        demande.commande.motif_refus_fournisseur = None
        demande.commande.save()

        ligne = demande.commande.lignes.filter(piece=demande.piece).first()
        if ligne:
            ligne.prix_unitaire = prix_decimal
            ligne.quantite = demande.quantite_manquante or demande.quantite
            ligne.save()

        PrixFournisseur.objects.update_or_create(
            piece=demande.piece,
            fournisseur=demande.fournisseur,
            defaults={'prix': prix_decimal, 'est_actif': True}
        )

        demande.save()
        return Response(self.get_serializer(demande).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reception-livraison')
    def reception_livraison(self, request, pk=None):
        demande = self.get_object()

        if demande.statut not in ('acceptee_fournisseur', 'commandee', 'reaffectee'):
            return Response({'detail': 'La demande doit être acceptée ou commandée avant la livraison.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantite_livree = int(request.data.get('quantite_livree', 0))
            if quantite_livree <= 0:
                raise ValueError
        except Exception:
            return Response({'detail': 'quantite_livree doit être un entier positif.'}, status=status.HTTP_400_BAD_REQUEST)

        piece = demande.piece
        piece.quantite_stock += quantite_livree
        piece.save()

        manque_restant = max((demande.quantite_manquante or 0) - quantite_livree, 0)
        demande.quantite_manquante = manque_restant
        demande.statut = 'livree' if manque_restant == 0 else 'commandee'

        if demande.commande:
            demande.commande.statut = 'livree' if manque_restant == 0 else 'commande'
            if manque_restant == 0:
                demande.commande.date_livraison_reelle = timezone.now()
            demande.commande.save()

        demande.save()

        if demande.commande and demande.fournisseur:
            prix = demande.prix_propose_fournisseur or demande.piece.prix_unitaire
            montant = Decimal(str(prix)) * Decimal(str(quantite_livree))
            numero_facture = request.data.get('numero_facture') or f"FF-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
            FactureFournisseur.objects.update_or_create(
                commande=demande.commande,
                defaults={
                    'numero_facture': numero_facture,
                    'fournisseur': demande.fournisseur,
                    'montant_total': montant,
                    'statut': 'validee' if demande.statut == 'livree' else 'brouillon',
                }
            )

        return Response(self.get_serializer(demande).data, status=status.HTTP_200_OK)

class FactureViewSet(viewsets.ModelViewSet):
    queryset = Facture.objects.all()
    serializer_class = FactureSerializer

class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer


class MessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    pagination_class = MessagePagination

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(expediteur=user) | Q(destinataire=user)
        ).order_by('-date_envoi')

    def perform_create(self, serializer):
        destinataire = serializer.validated_data.get('destinataire')

        if not destinataire:
            raise ValidationError({'destinataire': 'This field is required.'})

        if destinataire == self.request.user:
            raise ValidationError({'destinataire': 'You cannot send a message to yourself.'})

        if getattr(destinataire, 'is_deleted', False):
            raise ValidationError({'destinataire': 'Invalid destinataire.'})

        message = serializer.save(expediteur=self.request.user)

        payload = {
            'type': 'message.created',
            'id': message.id,
            'expediteur': message.expediteur_id,
            'destinataire': message.destinataire_id,
            'objet': message.objet,
            'contenu': message.contenu,
            'date_envoi': message.date_envoi.isoformat(),
        }

        channel_layer = get_channel_layer()
        if channel_layer:
            event = {'type': 'message.created', 'payload': payload}
            async_to_sync(channel_layer.group_send)(f'user_{message.destinataire_id}', event)
            async_to_sync(channel_layer.group_send)(f'user_{message.expediteur_id}', event)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


# ===== MODULE D'ACHAT DE PIECES =====

class FournisseurViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les fournisseurs"""
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nom', 'email', 'telephone']
    ordering_fields = ['nom', 'date_creation']


class CommandePieceViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les commandes de pièces"""
    queryset = CommandePiece.objects.filter(is_deleted=False)
    serializer_class = CommandePieceSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['numero_commande', 'fournisseur__nom']
    ordering_fields = ['date_commande', 'statut', 'montant_total']

    @action(detail=True, methods=['post'])
    def calculer_montant(self, request, pk=None):
        """Action personnalisée pour calculer le montant total d'une commande"""
        commande = self.get_object()
        montant = commande.calculer_montant_total()
        return Response({'montant_total': montant}, status=status.HTTP_200_OK)


class LigneCommandePieceViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les lignes de commande"""
    queryset = LigneCommandePiece.objects.all()
    serializer_class = LigneCommandePieceSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['commande__numero_commande', 'piece__nom']


class PrixFournisseurViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les prix fournisseurs"""
    queryset = PrixFournisseur.objects.filter(est_actif=True)
    serializer_class = PrixFournisseurSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['piece__nom', 'fournisseur__nom']
    ordering_fields = ['prix', 'delai_livraison_jours']


class FactureFournisseurViewSet(viewsets.ModelViewSet):
    """ViewSet pour les factures fournisseurs"""
    queryset = FactureFournisseur.objects.all()
    serializer_class = FactureFournisseurSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['numero_facture', 'fournisseur__nom', 'commande__numero_commande']
    ordering_fields = ['date_facture', 'montant_total', 'statut']