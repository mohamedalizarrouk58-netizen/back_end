from django.shortcuts import render
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
from rest_framework import viewsets, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import PermissionDenied, ValidationError
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
    UserSerializer, UserProfileSerializer, ClientSerializer, CategorieMaterielSerializer, MaterielSerializer,
    DemandeMaintenanceSerializer, InterventionSerializer, FicheReparationSerializer, PieceSerializer,
    DemandePieceSerializer, FactureSerializer, PaiementSerializer, MessageSerializer, DepartmentSerializer,
    FournisseurSerializer, CommandePieceSerializer, LigneCommandePieceSerializer, PrixFournisseurSerializer,
    FactureFournisseurSerializer,
)
from .permissions import IsChefStockOrAdmin, IsAdmin, RoleWritePermission
from .realtime_messages import broadcast_message_created, broadcast_message_deleted
from .client_invoice import (
    upsert_client_facture,
    send_client_repair_invoice_email,
    compute_repair_total,
    compute_repair_breakdown,
)
from .mixins import ListQueryParamFilterMixin
from .pagination import StandardPagination
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

class UserViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = set()  # only admin can create/update/delete users
    search_fields = ['username', 'email', 'first_name', 'last_name', 'telephone']
    ordering_fields = ['username', 'date_joined', 'role']

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_active = False
        instance.save(update_fields=['is_deleted', 'is_active'])

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

    # Self-registration is restricted to suppliers. Staff accounts
    # (admin, manager, technicien, ...) must be created by an admin.
    SELF_REGISTER_ROLES = {'fournisseur'}

    @action(detail=False, methods=['post'], url_path='register', permission_classes=[AllowAny])
    def register(self, request):
        """Public self-registration endpoint (suppliers only)."""
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

        if role not in self.SELF_REGISTER_ROLES:
            return Response(
                {'detail': 'Self-registration is only available for supplier accounts. '
                           'Staff accounts must be created by an administrator.'},
                status=status.HTTP_403_FORBIDDEN
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

    def _update_current_user_profile(self, request):
        profile_serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH',
        )
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get', 'patch', 'put'], url_path='me', permission_classes=[IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        return self._update_current_user_profile(request)

    @action(
        detail=False,
        methods=['patch', 'put'],
        url_path='me/profile',
        permission_classes=[IsAuthenticated],
    )
    def update_profile(self, request):
        return self._update_current_user_profile(request)

class ClientViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Client.objects.filter(is_deleted=False)
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'receptioniste', 'manager'}
    search_fields = ['nom_complet', 'email', 'telephone', 'adresse']
    ordering_fields = ['nom_complet', 'date_creation']

    def perform_create(self, serializer):
        serializer.save(is_deleted=False)

    def perform_update(self, serializer):
        serializer.save(is_deleted=False)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


class CategorieMaterielViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = CategorieMateriel.objects.all()
    serializer_class = CategorieMaterielSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock'}
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'date_creation']

class MaterielViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Materiel.objects.filter(is_deleted=False)
    serializer_class = MaterielSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'receptioniste', 'manager'}
    search_fields = ['numero_serie', 'marque', 'modele', 'type', 'client__nom_complet']
    ordering_fields = ['date_reception', 'marque', 'modele']

    def perform_create(self, serializer):
        serializer.save(is_deleted=False)

    def perform_update(self, serializer):
        serializer.save(is_deleted=False)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


# Allowed status transitions for the maintenance workflow.
DEMANDE_TRANSITIONS = {
    'en_attente': {'en_cours', 'refuse'},
    'en_cours': {'termine', 'refuse'},
    'termine': set(),
    'refuse': {'en_attente'},
}

INTERVENTION_TRANSITIONS = {
    'en_attente': {'en_cours', 'refuse'},
    'en_cours': {'termine', 'refuse'},
    'termine': set(),
    'refuse': {'en_attente', 'en_cours'},
}


def validate_status_transition(old_status, new_status, transitions, label):
    if new_status == old_status:
        return
    allowed = transitions.get(old_status, set())
    if new_status not in allowed:
        raise ValidationError({
            'statut': f"Transition invalide pour {label}: '{old_status}' -> '{new_status}'. "
                      f"Transitions autorisées: {', '.join(sorted(allowed)) or 'aucune'}."
        })


class DemandeMaintenanceViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = DemandeMaintenance.objects.all()
    serializer_class = DemandeMaintenanceSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'receptioniste', 'manager'}
    search_fields = [
        'materiel__numero_serie', 'materiel__marque', 'materiel__modele',
        'materiel__client__nom_complet', 'receptioniste__username', 'manager__username',
    ]
    ordering_fields = ['date_creation', 'statut', 'priorite']

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self.request.user, 'role', None) == 'manager':
            qs = qs.filter(manager=self.request.user)
        return qs

    def perform_create(self, serializer):
        # Enforce server-side ownership and initial workflow status.
        serializer.save(receptioniste=self.request.user, statut='en_attente')

    def perform_update(self, serializer):
        instance = self.get_object()
        new_status = serializer.validated_data.get('statut', instance.statut)
        validate_status_transition(instance.statut, new_status, DEMANDE_TRANSITIONS, 'la demande')
        serializer.save()

    @action(detail=False, methods=['get'], url_path='me')
    def my_demandes(self, request):
        queryset = self.filter_queryset(
            DemandeMaintenance.objects.filter(receptioniste=request.user)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='envoyer-facture-client')
    @transaction.atomic
    def envoyer_facture_client(self, request, pk=None):
        """Email client invoice PDF after manager has generated the facture."""
        user_role = getattr(request.user, 'role', None)
        if user_role not in ('receptioniste', 'admin', 'administrateur'):
            return Response(
                {'detail': 'Seul le réceptionniste peut envoyer la facture au client.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        demande = self.get_object()

        if demande.statut != 'termine':
            return Response(
                {'detail': 'La facture ne peut être envoyée que lorsque la demande est terminée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            intervention = demande.intervention
        except Intervention.DoesNotExist:
            return Response(
                {'detail': 'Aucune intervention liée à cette demande.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            fiche = intervention.fiche_reparation
        except FicheReparation.DoesNotExist:
            return Response(
                {'detail': 'Aucune fiche de réparation liée à cette intervention.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not fiche.valide_manager:
            return Response(
                {'detail': 'Le manager doit valider la fiche et générer la facture avant l\'envoi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_facture = Facture.objects.filter(
            intervention=intervention, is_deleted=False,
        ).first()
        if not existing_facture:
            return Response(
                {'detail': 'Aucune facture générée. Le manager doit générer la facture depuis la fiche de réparation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        materiel = demande.materiel
        client = materiel.client

        if not client.email:
            return Response(
                {'detail': 'Le client ne possède pas une adresse email configurée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facture = upsert_client_facture(intervention, client, fiche)

        try:
            send_client_repair_invoice_email(facture, fiche, client, materiel, intervention)
        except Exception as exc:
            return Response(
                {
                    'detail': f'La facture existe mais l\'email n\'a pas pu être envoyé : {exc}',
                    'facture': FactureSerializer(facture).data,
                    'montant_total': str(facture.montant_total),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'detail': 'Facture envoyée au client par email.',
                'facture': FactureSerializer(facture).data,
                'montant_total': str(facture.montant_total),
            },
            status=status.HTTP_200_OK,
        )

class InterventionViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'manager', 'technicien'}
    search_fields = [
        'diagnostic', 'solution_proposee', 'technicien__username',
        'demande__materiel__numero_serie', 'demande__materiel__client__nom_complet',
    ]
    ordering_fields = ['date_debut', 'date_fin', 'statut']

    @transaction.atomic
    def perform_create(self, serializer):
        intervention = serializer.save()
        # Creating an intervention moves the linked request to "en cours".
        demande = intervention.demande
        if demande and demande.statut == 'en_attente':
            demande.statut = 'en_cours'
            demande.save(update_fields=['statut'])

    @transaction.atomic
    def perform_update(self, serializer):
        instance = self.get_object()
        new_status = serializer.validated_data.get('statut', instance.statut)
        validate_status_transition(instance.statut, new_status, INTERVENTION_TRANSITIONS, "l'intervention")
        intervention = serializer.save()

        # Keep the maintenance request in sync with the intervention outcome.
        demande = intervention.demande
        if demande and new_status in ('termine', 'refuse') and demande.statut != new_status:
            demande.statut = new_status
            demande.save(update_fields=['statut'])

    @action(detail=False, methods=['get'], url_path='me')
    def my_interventions(self, request):
        queryset = self.filter_queryset(
            Intervention.objects.filter(technicien=request.user)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class FicheReparationViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = FicheReparation.objects.all()
    serializer_class = FicheReparationSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'technicien', 'manager'}
    search_fields = ['description_panne', 'solution', 'intervention__demande__materiel__numero_serie']
    ordering_fields = ['id']

    @transaction.atomic
    def perform_update(self, serializer):
        instance = self.get_object()
        was_validated = instance.valide_manager
        fiche = serializer.save()

        if fiche.valide_manager and not was_validated:
            intervention = fiche.intervention
            demande = getattr(intervention, 'demande', None)
            materiel = getattr(demande, 'materiel', None) if demande else None
            client = getattr(materiel, 'client', None) if materiel else None
            if client:
                upsert_client_facture(intervention, client, fiche)

    @action(detail=True, methods=['post'], url_path='generer-facture')
    @transaction.atomic
    def generer_facture(self, request, pk=None):
        """Manager generates client invoice from validated repair sheet breakdown."""
        user_role = getattr(request.user, 'role', None)
        if user_role not in ('manager', 'admin', 'administrateur'):
            return Response(
                {'detail': 'Seul le manager peut générer la facture.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        fiche = self.get_object()
        if not fiche.valide_manager:
            return Response(
                {'detail': 'Validez la fiche de réparation avant de générer la facture.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        intervention = fiche.intervention
        demande = getattr(intervention, 'demande', None)
        materiel = getattr(demande, 'materiel', None) if demande else None
        client = getattr(materiel, 'client', None) if materiel else None

        if not client:
            return Response(
                {'detail': 'Client introuvable pour cette intervention.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facture = upsert_client_facture(intervention, client, fiche)
        return Response(
            {
                'detail': 'Facture générée avec le détail pièces, frais et montants.',
                'facture': FactureSerializer(facture).data,
                'montant_total': str(facture.montant_total),
            },
            status=status.HTTP_200_OK,
        )

class PieceViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Piece.objects.all()
    serializer_class = PieceSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock'}
    search_fields = ['nom', 'reference', 'modele', 'categorie__nom']
    ordering_fields = ['nom', 'quantite_stock', 'prix_unitaire', 'date_creation']

class DemandePieceViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = DemandePiece.objects.all()
    serializer_class = DemandePieceSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'technicien', 'manager', 'chefstock', 'fournisseur'}
    search_fields = ['piece__nom', 'piece__reference', 'fiche__intervention__demande__materiel__numero_serie']
    ordering_fields = ['date_demande', 'statut']

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

    @action(detail=True, methods=['post'], url_path='livrer-stock')
    def livrer_stock(self, request, pk=None):
        """Deliver a request from existing stock: decrement atomically."""
        user_role = getattr(request.user, 'role', None)
        if user_role not in ('chefstock', 'admin'):
            return Response(
                {'detail': 'Seul le chef de stock ou un administrateur peut livrer depuis le stock.'},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            demande = (
                DemandePiece.objects.select_for_update()
                .select_related('piece')
                .get(pk=pk)
            )

            if demande.statut not in ('demandee',):
                return Response(
                    {'detail': f"Impossible de livrer une demande au statut '{demande.statut}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            piece = Piece.objects.select_for_update().get(pk=demande.piece_id)
            if piece.quantite_stock < demande.quantite:
                return Response(
                    {'detail': f'Stock insuffisant ({piece.quantite_stock} disponible, '
                               f'{demande.quantite} demandé). Commandez la pièce.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            piece.quantite_stock -= demande.quantite
            piece.save()

            demande.statut = 'livree'
            demande.quantite_manquante = 0
            demande.save(update_fields=['statut', 'quantite_manquante'])

        return Response(self.get_serializer(demande).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assigner-fournisseur')
    @transaction.atomic
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
    @transaction.atomic
    def reponse_fournisseur(self, request, pk=None):
        demande = self.get_object()
        
        user_role = getattr(request.user, 'role', None)
        if user_role not in ['fournisseur', 'chefstock', 'admin']:
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
    @transaction.atomic
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
            montant_livraison = Decimal(str(prix)) * Decimal(str(quantite_livree))
            facture_existante = FactureFournisseur.objects.filter(commande=demande.commande).first()
            if facture_existante:
                # Partial deliveries accumulate on the same invoice.
                facture_existante.montant_total += montant_livraison
                facture_existante.statut = 'validee' if demande.statut == 'livree' else 'brouillon'
                facture_existante.save(update_fields=['montant_total', 'statut'])
            else:
                numero_facture = request.data.get('numero_facture') or f"FF-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
                FactureFournisseur.objects.create(
                    commande=demande.commande,
                    numero_facture=numero_facture,
                    fournisseur=demande.fournisseur,
                    montant_total=montant_livraison,
                    statut='validee' if demande.statut == 'livree' else 'brouillon',
                )

        return Response(self.get_serializer(demande).data, status=status.HTTP_200_OK)

class FactureViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Facture.objects.filter(is_deleted=False)
    serializer_class = FactureSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'receptioniste', 'manager'}
    search_fields = ['client__nom_complet', 'client__email', 'intervention__demande__materiel__numero_serie']
    ordering_fields = ['date_facture', 'montant_total', 'est_payee']

    def perform_create(self, serializer):
        intervention = serializer.validated_data.get('intervention')
        client = serializer.validated_data.get('client')

        if intervention and not client:
            demande = getattr(intervention, 'demande', None)
            materiel = getattr(demande, 'materiel', None) if demande else None
            if materiel and materiel.client_id:
                client = materiel.client

        fiche = FicheReparation.objects.filter(intervention=intervention).first()
        extra = {'is_deleted': False}
        if client:
            extra['client'] = client

        if fiche:
            breakdown = compute_repair_breakdown(fiche)
            extra.update(breakdown)
        elif not serializer.validated_data.get('montant_total'):
            raise ValidationError({
                'intervention': 'Aucune fiche de réparation trouvée pour calculer le montant.',
            })

        if not extra.get('client'):
            raise ValidationError({
                'client': 'Client requis ou introuvable pour cette intervention.',
            })

        serializer.save(**extra)

    def perform_update(self, serializer):
        serializer.save(is_deleted=False)

    @action(detail=True, methods=['post'], url_path='envoyer-email-client')
    @transaction.atomic
    def envoyer_email_client(self, request, pk=None):
        """Receptionist emails the manager-generated invoice PDF to the client."""
        user_role = getattr(request.user, 'role', None)
        if user_role not in ('receptioniste', 'admin', 'administrateur'):
            return Response(
                {'detail': 'Seul le réceptionniste peut envoyer la facture au client.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        facture = self.get_object()
        intervention = facture.intervention

        try:
            fiche = intervention.fiche_reparation
        except FicheReparation.DoesNotExist:
            return Response(
                {'detail': 'Aucune fiche de réparation liée à cette facture.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        demande = getattr(intervention, 'demande', None)
        if not demande or demande.statut != 'termine':
            return Response(
                {'detail': 'La demande doit être terminée avant l\'envoi de la facture.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not fiche.valide_manager:
            return Response(
                {'detail': 'La fiche doit être validée par le manager avant l\'envoi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        materiel = demande.materiel
        client = facture.client

        if not client.email:
            return Response(
                {'detail': 'Le client ne possède pas une adresse email configurée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facture = upsert_client_facture(intervention, client, fiche)

        try:
            send_client_repair_invoice_email(facture, fiche, client, materiel, intervention)
        except Exception as exc:
            return Response(
                {'detail': f'Échec de l\'envoi email : {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'detail': 'Facture envoyée au client par email.',
                'facture': FactureSerializer(facture).data,
            },
            status=status.HTTP_200_OK,
        )

    def perform_destroy(self, instance):
        user_role = getattr(self.request.user, 'role', None)
        if user_role == 'receptioniste' and not instance.est_payee:
            raise ValidationError('Seule une facture payée peut être supprimée.')
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


def _sync_facture_paiement(facture):
    """Recompute est_payee from the sum of recorded payments."""
    total_paye = facture.paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0')
    est_payee = total_paye >= facture.montant_total
    if facture.est_payee != est_payee:
        facture.est_payee = est_payee
        facture.save(update_fields=['est_payee'])


class PaiementViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'receptioniste', 'manager'}
    search_fields = ['facture__client__nom_complet', 'mode_paiement']
    ordering_fields = ['date_paiement', 'montant']

    @transaction.atomic
    def perform_create(self, serializer):
        paiement = serializer.save()
        _sync_facture_paiement(paiement.facture)

    @transaction.atomic
    def perform_update(self, serializer):
        paiement = serializer.save()
        _sync_facture_paiement(paiement.facture)

    @transaction.atomic
    def perform_destroy(self, instance):
        facture = instance.facture
        instance.delete()
        _sync_facture_paiement(facture)


class MessageViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    pagination_class = StandardPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ['objet', 'contenu', 'expediteur__username', 'destinataire__username']
    ordering_fields = ['date_envoi']

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(expediteur=user) | Q(destinataire=user)
        ).order_by('-date_envoi')

    @transaction.atomic
    def perform_create(self, serializer):
        destinataire = serializer.validated_data.get('destinataire')

        if not destinataire:
            raise ValidationError({'destinataire': 'This field is required.'})

        if destinataire == self.request.user:
            raise ValidationError({'destinataire': 'You cannot send a message to yourself.'})

        if getattr(destinataire, 'is_deleted', False):
            raise ValidationError({'destinataire': 'Invalid destinataire.'})

        message = serializer.save(expediteur=self.request.user)
        broadcast_message_created(message, self.request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.expediteur_id != user.id:
            raise PermissionDenied('Only the sender can delete this message.')

        if instance.is_deleted:
            return

        if instance.fichier:
            instance.fichier.delete(save=False)

        instance.fichier = None
        instance.contenu = ''
        instance.type_message = Message.TYPE_TEXT
        instance.is_deleted = True
        instance.save(update_fields=['fichier', 'contenu', 'type_message', 'is_deleted'])
        broadcast_message_deleted(instance, self.request)

class DepartmentViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = set()  # only admin can manage departments
    search_fields = ['nom_dept', 'description']
    ordering_fields = ['nom_dept', 'date_creation']

    def list(self, request, *args, **kwargs):
        from .department_policy import MAX_SOCIETY_DEPARTMENTS

        response = super().list(request, *args, **kwargs)
        payload = response.data
        if isinstance(payload, dict):
            payload['max_departments'] = MAX_SOCIETY_DEPARTMENTS
            payload['can_create'] = Department.objects.count() < MAX_SOCIETY_DEPARTMENTS
        return response


# ===== MODULE D'ACHAT DE PIECES =====

class FournisseurViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    """ViewSet pour gérer les fournisseurs"""
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock'}
    search_fields = ['nom', 'email', 'telephone']
    ordering_fields = ['nom', 'date_creation']


class CommandePieceViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    """ViewSet pour gérer les commandes de pièces"""
    queryset = CommandePiece.objects.filter(is_deleted=False)
    serializer_class = CommandePieceSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock', 'fournisseur'}
    search_fields = ['numero_commande', 'fournisseur__nom']
    ordering_fields = ['date_commande', 'statut', 'montant_total']

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    def perform_create(self, serializer):
        serializer.save(statut='brouillon')

    @action(detail=True, methods=['post'])
    def calculer_montant(self, request, pk=None):
        """Action personnalisée pour calculer le montant total d'une commande"""
        commande = self.get_object()
        montant = commande.calculer_montant_total()
        return Response({'montant_total': montant}, status=status.HTTP_200_OK)


class LigneCommandePieceViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    """ViewSet pour gérer les lignes de commande"""
    queryset = LigneCommandePiece.objects.all()
    serializer_class = LigneCommandePieceSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock'}
    search_fields = ['commande__numero_commande', 'piece__nom']


class PrixFournisseurViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    """ViewSet pour gérer les prix fournisseurs"""
    queryset = PrixFournisseur.objects.filter(est_actif=True)
    serializer_class = PrixFournisseurSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock', 'fournisseur'}
    search_fields = ['piece__nom', 'fournisseur__nom']
    ordering_fields = ['prix', 'delai_livraison_jours']


class FactureFournisseurViewSet(ListQueryParamFilterMixin, viewsets.ModelViewSet):
    """ViewSet pour les factures fournisseurs"""
    queryset = FactureFournisseur.objects.all()
    serializer_class = FactureFournisseurSerializer
    permission_classes = [IsAuthenticated, RoleWritePermission]
    write_roles = {'chefstock'}
    search_fields = ['numero_facture', 'fournisseur__nom', 'commande__numero_commande']
    ordering_fields = ['date_facture', 'montant_total', 'statut']
