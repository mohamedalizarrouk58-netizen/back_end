"""
Seed demo data (~100 records per model).

Usage:
  python manage.py seed_demo_data --count 100     # insert demo rows
  python manage.py seed_demo_data --clear          # remove demo rows only (keeps real data)
"""
from decimal import Decimal
from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import (
    User, Department, Client, CategorieMateriel, Materiel,
    DemandeMaintenance, Intervention, FicheReparation, Piece, DemandePiece,
    Facture, Paiement, Message, Fournisseur, CommandePiece,
    LigneCommandePiece, PrixFournisseur, FactureFournisseur, OTPCode,
)

SEED_PASSWORD = 'SeedPass123!'
SEED_EMAIL_DOMAIN = 'demo.gmao.test'

DEMANDE_STATUTS = ['en_attente', 'en_cours', 'termine', 'refuse']
INTERVENTION_STATUTS = ['en_attente', 'en_cours', 'termine', 'refuse']
DEMANDE_PIECE_STATUTS = ['demandee', 'livree', 'hors_stock', 'commandee']
COMMANDE_STATUTS = ['brouillon', 'en_attente_fournisseur', 'acceptee_fournisseur', 'commande', 'livree']
PRIORITES = ['faible', 'moyenne', 'haute']
PAIEMENT_MODES = ['especes', 'cheque', 'virement']
FACTURE_FOURNISSEUR_STATUTS = ['brouillon', 'validee', 'payee']

PANNE_SAMPLES = [
    'Écran fissé', 'Ne charge plus', 'Surchauffe', 'Bruit disque dur',
    'Clavier défectueux', 'Wi-Fi instable', 'Batterie faible', 'Port USB cassé',
]
SOLUTION_SAMPLES = [
    'Remplacement pièce', 'Nettoyage interne', 'Mise à jour logicielle',
    'Réparation carte mère', 'Changement batterie', 'Réinstallation OS',
]


