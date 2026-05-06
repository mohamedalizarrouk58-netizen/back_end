from django.shortcuts import render
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import JsonResponse
from .models import User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, Piece, DemandePiece, Facture, Paiement, Message, Department
from .serializers import (
    UserSerializer, ClientSerializer, CategorieMaterielSerializer, MaterielSerializer, DemandeMaintenanceSerializer,
    InterventionSerializer, FicheReparationSerializer, PieceSerializer, DemandePieceSerializer,
    FactureSerializer, PaiementSerializer, MessageSerializer, DepartmentSerializer
)
from .permissions import IsChefStockOrAdmin

# Create your views here.

@api_view(['GET'])
def hello(request):
    return JsonResponse({"response": "hello"})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

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



