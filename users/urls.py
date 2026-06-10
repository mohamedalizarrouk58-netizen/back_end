from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'clients', views.ClientViewSet)
router.register(r'categories-materiel', views.CategorieMaterielViewSet)
router.register(r'materiels', views.MaterielViewSet)
router.register(r'demande-maintenances', views.DemandeMaintenanceViewSet)
router.register(r'interventions', views.InterventionViewSet)
router.register(r'fiche-reparations', views.FicheReparationViewSet)
router.register(r'pieces', views.PieceViewSet)
router.register(r'demande-pieces', views.DemandePieceViewSet)
router.register(r'factures', views.FactureViewSet)
router.register(r'paiements', views.PaiementViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'departments', views.DepartmentViewSet)
# Module d'achat de pièces
router.register(r'fournisseurs', views.FournisseurViewSet)
router.register(r'commandes-pieces', views.CommandePieceViewSet)
router.register(r'lignes-commandes', views.LigneCommandePieceViewSet)
router.register(r'prix-fournisseurs', views.PrixFournisseurViewSet)
router.register(r'factures-fournisseurs', views.FactureFournisseurViewSet)

urlpatterns = [
    path("hello/", views.hello, name='hello'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
    # OTP / Email Auth
    path('api/auth/send-otp/', views.send_otp, name='send_otp'),
    path('api/auth/reset-password/', views.verify_otp_reset_password, name='reset_password'),
    path('api/auth/login-2fa/', views.login_with_2fa, name='login_2fa'),
    path('api/auth/toggle-2fa/', views.toggle_2fa, name='toggle_2fa'),
    path('api/auth/2fa-status/', views.get_2fa_status, name='2fa_status'),
    path('api/auth/send-2fa-otp/', views.send_2fa_otp_for_login, name='send_2fa_otp'),
]