class Command(BaseCommand):
    help = 'Generate large demo datasets (~100 rows per model).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of records to create per model (default: 100).',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove demo/seed data only (keeps your real records). Does not insert new demo rows.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            with transaction.atomic():
                removed = self._clear_seed_data()
            self.stdout.write(self.style.SUCCESS('Demo seed data removed. Your real records were kept.'))
            for label, n in removed.items():
                if n:
                    self.stdout.write(f'  removed {label}: {n}')
            return

        count = max(1, options['count'])
        with transaction.atomic():
            stats = self._seed_all(count)

        self.stdout.write(self.style.SUCCESS('Demo data seed complete:'))
        for label, n in stats.items():
            self.stdout.write(f'  {label}: {n}')

    def _clear_seed_data(self):
        """Delete seed records in dependency-safe order. Real data is untouched."""
        removed = {}

        def _del(label, qs):
            count, _ = qs.delete()
            removed[label] = count
            return count

        _del('FactureFournisseur', FactureFournisseur.objects.filter(numero_facture__startswith='SEED-FF-'))
        _del('LigneCommandePiece', LigneCommandePiece.objects.filter(commande__numero_commande__startswith='SEED-CMD-'))
        _del('CommandePiece', CommandePiece.objects.filter(numero_commande__startswith='SEED-CMD-'))
        _del('PrixFournisseur', PrixFournisseur.objects.filter(piece__reference__startswith='SEED-PIECE-'))
        _del('OTPCode', OTPCode.objects.filter(user__username__startswith='seed_'))
        _del('Message', Message.objects.filter(expediteur__username__startswith='seed_'))
        _del('Paiement', Paiement.objects.filter(facture__client__email__endswith=SEED_EMAIL_DOMAIN))
        _del('Facture', Facture.objects.filter(client__email__endswith=SEED_EMAIL_DOMAIN))
        _del('DemandePiece', DemandePiece.objects.filter(piece__reference__startswith='SEED-PIECE-'))
        _del('FicheReparation', FicheReparation.objects.filter(intervention__demande__materiel__numero_serie__startswith='SEED-SN-'))
        _del('Intervention', Intervention.objects.filter(demande__materiel__numero_serie__startswith='SEED-SN-'))
        _del('DemandeMaintenance', DemandeMaintenance.objects.filter(materiel__numero_serie__startswith='SEED-SN-'))
        _del('Materiel', Materiel.objects.filter(numero_serie__startswith='SEED-SN-'))
        _del('Piece', Piece.objects.filter(reference__startswith='SEED-PIECE-'))
        _del('Client', Client.objects.filter(email__endswith=SEED_EMAIL_DOMAIN))
        _del('CategorieMateriel', CategorieMateriel.objects.filter(nom__startswith='Seed Cat '))
        _del('Fournisseur', Fournisseur.objects.filter(nom__startswith='Seed Fournisseur '))
        _del('User', User.objects.filter(username__startswith='seed_'))
        _del('Department', Department.objects.filter(nom_dept__startswith='Seed Dept '))

        return removed

    def _seed_all(self, count):
        stats = {}
        now = timezone.now()
        roles = ['receptioniste', 'manager', 'technicien', 'chefstock', 'fournisseur', 'admin']

        # Departments
        departments = []
        for i in range(1, count + 1):
            departments.append(Department(
                nom_dept=f'Seed Dept {i:03d}',
                description=f'Department demo #{i}',
            ))
        Department.objects.bulk_create(departments, ignore_conflicts=True)
        departments = list(Department.objects.filter(nom_dept__startswith='Seed Dept ').order_by('id')[:count])
        stats['Department'] = len(departments)

        # Users
        users = []
        for i in range(1, count + 1):
            role = roles[i % len(roles)]
            dept = departments[i % len(departments)] if departments else None
            user = User(
                username=f'seed_{role}_{i:03d}',
                email=f'seed_{role}_{i:03d}@{SEED_EMAIL_DOMAIN}',
                first_name=f'Seed{i}',
                last_name=role.capitalize(),
                role=role,
                department=dept,
                telephone=f'+216{random.randint(20000000, 99999999)}',
                is_deleted=False,
            )
            user.set_password(SEED_PASSWORD)
            users.append(user)
        User.objects.bulk_create(users, ignore_conflicts=True)
        users = list(User.objects.filter(username__startswith='seed_').order_by('id'))
        stats['User'] = len(users)

        by_role = {r: [u for u in users if u.role == r] for r in roles}

        # Clients
        clients = []
        for i in range(1, count + 1):
            clients.append(Client(
                nom_complet=f'Seed Client {i:03d}',
                email=f'seed_client_{i:03d}@{SEED_EMAIL_DOMAIN}',
                telephone=f'+216{random.randint(20000000, 99999999)}',
                adresse=f'{i} Rue Demo, Tunis',
                is_deleted=False,
            ))
        Client.objects.bulk_create(clients, ignore_conflicts=True)
        clients = list(Client.objects.filter(email__endswith=SEED_EMAIL_DOMAIN).order_by('id')[:count])
        stats['Client'] = len(clients)

        # Categories
        categories = []
        for i in range(1, count + 1):
            categories.append(CategorieMateriel(
                nom=f'Seed Cat {i:03d}',
                description=f'Category demo #{i}',
                is_active=True,
            ))
        CategorieMateriel.objects.bulk_create(categories, ignore_conflicts=True)
        categories = list(CategorieMateriel.objects.filter(nom__startswith='Seed Cat ').order_by('id')[:count])
        stats['CategorieMateriel'] = len(categories)

        # Pieces
        pieces = []
        types_piece = ['RAM', 'SSD', 'Écran', 'Batterie', 'Clavier', 'Carte mère', 'Ventilateur']
        for i in range(1, count + 1):
            pieces.append(Piece(
                nom=f'Seed Pièce {i:03d}',
                reference=f'SEED-PIECE-{i:04d}',
                modele=f'MDL-{i:03d}',
                categorie=categories[i % len(categories)],
                quantite_stock=random.randint(0, 200),
                seuil_alerte=random.randint(1, 10),
                prix_unitaire=Decimal(str(random.randint(15, 850))),
            ))
        Piece.objects.bulk_create(pieces, ignore_conflicts=True)
        pieces = list(Piece.objects.filter(reference__startswith='SEED-PIECE-').order_by('id')[:count])
        stats['Piece'] = len(pieces)

        # Fournisseurs (+ link some to fournisseur users)
        fournisseurs = []
        fournisseur_users = by_role.get('fournisseur', [])
        for i in range(1, count + 1):
            fu = fournisseur_users[i % len(fournisseur_users)] if fournisseur_users else None
            fournisseurs.append(Fournisseur(
                nom=f'Seed Fournisseur {i:03d}',
                utilisateur=fu if i <= len(fournisseur_users) else None,
                email=f'seed_fournisseur_{i:03d}@{SEED_EMAIL_DOMAIN}',
                telephone=f'+216{random.randint(20000000, 99999999)}',
                adresse=f'Zone industrielle {i}',
                ville=random.choice(['Tunis', 'Sfax', 'Sousse', 'Nabeul']),
                code_postal=f'{1000 + i}',
                pays='Tunisie',
                contact_principal=f'Contact {i}',
                est_actif=True,
            ))
        Fournisseur.objects.bulk_create(fournisseurs, ignore_conflicts=True)
        fournisseurs = list(Fournisseur.objects.filter(nom__startswith='Seed Fournisseur ').order_by('id')[:count])
        stats['Fournisseur'] = len(fournisseurs)

        # Materiels
        materiel_types = ['Laptop', 'Desktop', 'Printer', 'Tablet', 'Server']
        brands = ['Dell', 'HP', 'Lenovo', 'Asus', 'Apple', 'Acer']
        materiels = []
        for i in range(1, count + 1):
            materiels.append(Materiel(
                client=clients[i % len(clients)],
                type=random.choice(materiel_types),
                marque=random.choice(brands),
                modele=f'Model-{i:03d}',
                numero_serie=f'SEED-SN-{i:05d}',
                etat=random.choice(['Reçu', 'En réparation', 'Réparé', 'Livré']),
                is_deleted=False,
            ))
        Materiel.objects.bulk_create(materiels, ignore_conflicts=True)
        materiels = list(Materiel.objects.filter(numero_serie__startswith='SEED-SN-').order_by('id')[:count])
        stats['Materiel'] = len(materiels)

        receptionistes = by_role.get('receptioniste', users)
        managers = by_role.get('manager', users)
        techniciens = by_role.get('technicien', users)
        chefstocks = by_role.get('chefstock', users)

        # Demandes maintenance
        demandes = []
        for i in range(1, count + 1):
            demandes.append(DemandeMaintenance(
                materiel=materiels[i - 1],
                receptioniste=receptionistes[i % len(receptionistes)],
                manager=managers[i % len(managers)],
                priorite=random.choice(PRIORITES),
                statut=random.choice(DEMANDE_STATUTS),
            ))
        DemandeMaintenance.objects.bulk_create(demandes)
        demandes = list(
            DemandeMaintenance.objects.filter(materiel__numero_serie__startswith='SEED-SN-')
            .order_by('id')[:count]
        )
        stats['DemandeMaintenance'] = len(demandes)

        # Interventions (1:1 demandes)
        interventions = []
        for i, demande in enumerate(demandes):
            interventions.append(Intervention(
                demande=demande,
                technicien=techniciens[i % len(techniciens)],
                diagnostic=f'Diagnostic seed #{i + 1}: {random.choice(PANNE_SAMPLES)}',
                solution_proposee=random.choice(SOLUTION_SAMPLES),
                date_debut=now - timedelta(days=random.randint(1, 60)),
                date_fin=now - timedelta(days=random.randint(0, 30)) if demande.statut == 'termine' else None,
                statut=random.choice(INTERVENTION_STATUTS),
            ))
        Intervention.objects.bulk_create(interventions)
        interventions = list(
            Intervention.objects.filter(demande__in=demandes).order_by('id')[:count]
        )
        stats['Intervention'] = len(interventions)

        # Fiches réparation
        fiches = []
        for i, intervention in enumerate(interventions):
            labor = Decimal(str(random.randint(30, 250)))
            society = Decimal(str(random.randint(10, 80)))
            extra = Decimal(str(random.randint(0, 120)))
            fiches.append(FicheReparation(
                intervention=intervention,
                description_panne=random.choice(PANNE_SAMPLES),
                solution=random.choice(SOLUTION_SAMPLES),
                cout_main_oeuvre=labor,
                frais_societe=society,
                prix_supplementaire=extra,
                confirmation=random.choice([True, False]),
                valide_manager=random.choice([True, False]),
            ))
        FicheReparation.objects.bulk_create(fiches)
        fiches = list(
            FicheReparation.objects.filter(intervention__in=interventions).order_by('id')[:count]
        )
        stats['FicheReparation'] = len(fiches)

        # Demande pièces
        demande_pieces = []
        for i in range(1, count + 1):
            fiche = fiches[i % len(fiches)]
            piece = pieces[i % len(pieces)]
            qty = random.randint(1, 5)
            demande_pieces.append(DemandePiece(
                fiche=fiche,
                piece=piece,
                quantite=qty,
                quantite_manquante=max(0, qty - piece.quantite_stock),
                demandeur_stock=chefstocks[i % len(chefstocks)] if chefstocks else None,
                fournisseur=fournisseurs[i % len(fournisseurs)],
                statut=random.choice(DEMANDE_PIECE_STATUTS),
            ))
        DemandePiece.objects.bulk_create(demande_pieces)
        stats['DemandePiece'] = count

        # Factures client
        factures = []
        for i, intervention in enumerate(interventions):
            fiche = fiches[i]
            client = intervention.demande.materiel.client
            pieces_amt = Decimal(str(fiche.cout_pieces() or 0))
            labor = Decimal(str(fiche.cout_main_oeuvre or 0))
            society = Decimal(str(fiche.frais_societe or 0))
            extra = Decimal(str(fiche.prix_supplementaire or 0))
            total = pieces_amt + labor + society + extra
            factures.append(Facture(
                intervention=intervention,
                client=client,
                montant_pieces=pieces_amt,
                montant_main_oeuvre=labor,
                montant_frais_societe=society,
                montant_supplementaire=extra,
                montant_total=total,
                est_payee=random.choice([True, False]),
                email_client_envoye=random.choice([True, False]),
                is_deleted=False,
            ))
        Facture.objects.bulk_create(factures)
        factures = list(Facture.objects.filter(client__email__endswith=SEED_EMAIL_DOMAIN).order_by('id')[:count])
        stats['Facture'] = len(factures)

        # Paiements
        paiements = []
        for i in range(1, count + 1):
            facture = factures[i % len(factures)]
            montant = facture.montant_total if i % 3 == 0 else (facture.montant_total / 2)
            paiements.append(Paiement(
                facture=facture,
                montant=montant,
                mode_paiement=random.choice(PAIEMENT_MODES),
            ))
        Paiement.objects.bulk_create(paiements)
        stats['Paiement'] = count

        # Commandes pièces
        commandes = []
        for i in range(1, count + 1):
            commandes.append(CommandePiece(
                numero_commande=f'SEED-CMD-{i:05d}',
                fournisseur=fournisseurs[i % len(fournisseurs)],
                chef_stock=chefstocks[i % len(chefstocks)] if chefstocks else None,
                statut=random.choice(COMMANDE_STATUTS),
                montant_total=Decimal('0'),
                date_livraison_prevue=now + timedelta(days=random.randint(3, 30)),
                remarques=f'Commande seed #{i}',
                is_deleted=False,
            ))
        CommandePiece.objects.bulk_create(commandes)
        commandes = list(
            CommandePiece.objects.filter(numero_commande__startswith='SEED-CMD-').order_by('id')[:count]
        )
        stats['CommandePiece'] = len(commandes)

        # Lignes commande
        lignes = []
        for i in range(1, count + 1):
            piece = pieces[i % len(pieces)]
            qty = random.randint(1, 20)
            prix = piece.prix_unitaire
            lignes.append(LigneCommandePiece(
                commande=commandes[i % len(commandes)],
                piece=piece,
                quantite=qty,
                prix_unitaire=prix,
                sous_total=qty * prix,
            ))
        LigneCommandePiece.objects.bulk_create(lignes)
        stats['LigneCommandePiece'] = count

        for cmd in commandes:
            cmd.calculer_montant_total()

        # Prix fournisseurs
        prix_rows = []
        for i in range(1, count + 1):
            prix_rows.append(PrixFournisseur(
                piece=pieces[i - 1],
                fournisseur=fournisseurs[i - 1],
                prix=Decimal(str(random.randint(10, 500))),
                delai_livraison_jours=random.randint(1, 14),
                quantite_minimum=random.randint(1, 5),
                est_actif=True,
            ))
        PrixFournisseur.objects.bulk_create(prix_rows, ignore_conflicts=True)
        stats['PrixFournisseur'] = count

        # Factures fournisseur
        ff_rows = []
        for i, commande in enumerate(commandes):
            ff_rows.append(FactureFournisseur(
                numero_facture=f'SEED-FF-{i + 1:05d}',
                commande=commande,
                fournisseur=commande.fournisseur,
                montant_total=commande.montant_total or Decimal('100'),
                statut=random.choice(FACTURE_FOURNISSEUR_STATUTS),
                notes=f'Facture fournisseur seed #{i + 1}',
            ))
        FactureFournisseur.objects.bulk_create(ff_rows, ignore_conflicts=True)
        stats['FactureFournisseur'] = count

        # Messages
        messages = []
        for i in range(1, count + 1):
            sender = users[i % len(users)]
            receiver = users[(i + 7) % len(users)]
            if sender.id == receiver.id:
                receiver = users[(i + 1) % len(users)]
            messages.append(Message(
                expediteur=sender,
                destinataire=receiver,
                objet=f'Seed message #{i}',
                contenu=f'Contenu du message de démonstration numéro {i}.',
            ))
        Message.objects.bulk_create(messages)
        stats['Message'] = count

        # OTP codes
        otps = []
        for i in range(1, count + 1):
            user = users[i % len(users)]
            otps.append(OTPCode(
                user=user,
                code=f'{random.randint(100000, 999999)}',
                purpose=random.choice(['password_reset', 'two_factor']),
                expires_at=now + timedelta(minutes=10),
                is_used=random.choice([True, False]),
            ))
        OTPCode.objects.bulk_create(otps)
        stats['OTPCode'] = count

        return stats
