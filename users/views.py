from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import JsonResponse
from .models import User, Client, Materiel, DemandeMaintenance, Intervention, FicheReparation, Piece, DemandePiece, Facture, Paiement, Message
from .serializers import (
    UserSerializer, ClientSerializer, MaterielSerializer, DemandeMaintenanceSerializer,
    InterventionSerializer, FicheReparationSerializer, PieceSerializer, DemandePieceSerializer,
    FactureSerializer, PaiementSerializer, MessageSerializer
)

# Create your views here.

@api_view(['GET'])
def hello(request):
    return JsonResponse({"response": "hello"})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class MaterielViewSet(viewsets.ModelViewSet):
    queryset = Materiel.objects.all()
    serializer_class = MaterielSerializer

class DemandeMaintenanceViewSet(viewsets.ModelViewSet):
    queryset = DemandeMaintenance.objects.all()
    serializer_class = DemandeMaintenanceSerializer

class InterventionViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer

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

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer



