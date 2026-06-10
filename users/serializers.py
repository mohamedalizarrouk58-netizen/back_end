import base64
import re

from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import (
    User, Client, CategorieMateriel, Materiel,
    DemandeMaintenance, Intervention, FicheReparation,
    Piece, DemandePiece, Facture, Paiement, Message, Department,
    Fournisseur, CommandePiece, LigneCommandePiece, PrixFournisseur, FactureFournisseur,
)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'nom_dept', 'description', 'date_creation']
        read_only_fields = ['date_creation']

    def validate(self, attrs):
        from .department_policy import can_create_department, department_limit_error_message

        if self.instance is None and not can_create_department():
            raise serializers.ValidationError(department_limit_error_message())
        return attrs


class UserSerializer(serializers.ModelSerializer):
    MAX_PROFILE_IMAGE_BYTES = 20 * 1024 * 1024

    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    image = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='department',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'telephone', 'image', 'department', 'department_id', 'password',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = self._get_image_payload(instance)
        return data

    def _get_image_payload(self, instance):
        if instance.image_data:
            return instance.image_data
        if instance.image:
            try:
                with instance.image.open('rb') as file_handle:
                    encoded = base64.b64encode(file_handle.read()).decode('ascii')
                name = instance.image.name.lower()
                mime = 'image/jpeg'
                if name.endswith('.png'):
                    mime = 'image/png'
                elif name.endswith('.webp'):
                    mime = 'image/webp'
                elif name.endswith('.gif'):
                    mime = 'image/gif'
                return f'data:{mime};base64,{encoded}'
            except OSError:
                return None
        return None

    def validate_image(self, value):
        if not value:
            return value
        if value.startswith('data:image/'):
            payload = value.split(',', 1)[-1]
            try:
                decoded = base64.b64decode(payload, validate=False)
            except (ValueError, TypeError):
                raise serializers.ValidationError('Image must be a base64 or data-URL string.')
            if len(decoded) > self.MAX_PROFILE_IMAGE_BYTES:
                raise serializers.ValidationError('Profile image must be 20 MB or smaller.')
            return value
        if re.fullmatch(r'[A-Za-z0-9+/=\s]+', value.strip()):
            payload = value.strip()
            try:
                decoded = base64.b64decode(payload, validate=False)
            except (ValueError, TypeError):
                raise serializers.ValidationError('Image must be a base64 or data-URL string.')
            if len(decoded) > self.MAX_PROFILE_IMAGE_BYTES:
                raise serializers.ValidationError('Profile image must be 20 MB or smaller.')
            return f'data:image/png;base64,{payload}'
        raise serializers.ValidationError('Image must be a base64 or data-URL string.')

    def _apply_image(self, user, image_value):
        if image_value is None:
            return
        if image_value == '':
            user.image_data = None
            if user.image:
                user.image.delete(save=False)
            return
        user.image_data = image_value
        try:
            header, payload = image_value.split(',', 1)
            extension = 'png'
            if 'jpeg' in header or 'jpg' in header:
                extension = 'jpg'
            elif 'webp' in header:
                extension = 'webp'
            elif 'gif' in header:
                extension = 'gif'
            decoded = base64.b64decode(payload)
            if user.image:
                user.image.delete(save=False)
            user.image.save(
                f'user_{user.pk}.{extension}',
                ContentFile(decoded),
                save=False,
            )
        except (ValueError, TypeError):
            pass

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        image_value = validated_data.pop('image', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        if image_value is not None:
            self._apply_image(user, image_value)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        image_value = validated_data.pop('image', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if image_value is not None:
            self._apply_image(instance, image_value)
        instance.save()
        return instance


class UserProfileSerializer(UserSerializer):
    """Fields a signed-in user may update on their own profile."""

    class Meta(UserSerializer.Meta):
        read_only_fields = ['id', 'username', 'role', 'department', 'department_id']


class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight read-only reference used in nested contexts."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


# ---------------------------------------------------------------------------
# Maintenance domain
# ---------------------------------------------------------------------------

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'nom_complet', 'email', 'telephone', 'adresse',
            'date_creation', 'is_deleted',
        ]
        read_only_fields = ['date_creation', 'is_deleted']


class CategorieMaterielSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieMateriel
        fields = ['id', 'nom', 'description', 'is_active', 'date_creation']
        read_only_fields = ['date_creation']


class MaterielSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom_complet', read_only=True)

    class Meta:
        model = Materiel
        fields = [
            'id', 'client', 'client_nom', 'type', 'marque', 'modele',
            'numero_serie', 'etat', 'date_reception', 'is_deleted',
        ]
        read_only_fields = ['is_deleted']


class DemandeMaintenanceSerializer(serializers.ModelSerializer):
    materiel_detail = serializers.SerializerMethodField(read_only=True)
    receptioniste_nom = serializers.CharField(
        source='receptioniste.username', read_only=True
    )
    manager_nom = serializers.CharField(
        source='manager.username', read_only=True
    )
    facture_id = serializers.SerializerMethodField(read_only=True)
    facture_email_envoye = serializers.SerializerMethodField(read_only=True)
    montant_facture = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DemandeMaintenance
        fields = [
            'id', 'materiel', 'materiel_detail', 'receptioniste', 'receptioniste_nom',
            'manager', 'manager_nom', 'priorite', 'statut', 'date_creation',
            'facture_id', 'facture_email_envoye', 'montant_facture',
        ]
        read_only_fields = ['date_creation']

    def _get_client_facture(self, obj):
        try:
            facture = obj.intervention.facture
        except Exception:
            return None
        if facture is None or facture.is_deleted:
            return None
        return facture

    def get_facture_id(self, obj):
        facture = self._get_client_facture(obj)
        return facture.id if facture else None

    def get_facture_email_envoye(self, obj):
        facture = self._get_client_facture(obj)
        return bool(facture and facture.email_client_envoye)

    def get_montant_facture(self, obj):
        facture = self._get_client_facture(obj)
        return facture.montant_total if facture else None

    def get_materiel_detail(self, obj):
        if obj.materiel:
            return {
                'id': obj.materiel.id,
                'numero_serie': obj.materiel.numero_serie,
                'marque': obj.materiel.marque,
                'modele': obj.materiel.modele,
            }
        return None


class InterventionSerializer(serializers.ModelSerializer):
    technicien_nom = serializers.CharField(source='technicien.username', read_only=True)
    demande_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Intervention
        fields = [
            'id', 'demande', 'demande_detail', 'technicien', 'technicien_nom',
            'diagnostic', 'solution_proposee', 'date_debut', 'date_fin', 'statut',
        ]

    def get_demande_detail(self, obj):
        if obj.demande:
            return {
                'id': obj.demande.id,
                'statut': obj.demande.statut,
                'priorite': obj.demande.priorite,
            }
        return None


class FicheReparationSerializer(serializers.ModelSerializer):
    cout_pieces = serializers.SerializerMethodField(read_only=True)
    intervention_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FicheReparation
        fields = [
            'id', 'intervention', 'intervention_detail', 'description_panne', 'solution',
            'cout_main_oeuvre', 'frais_societe', 'prix_supplementaire',
            'cout_pieces', 'confirmation', 'valide_manager',
        ]

    def get_cout_pieces(self, obj):
        return str(obj.cout_pieces())

    def get_intervention_detail(self, obj):
        if obj.intervention:
            return {'id': obj.intervention.id, 'statut': obj.intervention.statut}
        return None


# ---------------------------------------------------------------------------
# Inventory domain
# ---------------------------------------------------------------------------

class PieceSerializer(serializers.ModelSerializer):
    categorie = serializers.PrimaryKeyRelatedField(
        queryset=CategorieMateriel.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    categorie_detail = CategorieMaterielSerializer(source='categorie', read_only=True)

    class Meta:
        model = Piece
        fields = [
            'id', 'nom', 'reference', 'modele', 'categorie', 'categorie_detail',
            'quantite_stock', 'seuil_alerte', 'statut_stock', 'prix_unitaire', 'date_creation',
        ]
        read_only_fields = ['statut_stock', 'date_creation']


class DemandePieceSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    piece_reference = serializers.CharField(source='piece.reference', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    demandeur_username = serializers.CharField(
        source='demandeur_stock.username', read_only=True
    )

    class Meta:
        model = DemandePiece
        fields = [
            'id', 'fiche', 'piece', 'piece_nom', 'piece_reference', 'quantite',
            'quantite_manquante', 'demandeur_stock', 'demandeur_username',
            'fournisseur', 'fournisseur_nom', 'commande',
            'prix_propose_fournisseur', 'motif_refus_fournisseur',
            'date_reponse_fournisseur', 'statut', 'date_demande',
        ]
        read_only_fields = [
            'date_demande', 'date_reponse_fournisseur',
            'quantite_manquante', 'demandeur_stock',
        ]


# ---------------------------------------------------------------------------
# Billing domain
# ---------------------------------------------------------------------------

class FactureSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom_complet', read_only=True)
    intervention_statut = serializers.CharField(
        source='intervention.statut', read_only=True
    )

    class Meta:
        model = Facture
        fields = [
            'id', 'intervention', 'intervention_statut', 'client', 'client_nom',
            'montant_pieces', 'montant_main_oeuvre', 'montant_frais_societe',
            'montant_supplementaire', 'montant_total', 'date_facture', 'est_payee',
            'email_client_envoye', 'date_email_client', 'is_deleted',
        ]
        read_only_fields = [
            'montant_pieces', 'montant_main_oeuvre', 'montant_frais_societe',
            'montant_supplementaire', 'date_facture', 'email_client_envoye',
            'date_email_client', 'is_deleted',
        ]


class PaiementSerializer(serializers.ModelSerializer):
    facture_montant = serializers.DecimalField(
        source='facture.montant_total', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Paiement
        fields = [
            'id', 'facture', 'facture_montant', 'montant', 'mode_paiement', 'date_paiement',
        ]
        read_only_fields = ['date_paiement']


# ---------------------------------------------------------------------------
# Messaging domain
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    expediteur_detail = UserMinimalSerializer(source='expediteur', read_only=True)
    destinataire_detail = UserMinimalSerializer(source='destinataire', read_only=True)
    fichier_url = serializers.SerializerMethodField()
    fichier_name = serializers.SerializerMethodField()
    # Avoid model choice validation on write — type is inferred from the attachment in validate().
    type_message = serializers.CharField(required=False, allow_blank=True)

    IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    AUDIO_TYPES = {
        'audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/mp3', 'audio/mp4',
        'audio/wav', 'audio/x-wav', 'audio/aac', 'audio/m4a',
        'video/webm',  # browsers often tag voice-only webm this way
    }
    AUDIO_EXTENSIONS = {'.webm', '.ogg', '.mp3', '.m4a', '.wav', '.aac', '.mp4'}
    FILE_TYPES = {
        'application/pdf',
        'application/x-pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'application/zip',
        'application/x-zip-compressed',
        'application/x-rar-compressed',
        'application/octet-stream',
    }
    FILE_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.csv', '.zip', '.rar', '.7z',
    }
    MAX_IMAGE_BYTES = 20 * 1024 * 1024
    MAX_AUDIO_BYTES = 10 * 1024 * 1024
    MAX_FILE_BYTES = 20 * 1024 * 1024

    class Meta:
        model = Message
        fields = [
            'id', 'expediteur', 'expediteur_detail', 'destinataire', 'destinataire_detail',
            'objet', 'contenu', 'type_message', 'fichier', 'fichier_url', 'fichier_name',
            'is_deleted', 'date_envoi',
        ]
        read_only_fields = ['expediteur', 'date_envoi', 'fichier_url', 'fichier_name', 'is_deleted']
        extra_kwargs = {
            'fichier': {'write_only': True},
            'type_message': {'required': False},
        }

    def get_fichier_url(self, obj):
        if not obj.fichier:
            return None
        request = self.context.get('request')
        url = obj.fichier.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_fichier_name(self, obj):
        if not obj.fichier:
            return None
        name = obj.fichier.name or ''
        return name.rsplit('/', 1)[-1] if name else None

    def validate_destinataire(self, value):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated and value == request.user:
            raise serializers.ValidationError('You cannot send a message to yourself.')
        return value

    def _is_audio_upload(self, value):
        name = (value.name or '').lower()
        if any(name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
            return True

        content_type = (value.content_type or '').lower().split(';')[0].strip()
        return content_type in self.AUDIO_TYPES

    def _is_file_upload(self, value):
        name = (value.name or '').lower()
        if any(name.endswith(ext) for ext in self.FILE_EXTENSIONS):
            return True

        content_type = (value.content_type or '').lower().split(';')[0].strip()
        return content_type in self.FILE_TYPES

    def validate_fichier(self, value):
        if not value:
            return value

        content_type = (value.content_type or '').lower().split(';')[0].strip()
        size = value.size or 0

        if content_type in self.IMAGE_TYPES:
            if size > self.MAX_IMAGE_BYTES:
                raise serializers.ValidationError('Image must be 20 MB or smaller.')
            return value

        # Check documents before audio — many browsers send application/octet-stream for PDF/TXT.
        if self._is_file_upload(value):
            if size > self.MAX_FILE_BYTES:
                raise serializers.ValidationError('File must be 20 MB or smaller.')
            return value

        if self._is_audio_upload(value):
            if size > self.MAX_AUDIO_BYTES:
                raise serializers.ValidationError('Audio must be 10 MB or smaller.')
            return value

        request = self.context.get('request')
        declared_type = ''
        if request is not None:
            declared_type = str(request.data.get('type_message', '')).lower().strip()

        if declared_type in {Message.TYPE_FILE, Message.TYPE_TEXT}:
            if size > self.MAX_FILE_BYTES:
                raise serializers.ValidationError('File must be 20 MB or smaller.')
            return value

        # Non-image, non-audio uploads are treated as generic file attachments.
        if size > self.MAX_FILE_BYTES:
            raise serializers.ValidationError('File must be 20 MB or smaller.')
        return value

    def validate(self, attrs):
        contenu = str(attrs.get('contenu') or '').strip()
        fichier = attrs.get('fichier')
        type_message = attrs.get('type_message') or Message.TYPE_TEXT

        if fichier:
            content_type = (fichier.content_type or '').lower().split(';')[0].strip()
            declared_type = str(type_message).lower().strip()
            if content_type in self.IMAGE_TYPES and declared_type != Message.TYPE_FILE:
                attrs['type_message'] = Message.TYPE_IMAGE
            elif self._is_audio_upload(fichier) and declared_type not in {
                Message.TYPE_FILE,
                Message.TYPE_IMAGE,
            }:
                attrs['type_message'] = Message.TYPE_AUDIO
            elif self._is_file_upload(fichier) or declared_type == Message.TYPE_FILE:
                attrs['type_message'] = Message.TYPE_FILE
            else:
                attrs['type_message'] = Message.TYPE_FILE
        elif contenu:
            attrs['type_message'] = Message.TYPE_TEXT
            attrs['contenu'] = contenu
        else:
            raise serializers.ValidationError('Message must include text or an attachment.')

        if contenu:
            attrs['contenu'] = contenu

        return attrs


# ---------------------------------------------------------------------------
# Procurement domain
# ---------------------------------------------------------------------------

class FournisseurSerializer(serializers.ModelSerializer):
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    utilisateur_email = serializers.CharField(source='utilisateur.email', read_only=True)

    class Meta:
        model = Fournisseur
        fields = [
            'id', 'utilisateur', 'utilisateur_username', 'utilisateur_email',
            'nom', 'email', 'telephone', 'adresse', 'ville', 'code_postal',
            'pays', 'contact_principal', 'date_creation', 'est_actif',
        ]
        read_only_fields = ['date_creation']


class LigneCommandePieceSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    piece_reference = serializers.CharField(source='piece.reference', read_only=True)
    sous_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = LigneCommandePiece
        fields = [
            'id', 'commande', 'piece', 'piece_nom', 'piece_reference',
            'quantite', 'prix_unitaire', 'sous_total',
        ]


class CommandePieceSerializer(serializers.ModelSerializer):
    lignes = LigneCommandePieceSerializer(many=True, read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    chef_stock_nom = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CommandePiece
        fields = [
            'id', 'numero_commande', 'fournisseur', 'fournisseur_nom',
            'chef_stock', 'chef_stock_nom', 'statut', 'montant_total',
            'date_commande', 'date_livraison_prevue', 'date_livraison_reelle',
            'date_reponse_fournisseur', 'motif_refus_fournisseur',
            'remarques', 'is_deleted', 'lignes',
        ]
        read_only_fields = ['montant_total', 'date_commande']

    def get_chef_stock_nom(self, obj):
        if obj.chef_stock:
            return obj.chef_stock.get_full_name() or obj.chef_stock.username
        return None


class PrixFournisseurSerializer(serializers.ModelSerializer):
    piece_nom = serializers.CharField(source='piece.nom', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)

    class Meta:
        model = PrixFournisseur
        fields = [
            'id', 'piece', 'piece_nom', 'fournisseur', 'fournisseur_nom',
            'prix', 'delai_livraison_jours', 'quantite_minimum',
            'date_mise_a_jour', 'est_actif',
        ]
        read_only_fields = ['date_mise_a_jour']


class FactureFournisseurSerializer(serializers.ModelSerializer):
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    numero_commande = serializers.CharField(source='commande.numero_commande', read_only=True)

    class Meta:
        model = FactureFournisseur
        fields = [
            'id', 'numero_facture', 'commande', 'numero_commande',
            'fournisseur', 'fournisseur_nom',
            'montant_total', 'date_facture', 'statut', 'notes',
        ]
        read_only_fields = ['date_facture']
