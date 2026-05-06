from rest_framework import serializers
from .models import User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation, Piece, DemandePiece, Facture, Paiement, Message, Department

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
        read_only_fields = ['expediteur', 'date_envoi']

    def validate_destinataire(self, value):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated and value == request.user:
            raise serializers.ValidationError('You cannot send a message to yourself.')
        return value