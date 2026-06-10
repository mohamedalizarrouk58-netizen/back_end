from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    User, Department, Client, Materiel, CategorieMateriel,
    DemandeMaintenance, Intervention, FicheReparation,
    Piece, DemandePiece, Facture, Paiement,
    Fournisseur, CommandePiece,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username, role, **kwargs):
    return User.objects.create_user(
        username=username, password='testpass123', email=f'{username}@test.com',
        role=role, **kwargs,
    )


def auth_header(user):
    token = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

class AuthTests(APITestCase):
    def setUp(self):
        self.admin = make_user('admin1', 'admin')
        self.manager = make_user('manager1', 'manager')

    def test_login_returns_tokens(self):
        resp = self.client.post('/api/auth/send-2fa-otp/', {
            'username': 'admin1', 'password': 'testpass123'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # No 2FA — tokens returned directly
        self.assertFalse(data.get('requires_2fa'))
        self.assertIn('access', data)

    def test_login_wrong_credentials(self):
        resp = self.client.post('/api/auth/send-2fa-otp/', {
            'username': 'admin1', 'password': 'wrong'
        })
        self.assertEqual(resp.status_code, 401)

    def test_me_endpoint_returns_current_user(self):
        resp = self.client.get('/api/users/me/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], 'admin1')
        self.assertEqual(resp.json()['role'], 'admin')


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

class RegistrationTests(APITestCase):
    def test_supplier_self_registration_allowed(self):
        resp = self.client.post('/api/users/register/', {
            'username': 'supplier1',
            'password': 'pass1234',
            'email': 'supplier1@test.com',
            'role': 'fournisseur',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='supplier1').exists())

    def test_admin_self_registration_blocked(self):
        resp = self.client.post('/api/users/register/', {
            'username': 'badactor',
            'password': 'pass1234',
            'email': 'bad@test.com',
            'role': 'admin',
        })
        self.assertEqual(resp.status_code, 403)

    def test_manager_self_registration_blocked(self):
        resp = self.client.post('/api/users/register/', {
            'username': 'badmanager',
            'password': 'pass1234',
            'email': 'bm@test.com',
            'role': 'manager',
        })
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Role permission tests
# ---------------------------------------------------------------------------

class RolePermissionTests(APITestCase):
    def setUp(self):
        self.admin = make_user('admin2', 'admin')
        self.manager = make_user('manager2', 'manager')
        self.technicien = make_user('tech2', 'technicien')
        self.receptioniste = make_user('recep2', 'receptioniste')
        self.chefstock = make_user('chef2', 'chefstock')

    # --- Users ---
    def test_admin_can_list_users(self):
        resp = self.client.get('/api/users/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, 200)

    def test_manager_can_read_users(self):
        resp = self.client.get('/api/users/', **auth_header(self.manager))
        self.assertEqual(resp.status_code, 200)

    def test_manager_cannot_create_user(self):
        resp = self.client.post('/api/users/', {
            'username': 'newuser', 'password': 'pass', 'email': 'n@n.com', 'role': 'technicien'
        }, **auth_header(self.manager))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_user(self):
        resp = self.client.post('/api/users/', {
            'username': 'createdbyAdmin', 'password': 'pass1234',
            'email': 'cba@test.com', 'role': 'technicien',
        }, **auth_header(self.admin), content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    # --- Pieces ---
    def test_chefstock_can_create_piece(self):
        cat = CategorieMateriel.objects.create(nom='Test Cat')
        resp = self.client.post('/api/pieces/', {
            'nom': 'Pièce A', 'quantite_stock': 10,
            'prix_unitaire': '25.00', 'categorie': cat.id,
        }, **auth_header(self.chefstock), content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    def test_technicien_cannot_create_piece(self):
        resp = self.client.post('/api/pieces/', {
            'nom': 'Pièce B', 'quantite_stock': 5, 'prix_unitaire': '10.00',
        }, **auth_header(self.technicien), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    # --- Unauthenticated ---
    def test_unauthenticated_cannot_access_api(self):
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Maintenance workflow tests
# ---------------------------------------------------------------------------

class MaintenanceWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = make_user('admin3', 'admin')
        self.manager = make_user('manager3', 'manager')
        self.technicien = make_user('tech3', 'technicien')
        self.receptioniste = make_user('recep3', 'receptioniste')

        self.client_obj = Client.objects.create(nom_complet='Client Test', email='c@c.com')
        self.materiel = Materiel.objects.create(
            client=self.client_obj, type='PC', marque='Dell',
            modele='XPS', numero_serie='SN001',
        )
        self.demande = DemandeMaintenance.objects.create(
            materiel=self.materiel,
            receptioniste=self.receptioniste,
            manager=self.manager,
            priorite='haute',
            statut='en_attente',
        )

    def test_creating_intervention_moves_demande_to_en_cours(self):
        resp = self.client.post('/api/interventions/', {
            'demande': self.demande.id,
            'technicien': self.technicien.id,
            'statut': 'en_attente',
        }, **auth_header(self.manager), content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_cours')

    def test_invalid_status_transition_rejected(self):
        """Cannot jump from en_attente directly to termine."""
        resp = self.client.patch(
            f'/api/demande-maintenances/{self.demande.id}/',
            {'statut': 'termine'},
            **auth_header(self.manager),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('statut', resp.json())

    def test_valid_status_transition_accepted(self):
        """en_attente -> en_cours is valid."""
        resp = self.client.patch(
            f'/api/demande-maintenances/{self.demande.id}/',
            {'statut': 'en_cours'},
            **auth_header(self.manager),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['statut'], 'en_cours')


# ---------------------------------------------------------------------------
# Stock workflow tests
# ---------------------------------------------------------------------------

class StockWorkflowTests(APITestCase):
    def setUp(self):
        self.chefstock = make_user('chef3', 'chefstock')
        self.technicien = make_user('tech4', 'technicien')
        self.cat = CategorieMateriel.objects.create(nom='Catégorie Test')
        self.piece = Piece.objects.create(
            nom='Résistance 100Ω', quantite_stock=20, prix_unitaire='5.00',
        )
        self.fiche = FicheReparation.objects.create(
            intervention=self._make_intervention(),
            description_panne='Panne test',
        )
        self.demande = DemandePiece.objects.create(
            fiche=self.fiche,
            piece=self.piece,
            quantite=5,
            statut='demandee',
        )

    def _make_intervention(self):
        admin = make_user('admin_stk', 'admin')
        manager = make_user('mgr_stk', 'manager')
        recep = make_user('rec_stk', 'receptioniste')
        client_obj = Client.objects.create(nom_complet='Stock Client')
        mat = Materiel.objects.create(
            client=client_obj, type='Server', marque='HP',
            modele='DL380', numero_serie='SRV001',
        )
        dem = DemandeMaintenance.objects.create(
            materiel=mat, receptioniste=recep, manager=manager,
            statut='en_cours', priorite='haute',
        )
        tech = make_user('tech_stk', 'technicien')
        return Intervention.objects.create(
            demande=dem, technicien=tech, statut='en_cours',
        )

    def test_livrer_stock_decrements_piece(self):
        resp = self.client.post(
            f'/api/demande-pieces/{self.demande.id}/livrer-stock/',
            **auth_header(self.chefstock),
        )
        self.assertEqual(resp.status_code, 200)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite_stock, 15)  # 20 - 5
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'livree')

    def test_livrer_stock_blocked_when_insufficient(self):
        self.piece.quantite_stock = 2
        self.piece.save()
        resp = self.client.post(
            f'/api/demande-pieces/{self.demande.id}/livrer-stock/',
            **auth_header(self.chefstock),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Stock insuffisant', resp.json().get('detail', ''))

    def test_technicien_cannot_livrer_stock(self):
        resp = self.client.post(
            f'/api/demande-pieces/{self.demande.id}/livrer-stock/',
            **auth_header(self.technicien),
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Payment / invoice sync tests
# ---------------------------------------------------------------------------

class PaiementSyncTests(APITestCase):
    def setUp(self):
        self.manager = make_user('mgr_pay', 'manager')
        self.recep = make_user('rec_pay', 'receptioniste')
        client_obj = Client.objects.create(nom_complet='Pay Client')
        mat = Materiel.objects.create(
            client=client_obj, type='PC', marque='Lenovo',
            modele='T14', numero_serie='SN-PAY',
        )
        dem = DemandeMaintenance.objects.create(
            materiel=mat, receptioniste=self.recep, manager=self.manager,
            statut='en_cours', priorite='moyenne',
        )
        tech = make_user('tech_pay', 'technicien')
        interv = Intervention.objects.create(demande=dem, technicien=tech, statut='en_cours')
        self.facture = Facture.objects.create(
            intervention=interv, client=client_obj,
            montant_total=Decimal('1000.00'),
        )

    def test_payment_marks_invoice_paid(self):
        self.assertFalse(self.facture.est_payee)
        self.client.post('/api/paiements/', {
            'facture': self.facture.id,
            'montant': '1000.00',
            'mode_paiement': 'virement',
        }, **auth_header(self.recep), content_type='application/json')
        self.facture.refresh_from_db()
        self.assertTrue(self.facture.est_payee)

    def test_partial_payment_does_not_mark_paid(self):
        self.client.post('/api/paiements/', {
            'facture': self.facture.id,
            'montant': '400.00',
            'mode_paiement': 'especes',
        }, **auth_header(self.recep), content_type='application/json')
        self.facture.refresh_from_db()
        self.assertFalse(self.facture.est_payee)


# ---------------------------------------------------------------------------
# Soft-delete tests
# ---------------------------------------------------------------------------

class SoftDeleteTests(APITestCase):
    def setUp(self):
        self.admin = make_user('admin_del', 'admin')
        self.receptioniste = make_user('recep_del', 'receptioniste')
        self.client_obj = Client.objects.create(nom_complet='Delete Me', email='del@del.com')

    def test_client_delete_is_soft(self):
        resp = self.client.delete(
            f'/api/clients/{self.client_obj.id}/',
            **auth_header(self.receptioniste),
        )
        self.assertEqual(resp.status_code, 204)
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_deleted)

    def test_soft_deleted_client_not_in_list(self):
        self.client_obj.is_deleted = True
        self.client_obj.save()
        resp = self.client.get('/api/clients/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        items = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        ids = [item['id'] for item in items]
        self.assertNotIn(self.client_obj.id, ids)

    def test_user_delete_is_soft(self):
        target = make_user('deleteable', 'technicien')
        resp = self.client.delete(
            f'/api/users/{target.id}/',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, 204)
        target.refresh_from_db()
        self.assertTrue(target.is_deleted)
        self.assertFalse(target.is_active)


# ---------------------------------------------------------------------------
# Department limit tests
# ---------------------------------------------------------------------------

class DepartmentLimitTests(APITestCase):
    def setUp(self):
        self.admin = make_user('admin_dept', 'admin')
        Department.objects.all().delete()

    def test_cannot_exceed_five_departments(self):
        for index in range(5):
            Department.objects.create(nom_dept=f'Dept {index}', description='Test')

        resp = self.client.post(
            '/api/departments/',
            {'nom_dept': 'Dept sixth', 'description': 'Too many'},
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_includes_department_limits(self):
        Department.objects.create(nom_dept='Unique Dept', description='One')

        resp = self.client.get('/api/departments/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload.get('max_departments'), 5)
        self.assertTrue(payload.get('can_create'))
