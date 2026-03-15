from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'clients', views.ClientViewSet)
router.register(r'materiels', views.MaterielViewSet)
router.register(r'demande-maintenances', views.DemandeMaintenanceViewSet)
router.register(r'interventions', views.InterventionViewSet)
router.register(r'fiche-reparations', views.FicheReparationViewSet)
router.register(r'pieces', views.PieceViewSet)
router.register(r'demande-pieces', views.DemandePieceViewSet)
router.register(r'factures', views.FactureViewSet)
router.register(r'paiements', views.PaiementViewSet)
router.register(r'messages', views.MessageViewSet)

urlpatterns = [
    path("hello/", views.hello, name='hello'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]
