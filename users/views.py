from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
import base64, os as _os
from .models import (User, Client, CategorieMateriel, Materiel, DemandeMaintenance, Intervention, FicheReparation,
                     Piece, DemandePiece, Facture, Paiement, Message, Department,
                     Fournisseur, CommandePiece, LigneCommandePiece, PrixFournisseur, FactureFournisseur, OTPCode)
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

# ===== OTP / EMAIL AUTH VIEWS =====


# Load logo once as base64 for HTML emails
_LOGO_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    '..', 'front_app', 'src', 'assets', 'logo_s.png'
)
try:
    with open(_LOGO_PATH, 'rb') as _f:
        _LOGO_B64 = base64.b64encode(_f.read()).decode('utf-8')
    _LOGO_SRC = f'data:image/png;base64,{_LOGO_B64}'
except Exception:
    _LOGO_SRC = ''  # fallback: no logo if file not found


def _build_html_email(user, purpose, code, expiry):
    """Build a styled HTML email body with embedded logo."""
    name = user.get_full_name() or user.username

    if purpose == 'password_reset':
        title = 'Réinitialisation de mot de passe'
        subtitle = 'Utilisez le code ci-dessous pour réinitialiser votre mot de passe.'
        footer_note = "Si vous n'avez pas demandé cette réinitialisation, ignorez cet email."
        badge_color = '#3b82f6'
    else:
        title = 'Code de vérification'
        subtitle = 'Utilisez le code ci-dessous pour finaliser votre connexion.'
        footer_note = "Si vous n'avez pas tenté de vous connecter, sécurisez votre compte immédiatement."
        badge_color = '#10b981'

    logo_html = f'<img src="{_LOGO_SRC}" alt="GMAO" style="height:48px;object-fit:contain;display:block;margin:0 auto 8px;" />' if _LOGO_SRC else ''

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:32px 40px;text-align:center;">
            {logo_html}
            <p style="margin:0;color:#94a3b8;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:600;">GMAO Système</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 40px 32px;">
            <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#0f172a;">{title}</h1>
            <p style="margin:0 0 28px;color:#64748b;font-size:15px;line-height:1.6;">Bonjour <strong>{name}</strong>,<br>{subtitle}</p>

            <!-- OTP Code Box -->
            <div style="background:#f8fafc;border:2px dashed {badge_color};border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
              <p style="margin:0 0 6px;font-size:11px;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;font-weight:600;">Votre code</p>
              <p style="margin:0;font-size:42px;font-weight:800;letter-spacing:12px;color:{badge_color};font-family:'Courier New',monospace;">{code}</p>
              <p style="margin:8px 0 0;font-size:12px;color:#94a3b8;">Expire dans <strong>{expiry} minutes</strong></p>
            </div>

            <p style="margin:0;font-size:13px;color:#94a3b8;line-height:1.6;">{footer_note}</p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 40px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">© GMAO Système — Ne pas répondre à cet email.</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _send_otp_email(user, purpose):
    """Helper: create OTP record and send HTML email via Gmail SMTP"""
    expiry = getattr(django_settings, 'OTP_EXPIRY_MINUTES', 10)
    length = getattr(django_settings, 'OTP_LENGTH', 6)

    # Invalidate previous OTPs for the same purpose
    OTPCode.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    code = OTPCode.generate_code(length)
    otp = OTPCode.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=expiry),
    )

    subject_map = {
        'password_reset': 'Réinitialisation de mot de passe — GMAO Système',
        'two_factor': 'Code de vérification — GMAO Système',
    }
    plain_text = f"Bonjour {user.get_full_name() or user.username},\n\nVotre code: {code}\n\nExpire dans {expiry} minutes.\n\n— GMAO Système"

    msg = EmailMultiAlternatives(
        subject=subject_map.get(purpose, 'Code OTP — GMAO Système'),
        body=plain_text,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(_build_html_email(user, purpose, code, expiry), 'text/html')
    msg.send(fail_silently=False)
    return otp


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Send OTP for password_reset or two_factor purposes.
    Body: { email: str, purpose: 'password_reset' | 'two_factor' }
    """
    email = request.data.get('email', '').strip()
    purpose = request.data.get('purpose', 'password_reset')

    if purpose not in ('password_reset', 'two_factor'):
        return Response({'detail': "purpose must be 'password_reset' or 'two_factor'."}, status=400)

    if not email:
        return Response({'detail': 'email is required.'}, status=400)

    try:
        user = User.objects.get(email=email, is_deleted=False)
    except User.DoesNotExist:
        # Return success even if email not found (security: don't expose user existence)
        return Response({'detail': 'If this email is registered, a code has been sent.'}, status=200)

    if not user.email:
        return Response({'detail': 'This account has no email address configured.'}, status=400)

    try:
        _send_otp_email(user, purpose)
    except Exception as exc:
        return Response({'detail': f'Failed to send email: {str(exc)}'}, status=500)

    return Response({'detail': 'If this email is registered, a code has been sent.'}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_reset_password(request):
    """Verify OTP and set a new password.
    Body: { email: str, code: str, new_password: str }
    """
    email = request.data.get('email', '').strip()
    code = request.data.get('code', '').strip()
    new_password = request.data.get('new_password', '')

    if not all([email, code, new_password]):
        return Response({'detail': 'email, code, and new_password are required.'}, status=400)

    if len(new_password) < 6:
        return Response({'detail': 'Le mot de passe doit contenir au moins 6 caractères.'}, status=400)

    try:
        user = User.objects.get(email=email, is_deleted=False)
    except User.DoesNotExist:
        return Response({'detail': 'Code invalide ou expiré.'}, status=400)

    otp = OTPCode.objects.filter(
        user=user,
        code=code,
        purpose='password_reset',
        is_used=False,
    ).order_by('-created_at').first()

    if not otp or not otp.is_valid():
        return Response({'detail': 'Code invalide ou expiré.'}, status=400)

    user.set_password(new_password)
    user.save()
    otp.is_used = True
    otp.save()

    return Response({'detail': 'Mot de passe réinitialisé avec succès.'}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_2fa(request):
    """Step 2 of 2FA login: verify OTP then return JWT tokens.
    Body: { username: str, code: str }
    """
    username = request.data.get('username', '').strip()
    code = request.data.get('code', '').strip()

    if not all([username, code]):
        return Response({'detail': 'username and code are required.'}, status=400)

    try:
        user = User.objects.get(username=username, is_deleted=False)
    except User.DoesNotExist:
        return Response({'detail': 'Code invalide ou expiré.'}, status=400)

    otp = OTPCode.objects.filter(
        user=user,
        code=code,
        purpose='two_factor',
        is_used=False,
    ).order_by('-created_at').first()

    if not otp or not otp.is_valid():
        return Response({'detail': 'Code invalide ou expiré.'}, status=400)

    otp.is_used = True
    otp.save()

    # Issue JWT tokens
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'role': user.role,
        'username': user.username,
    }, status=200)


@api_view(['POST'])
def toggle_2fa(request):
    """Toggle 2FA on/off for the authenticated user.
    Requires: JWT auth. Body: { enabled: bool }
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication required.'}, status=401)

    enabled = request.data.get('enabled')
    if enabled is None:
        return Response({'detail': 'enabled (bool) is required.'}, status=400)

    request.user.two_factor_enabled = bool(enabled)
    request.user.save(update_fields=['two_factor_enabled'])
    return Response({
        'two_factor_enabled': request.user.two_factor_enabled,
        'detail': f"Authentification à deux facteurs {'activée' if enabled else 'désactivée'}.",
    }, status=200)


@api_view(['GET'])
def get_2fa_status(request):
    """Return 2FA status for the authenticated user."""
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication required.'}, status=401)
    return Response({'two_factor_enabled': request.user.two_factor_enabled}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_2fa_otp_for_login(request):
    """Called right after credential verification when 2FA is enabled.
    Body: { username: str, password: str }
    Returns: { requires_2fa: bool } or tokens if 2FA disabled.
    """
    from django.contrib.auth import authenticate
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not all([username, password]):
        return Response({'detail': 'username and password are required.'}, status=400)

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({'detail': 'Identifiants invalides.'}, status=401)

    if not getattr(user, 'two_factor_enabled', False):
        # 2FA not enabled — return tokens directly
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        return Response({
            'requires_2fa': False,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'username': user.username,
        }, status=200)

    # 2FA enabled — send OTP
    if not user.email:
        return Response({'detail': 'Aucune adresse email configurée pour ce compte.'}, status=400)

    try:
        _send_otp_email(user, 'two_factor')
    except Exception as exc:
        return Response({'detail': f'Impossible d\'envoyer le code: {str(exc)}'}, status=500)

    return Response({
        'requires_2fa': True,
        'email_hint': user.email[:2] + '***@' + user.email.split('@')[-1],
    }, status=200)


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

    @action(detail=False, methods=['post'], url_path='register', permission_classes=[AllowAny])
    def register(self, request):
        """General user self-registration endpoint"""
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        role = request.data.get('role')
        telephone = request.data.get('telephone', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not all([username, password, email, role]):
            return Response(
                {'detail': 'username, password, email, and role are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_roles = [r[0] for r in User.ROLE_CHOICES]
        if role not in valid_roles:
            return Response(
                {'detail': f'Invalid role. Choose from {", ".join(valid_roles)}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'detail': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role=role,
            telephone=telephone,
            first_name=first_name,
            last_name=last_name
        )

        if role == 'fournisseur':
            Fournisseur.objects.create(
                utilisateur=user,
                nom=f"Fournisseur {username}",
                email=email,
                telephone=telephone,
                est_actif=True
            )

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
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
            data['statut'] = 'hors_stock'

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
        
        user_role = getattr(request.user, 'role', None)
        if user_role not in ['fournisseur', 'chefstock', 'administrateur']:
            return Response({'detail': 'Only suppliers or authorized staff can respond to piece demands.'}, status=status.HTTP_403_FORBIDDEN)
        
        if user_role == 'fournisseur' and demande.fournisseur and demande.fournisseur.utilisateur != request.user:
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
class FactureFournisseurViewSet(viewsets.ModelViewSet):
    """ViewSet pour les factures fournisseurs"""
    queryset = FactureFournisseur.objects.all()
    serializer_class = FactureFournisseurSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['numero_facture', 'fournisseur__nom', 'commande__numero_commande']
    ordering_fields = ['date_facture', 'montant_total', 'statut']