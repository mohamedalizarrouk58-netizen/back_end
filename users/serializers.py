from rest_framework import serializers
from .models import (User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, 
                     Piece, DemandePiece, Facture, Paiement, Message, Department,
                     Fournisseur, CommandePiece, LigneCommandePiece, PrixFournisseur, FactureFournisseur)

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'nom_dept', 'description', 'date_creation']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'telephone', 'image', 'department', 'password', 'groups', 'user_permissions']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class CategorieMaterielSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieMateriel
        fields = ['id', 'nom', 'description', 'is_active', 'date_creation']

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
    categorie = serializers.PrimaryKeyRelatedField(
        queryset=CategorieMateriel.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    categorie_detail = CategorieMaterielSerializer(source='categorie', read_only=True)

    class Meta:
        model = Piece
        fields = '__all__'

class DemandePieceSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)

    class Meta:
        model = DemandePiece
        fields = '__all__'
        read_only_fields = ('date_demande', 'date_reponse_fournisseur')

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
        read_only_fields = ['expediteur', 'date_envoi']

    def validate_destinataire(self, value):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated and value == request.user:
            raise serializers.ValidationError('You cannot send a message to yourself.')
        return value


# ===== MODULE D'ACHAT DE PIECES =====

class FournisseurSerializer(serializers.ModelSerializer):
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    utilisateur_email = serializers.CharField(source='utilisateur.email', read_only=True)
    
    class Meta:
        model = Fournisseur
        fields = '__all__'
        read_only_fields = ('date_creation',)


class PrixFournisseurSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)

    class Meta:
        model = PrixFournisseur
        fields = '__all__'
        read_only_fields = ('date_mise_a_jour',)


class LigneCommandePieceSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    sous_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = LigneCommandePiece
        fields = '__all__'


class CommandePieceSerializer(serializers.ModelSerializer):
    lignes = LigneCommandePieceSerializer(many=True, read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    chef_stock_nom = serializers.CharField(source='chef_stock.get_full_name', read_only=True)

    class Meta:
        model = CommandePiece
        fields = '__all__'
        read_only_fields = ('montant_total', 'date_commande')


class FactureFournisseurSerializer(serializers.ModelSerializer):
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    numero_commande = serializers.CharField(source='commande.numero_commande', read_only=True)

    class Meta:
        model = FactureFournisseur
        fields = '__all__'
        read_only_fields = ('date_facture',)