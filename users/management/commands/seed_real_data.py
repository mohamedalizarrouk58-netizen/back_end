"""
Insert realistic GMAO sample data (French industrial maintenance context).

Usage:
  python manage.py seed_real_data
  python manage.py seed_real_data --clear   # remove only GMAO-marked sample rows
"""
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.department_policy import seed_default_departments
from users.models import (
    User,
    Department,
    Client,
    CategorieMateriel,
    Materiel,
    DemandeMaintenance,
    Intervention,
    FicheReparation,
    Piece,
    DemandePiece,
    Facture,
    Paiement,
    Message,
    Fournisseur,
    CommandePiece,
    LigneCommandePiece,
    PrixFournisseur,
    FactureFournisseur,
)

MARKER_DOMAIN = 'entreprise-gmao.fr'
MARKER_SERIAL_PREFIX = 'GMAO-SN-'
MARKER_PIECE_PREFIX = 'GMAO-REF-'
MARKER_CMD_PREFIX = 'CMD-GMAO-'
MARKER_FF_PREFIX = 'FF-GMAO-'
DEFAULT_PASSWORD = 'Gmao2024!'


class Command(BaseCommand):
    help = 'Insert realistic sample data for demos and development.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove GMAO sample data (keeps manually created records).',
        )

    def handle(self, *args, **options):
        if options['clear']:
            with transaction.atomic():
                removed = self._clear()
            self.stdout.write(self.style.SUCCESS('GMAO sample data removed.'))
            for label, count in removed.items():
                if count:
                    self.stdout.write(f'  {label}: {count}')
            return

        with transaction.atomic():
            stats = self._seed()
        self.stdout.write(self.style.SUCCESS('Realistic GMAO data created:'))
        for label, count in stats.items():
            self.stdout.write(f'  {label}: {count}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            f'Staff password (sample users): {DEFAULT_PASSWORD}'
        ))

    def _clear(self):
        removed = {}

        def _del(label, qs):
            count, _ = qs.delete()
            removed[label] = count

        _del('FactureFournisseur', FactureFournisseur.objects.filter(numero_facture__startswith=MARKER_FF_PREFIX))
        _del('LigneCommandePiece', LigneCommandePiece.objects.filter(commande__numero_commande__startswith=MARKER_CMD_PREFIX))
        _del('CommandePiece', CommandePiece.objects.filter(numero_commande__startswith=MARKER_CMD_PREFIX))
        _del('PrixFournisseur', PrixFournisseur.objects.filter(piece__reference__startswith=MARKER_PIECE_PREFIX))
        _del('Message', Message.objects.filter(expediteur__email__endswith=f'@{MARKER_DOMAIN}'))
        _del('Paiement', Paiement.objects.filter(facture__client__email__endswith=f'@{MARKER_DOMAIN}'))
        _del('Facture', Facture.objects.filter(client__email__endswith=f'@{MARKER_DOMAIN}'))
        _del('DemandePiece', DemandePiece.objects.filter(piece__reference__startswith=MARKER_PIECE_PREFIX))
        _del('FicheReparation', FicheReparation.objects.filter(
            intervention__demande__materiel__numero_serie__startswith=MARKER_SERIAL_PREFIX,
        ))
        _del('Intervention', Intervention.objects.filter(
            demande__materiel__numero_serie__startswith=MARKER_SERIAL_PREFIX,
        ))
        _del('DemandeMaintenance', DemandeMaintenance.objects.filter(
            materiel__numero_serie__startswith=MARKER_SERIAL_PREFIX,
        ))
        _del('Materiel', Materiel.objects.filter(numero_serie__startswith=MARKER_SERIAL_PREFIX))
        _del('Piece', Piece.objects.filter(reference__startswith=MARKER_PIECE_PREFIX))
        _del('Client', Client.objects.filter(email__endswith=f'@{MARKER_DOMAIN}'))
        _del('CategorieMateriel', CategorieMateriel.objects.filter(nom__startswith='GMAO '))
        _del('Fournisseur', Fournisseur.objects.filter(email__endswith=f'@{MARKER_DOMAIN}'))
        _del('User', User.objects.filter(email__endswith=f'@{MARKER_DOMAIN}'))
        return removed

    def _seed(self):
        stats = {}
        now = timezone.now()
        dept_stats = seed_default_departments()
        stats['Department (defaults)'] = dept_stats.get('created', 0)

        departments = {
            d.nom_dept: d
            for d in Department.objects.filter(
                nom_dept__in=[
                    'Maintenance Industrielle',
                    'Atelier Mécanique',
                    'Électricité & Automatisme',
                    'Logistique & Stock',
                ],
            )
        }
        dept_maint = departments.get('Maintenance Industrielle')
        dept_meca = departments.get('Atelier Mécanique')
        dept_elec = departments.get('Électricité & Automatisme')
        dept_stock = departments.get('Logistique & Stock')

        staff_specs = [
            ('gmao.admin', 'Mohamed', 'Alizarrouk', 'admin', dept_maint, '+216 71 200 101'),
            ('gmao.manager', 'Fatima', 'Ben Salah', 'manager', dept_maint, '+216 71 200 102'),
            ('gmao.reception', 'Yasmine', 'Trabelsi', 'receptioniste', dept_maint, '+216 71 200 103'),
            ('gmao.tech.karim', 'Karim', 'Mansouri', 'technicien', dept_meca, '+216 71 200 104'),
            ('gmao.tech.omar', 'Omar', 'Gharbi', 'technicien', dept_elec, '+216 71 200 105'),
            ('gmao.stock', 'Salim', 'Jebali', 'chefstock', dept_stock, '+216 71 200 106'),
            ('gmao.fournisseur', 'Ridha', 'Mejri', 'fournisseur', dept_stock, '+216 71 200 107'),
        ]

        users = {}
        for username, first, last, role, dept, phone in staff_specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@{MARKER_DOMAIN}',
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'department': dept,
                    'telephone': phone,
                    'is_deleted': False,
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
            users[role] = users.get(role, user)
            if role == 'technicien':
                users.setdefault('techniciens', []).append(user)
            users[username] = user

        stats['User'] = len(staff_specs)

        client_specs = [
            ('Société Métal Tunis SA', 'contact@metal-tunis.tn', '+216 71 300 201', 'Zone industrielle Ben Arous, Tunis'),
            ('Agro Indus Nord', 'achats@agroindus-nord.tn', '+216 72 400 302', 'Route de Bizerte, Mateur'),
            ('Pharma Lab Sfax', 'maintenance@pharmalab-sfax.tn', '+216 74 500 403', 'Pôle technologique, Sfax'),
            ('Textile Atlas', 'atelier@textile-atlas.tn', '+216 73 600 504', 'Ksar Hellal, Monastir'),
            ('Logistique Cap Bon', 'depot@capbon-log.tn', '+216 72 700 605', 'Nabeul'),
            ('Cimenterie Sud', 'usine@cimenterie-sud.tn', '+216 75 800 706', 'Gabès'),
            ('Emballages Méditerranée', 'prod@emb-med.tn', '+216 71 900 807', 'Megrine, Tunis'),
            ('Hydraulique Pro Services', 'service@hydpro.tn', '+216 70 100 908', 'Ariana'),
        ]

        clients = []
        for i, (name, email, phone, addr) in enumerate(client_specs, start=1):
            sample_email = f'client{i:02d}@{MARKER_DOMAIN}'
            client, _ = Client.objects.get_or_create(
                email=sample_email,
                defaults={
                    'nom_complet': name,
                    'telephone': phone,
                    'adresse': addr,
                    'is_deleted': False,
                },
            )
            clients.append(client)
        stats['Client'] = len(clients)

        category_specs = [
            ('GMAO Mécanique', 'Courroies, roulements, transmissions et organes mécaniques.'),
            ('GMAO Électrique', 'Contacteurs, variateurs, câblage et composants électriques.'),
            ('GMAO Hydraulique', 'Pompes, joints, flexibles et distributeurs hydrauliques.'),
            ('GMAO Pneumatique', 'Vérins, régulateurs et raccords pneumatiques.'),
            ('GMAO Automatisme', 'Capteurs, automates et modules I/O.'),
        ]
        categories = {}
        for nom, desc in category_specs:
            cat, _ = CategorieMateriel.objects.get_or_create(
                nom=nom,
                defaults={'description': desc, 'is_active': True},
            )
            categories[nom] = cat
        stats['CategorieMateriel'] = len(category_specs)

        piece_specs = [
            ('Courroie trapézoïdale SPB 2000', 'GMAO Mécanique', 'SPB-2000', 24, 5, '85.00'),
            ('Roulement SKF 6205-2RS', 'GMAO Mécanique', 'SKF-6205', 18, 4, '42.50'),
            ('Joint torique NBR 50x3', 'GMAO Hydraulique', 'JT-50-3', 45, 10, '3.20'),
            ('Filtre hydraulique HF6555', 'GMAO Hydraulique', 'HF-6555', 8, 3, '128.00'),
            ('Contacteur Schneider LC1D25', 'GMAO Électrique', 'LC1D25', 12, 4, '156.00'),
            ('Variateur Altivar 312 4kW', 'GMAO Électrique', 'ATV312-4KW', 3, 2, '890.00'),
            ('Vérin pneumatique ISO 6432', 'GMAO Pneumatique', 'CY-6432-100', 6, 2, '210.00'),
            ('Capteur inductif PNP M12', 'GMAO Automatisme', 'SN-M12-PNP', 15, 5, '38.00'),
            ('Flexible hydraulique 3/8 2m', 'GMAO Hydraulique', 'FH-38-200', 10, 3, '95.00'),
            ('Graisse haute température 400g', 'GMAO Mécanique', 'GR-HT-400', 30, 8, '18.50'),
            ('Fusible NH00 160A', 'GMAO Électrique', 'NH00-160', 20, 6, '12.00'),
            ('Courroie crantée HTD 8M-1120', 'GMAO Mécanique', 'HTD-8M-1120', 2, 2, '72.00'),
        ]

        pieces = []
        for nom, cat_key, ref_suffix, qty, seuil, prix in piece_specs:
            ref = f'{MARKER_PIECE_PREFIX}{ref_suffix}'
            piece, _ = Piece.objects.get_or_create(
                reference=ref,
                defaults={
                    'nom': nom,
                    'categorie': categories[cat_key],
                    'modele': ref_suffix,
                    'quantite_stock': qty,
                    'seuil_alerte': seuil,
                    'prix_unitaire': Decimal(prix),
                },
            )
            pieces.append(piece)
        stats['Piece'] = len(pieces)

        fournisseur_specs = [
            ('HydraTech Fournitures', 'gmao.fournisseur', 'Ridha Mejri'),
            ('Electro Industrie Maghreb', None, 'Nadia Khelifi'),
            ('Meca Parts Distribution', None, 'Hichem Bouazizi'),
        ]
        fournisseurs = []
        for i, (nom, user_key, contact) in enumerate(fournisseur_specs, start=1):
            fu = users.get(user_key) if user_key else None
            four, _ = Fournisseur.objects.get_or_create(
                nom=nom,
                defaults={
                    'utilisateur': fu,
                    'email': f'fournisseur{i:02d}@{MARKER_DOMAIN}',
                    'telephone': f'+216 71 2{i:02d} 000',
                    'adresse': f'Zone industrielle {i}, Tunis',
                    'ville': 'Tunis',
                    'code_postal': '2035',
                    'pays': 'Tunisie',
                    'contact_principal': contact,
                    'est_actif': True,
                },
            )
            fournisseurs.append(four)
        stats['Fournisseur'] = len(fournisseurs)

        materiel_specs = [
            (0, 'Compresseur', 'Atlas Copco', 'GA 37 VSD', 'Reçu'),
            (0, 'Pompe centrifuge', 'KSB', 'Etaline G 32-160', 'En réparation'),
            (1, 'Convoyeur bande', 'Siemens', 'CB-1200', 'En réparation'),
            (1, 'Armoire électrique', 'Schneider', 'Prisma Plus P', 'Réparé'),
            (2, 'Pont roulant', 'Demag', 'DC-Pro 5t', 'En réparation'),
            (2, 'Centrale CVC', 'Daikin', 'EWAD-T', 'Reçu'),
            (3, 'Presse hydraulique', 'Schuler', 'PH-250', 'Livré'),
            (3, 'Groupe motopompe', 'Grundfos', 'CR 32-4', 'En réparation'),
            (4, 'Chariot élévateur', 'Toyota', '8FG25', 'Réparé'),
            (5, 'Four industriel', 'Nabertherm', 'N 300', 'En réparation'),
            (6, 'Ensacheuse flowpack', 'Bosch', 'Pack 201', 'Reçu'),
            (7, 'Unité hydraulique', 'Bosch Rexroth', 'A10VSO 45', 'En réparation'),
        ]

        materiels = []
        for i, (client_idx, typ, marque, modele, etat) in enumerate(materiel_specs, start=1):
            serial = f'{MARKER_SERIAL_PREFIX}{i:04d}'
            mat, _ = Materiel.objects.get_or_create(
                numero_serie=serial,
                defaults={
                    'client': clients[client_idx],
                    'type': typ,
                    'marque': marque,
                    'modele': modele,
                    'etat': etat,
                    'is_deleted': False,
                },
            )
            materiels.append(mat)
        stats['Materiel'] = len(materiels)

        panne_samples = [
            'Surchauffe moteur compresseur, alarme température.',
            'Fuite joint pompe, perte de pression ligne 2.',
            'Courroie convoyeur usée, glissement et bruit.',
            'Disjoncteur armoire qui saute en charge.',
            'Moteur pont roulant ne répond plus aux commandes.',
            'Échangeur CVC encrassé, faible rendement.',
            'Fuite huile presse, cylindre principal.',
            'Roulement pompe grippé, vibration élevée.',
            'Hydraulique chariot : pression insuffisante.',
            'Résistance four coupée, température instable.',
            'Capteur ensacheuse défaillant, arrêts intempestifs.',
            'Pompe hydraulique bruyante, niveau huile bas.',
        ]

        demande_configs = [
            (0, 'haute', 'en_cours', 5),
            (1, 'moyenne', 'en_cours', 8),
            (2, 'haute', 'en_attente', 2),
            (3, 'faible', 'termine', 25),
            (4, 'haute', 'en_cours', 12),
            (5, 'moyenne', 'en_attente', 1),
            (6, 'moyenne', 'termine', 18),
            (7, 'haute', 'en_cours', 6),
            (8, 'faible', 'termine', 30),
            (9, 'moyenne', 'refuse', 14),
        ]

        receptioniste = users['receptioniste']
        manager = users['manager']
        techniciens = users.get('techniciens', [users.get('technicien')])
        chefstock = users['chefstock']

        demandes = []
        for i, (mat_idx, priorite, statut, days_ago) in enumerate(demande_configs):
            mat = materiels[mat_idx]
            demande = DemandeMaintenance.objects.create(
                materiel=mat,
                receptioniste=receptioniste,
                manager=manager,
                priorite=priorite,
                statut=statut,
            )
            DemandeMaintenance.objects.filter(pk=demande.pk).update(
                date_creation=now - timedelta(days=days_ago),
            )
            demande.refresh_from_db()
            demandes.append(demande)
        stats['DemandeMaintenance'] = len(demandes)

        intervention_configs = [
            ('en_cours', 5, None, 0),
            ('en_cours', 8, None, 1),
            ('termine', 25, 22, 3),
            ('en_cours', 12, None, 4),
            ('termine', 18, 15, 6),
            ('en_cours', 6, None, 7),
            ('termine', 30, 27, 8),
            ('refuse', 14, 13, 9),
        ]

        interventions = []
        for i, (statut, start_days, end_days, demande_idx) in enumerate(intervention_configs):
            demande = demandes[demande_idx]
            if Intervention.objects.filter(demande=demande).exists():
                continue
            tech = techniciens[i % len(techniciens)]
            inter = Intervention.objects.create(
                demande=demande,
                technicien=tech,
                diagnostic=panne_samples[demande_idx],
                solution_proposee='Intervention planifiée selon diagnostic atelier.',
                date_debut=now - timedelta(days=start_days),
                date_fin=now - timedelta(days=end_days) if end_days else None,
                statut=statut,
            )
            interventions.append(inter)
        stats['Intervention'] = len(interventions)

        fiches = []
        for i, inter in enumerate(interventions):
            if FicheReparation.objects.filter(intervention=inter).exists():
                continue
            labor = Decimal('120') + Decimal(i * 15)
            fiche = FicheReparation.objects.create(
                intervention=inter,
                description_panne=inter.diagnostic or panne_samples[i % len(panne_samples)],
                solution='Réparation effectuée conformément au protocole maintenance.',
                cout_main_oeuvre=labor,
                frais_societe=Decimal('45.00'),
                prix_supplementaire=Decimal('25.00') if i % 2 == 0 else Decimal('0'),
                confirmation=inter.statut == 'termine',
                valide_manager=inter.statut in ('termine', 'en_cours'),
            )
            fiches.append(fiche)
        stats['FicheReparation'] = len(fiches)

        dp_statuts = ['livree', 'demandee', 'hors_stock', 'commandee', 'livree', 'demandee']
        for i, fiche in enumerate(fiches[:6]):
            piece = pieces[i % len(pieces)]
            qty = 1 + (i % 3)
            DemandePiece.objects.create(
                fiche=fiche,
                piece=piece,
                quantite=qty,
                quantite_manquante=max(0, qty - piece.quantite_stock),
                demandeur_stock=chefstock,
                fournisseur=fournisseurs[i % len(fournisseurs)],
                statut=dp_statuts[i % len(dp_statuts)],
            )
        stats['DemandePiece'] = min(6, len(fiches))

        factures = []
        for i, inter in enumerate([x for x in interventions if x.statut == 'termine'][:5]):
            if Facture.objects.filter(intervention=inter).exists():
                continue
            fiche = inter.fiche_reparation
            client = inter.demande.materiel.client
            parts = Decimal(str(fiche.cout_pieces() or 0))
            labor = Decimal(str(fiche.cout_main_oeuvre or 0))
            society = Decimal(str(fiche.frais_societe or 0))
            extra = Decimal(str(fiche.prix_supplementaire or 0))
            total = parts + labor + society + extra
            facture = Facture.objects.create(
                intervention=inter,
                client=client,
                montant_pieces=parts,
                montant_main_oeuvre=labor,
                montant_frais_societe=society,
                montant_supplementaire=extra,
                montant_total=total,
                est_payee=i % 2 == 0,
                email_client_envoye=i % 2 == 0,
                is_deleted=False,
            )
            factures.append(facture)
            if facture.est_payee:
                Paiement.objects.create(
                    facture=facture,
                    montant=total,
                    mode_paiement='virement' if i % 2 else 'cheque',
                )
        stats['Facture'] = len(factures)
        stats['Paiement'] = Paiement.objects.filter(facture__in=factures).count()

        commandes = []
        for i in range(1, 3):
            cmd_num = f'{MARKER_CMD_PREFIX}{i:04d}'
            cmd, created = CommandePiece.objects.get_or_create(
                numero_commande=cmd_num,
                defaults={
                    'fournisseur': fournisseurs[i - 1],
                    'chef_stock': chefstock,
                    'statut': 'livree' if i == 1 else 'en_attente_fournisseur',
                    'date_livraison_prevue': now + timedelta(days=7 + i),
                    'remarques': 'Commande urgente ligne production 2.',
                    'is_deleted': False,
                },
            )
            if created:
                for j in range(2):
                    piece = pieces[(i + j) % len(pieces)]
                    qty = 5 + j * 3
                    LigneCommandePiece.objects.create(
                        commande=cmd,
                        piece=piece,
                        quantite=qty,
                        prix_unitaire=piece.prix_unitaire,
                    )
                cmd.calculer_montant_total()
            commandes.append(cmd)
        stats['CommandePiece'] = len(commandes)

        for piece in pieces[:8]:
            for four in fournisseurs:
                PrixFournisseur.objects.get_or_create(
                    piece=piece,
                    fournisseur=four,
                    defaults={
                        'prix': piece.prix_unitaire * Decimal('0.92'),
                        'delai_livraison_jours': 3 + (piece.id % 5),
                        'quantite_minimum': 1,
                        'est_actif': True,
                    },
                )
        stats['PrixFournisseur'] = PrixFournisseur.objects.filter(
            piece__reference__startswith=MARKER_PIECE_PREFIX,
        ).count()

        for i, cmd in enumerate(commandes):
            FactureFournisseur.objects.get_or_create(
                numero_facture=f'{MARKER_FF_PREFIX}{i + 1:04d}',
                defaults={
                    'commande': cmd,
                    'fournisseur': cmd.fournisseur,
                    'montant_total': cmd.montant_total or Decimal('500'),
                    'statut': 'payee' if i == 0 else 'validee',
                    'notes': 'Facture fournisseur pièces détachées.',
                },
            )
        stats['FactureFournisseur'] = FactureFournisseur.objects.filter(
            numero_facture__startswith=MARKER_FF_PREFIX,
        ).count()

        message_pairs = [
            (users['gmao.manager'], users['gmao.tech.karim'], 'Priorité pompe KSB', 'Karim, la pompe Etaline ligne 2 est prioritaire pour demain matin.'),
            (users['gmao.stock'], users['gmao.manager'], 'Stock filtres hydrauliques', 'Il reste 8 filtres HF6555 — seuil d\'alerte atteint.'),
            (users['gmao.reception'], users['gmao.manager'], 'Client Pharma Lab', 'Pharma Lab Sfax demande un devis pour le pont roulant.'),
            (users['gmao.tech.omar'], users['gmao.tech.karim'], 'Armoire Schneider', 'J\'ai besoin du variateur ATV312 pour finaliser l\'armoire.'),
        ]
        for sender, receiver, objet, contenu in message_pairs:
            Message.objects.get_or_create(
                expediteur=sender,
                destinataire=receiver,
                objet=objet,
                defaults={'contenu': contenu, 'type_message': 'text'},
            )
        stats['Message'] = len(message_pairs)

        return stats
