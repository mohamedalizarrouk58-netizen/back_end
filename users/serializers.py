from rest_framework import serializers
from .models import User, Client, Materiel, DemandeMaintenance, Intervention, FicheReparation, Piece, DemandePiece, Facture, Paiement, Message

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'telephone', 'groups', 'user_permissions']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class MaterielSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materiel
        fields = '__all__'

class DemandeMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeMaintenance
        fields = '__all__'

class InterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervention
        fields = '__all__'

class FicheReparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FicheReparation
        fields = '__all__'

class PieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Piece
        fields = '__all__'

class DemandePieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandePiece
        fields = '__all__'

class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = '__all__'

class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'