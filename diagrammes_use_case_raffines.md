# Diagrammes de cas d'utilisation raffinés par acteur

Les diagrammes ci-dessous reprennent le diagramme global sous une forme raffinée par acteur, dans l'esprit de l'exemple fourni.

## 1) Réceptionniste

```plantuml
@startuml
left to right direction

actor "Réceptionniste" as Receptionniste

usecase "S'authentifier" as UC_AUTH
usecase "Gérer clients" as UC_CLIENTS
usecase "Ajouter client" as UC_AJOUTER_CLIENT
usecase "Modifier client" as UC_MODIFIER_CLIENT
usecase "Supprimer client" as UC_SUPPRIMER_CLIENT
usecase "Consulter client" as UC_CONSULTER_CLIENT

usecase "Gérer matériels" as UC_MATERIELS
usecase "Ajouter matériel" as UC_AJOUTER_MATERIEL
usecase "Modifier matériel" as UC_MODIFIER_MATERIEL
usecase "Supprimer matériel" as UC_SUPPRIMER_MATERIEL
usecase "Consulter matériel" as UC_CONSULTER_MATERIEL

usecase "Gérer demandes de maintenance" as UC_DEMANDES_MAINT
usecase "Enregistrer demande" as UC_ENREGISTRER_DEMANDE
usecase "Modifier demande" as UC_MODIFIER_DEMANDE
usecase "Suivre état demande" as UC_SUIVRE_DEMANDE

usecase "Gérer paiements" as UC_PAIEMENTS
usecase "Enregistrer paiement" as UC_ENREGISTRER_PAIEMENT
usecase "Consulter état paiement" as UC_CONSULTER_PAIEMENT

usecase "Consulter tableau de bord" as UC_DASHBOARD

Receptionniste --> UC_CLIENTS
Receptionniste --> UC_MATERIELS
Receptionniste --> UC_DEMANDES_MAINT
Receptionniste --> UC_PAIEMENTS
Receptionniste --> UC_DASHBOARD

UC_CLIENTS ..> UC_AUTH : <<include>>
UC_MATERIELS ..> UC_AUTH : <<include>>
UC_DEMANDES_MAINT ..> UC_AUTH : <<include>>
UC_PAIEMENTS ..> UC_AUTH : <<include>>
UC_DASHBOARD ..> UC_AUTH : <<include>>

UC_CLIENTS ..> UC_AJOUTER_CLIENT : <<extends>>
UC_CLIENTS ..> UC_MODIFIER_CLIENT : <<extends>>
UC_CLIENTS ..> UC_SUPPRIMER_CLIENT : <<extends>>
UC_CLIENTS ..> UC_CONSULTER_CLIENT : <<extends>>

UC_MATERIELS ..> UC_AJOUTER_MATERIEL : <<extends>>
UC_MATERIELS ..> UC_MODIFIER_MATERIEL : <<extends>>
UC_MATERIELS ..> UC_SUPPRIMER_MATERIEL : <<extends>>
UC_MATERIELS ..> UC_CONSULTER_MATERIEL : <<extends>>

UC_DEMANDES_MAINT ..> UC_ENREGISTRER_DEMANDE : <<extends>>
UC_DEMANDES_MAINT ..> UC_MODIFIER_DEMANDE : <<extends>>>
UC_DEMANDES_MAINT ..> UC_SUIVRE_DEMANDE : <<extends>>

UC_PAIEMENTS ..> UC_ENREGISTRER_PAIEMENT : <<extends>>
UC_PAIEMENTS ..> UC_CONSULTER_PAIEMENT : <<extends>>>

@enduml
```

## 2) Manager

```plantuml
@startuml
left to right direction

actor "Manager" as Manager

usecase "S'authentifier" as UC_AUTH
usecase "Gérer demandes de maintenance" as UC_GERER_DEMANDES_MAINT
usecase "Établir fiche de réparation" as UC_FICHE_REPARATION
usecase "Planifier intervention" as UC_PLANIFIER_INTERVENTION
usecase "Gérer facture" as UC_GERER_FACTURE
usecase "Consulter tableau de bord" as UC_DASHBOARD

Manager --> UC_GERER_DEMANDES_MAINT
Manager --> UC_DASHBOARD

UC_GERER_DEMANDES_MAINT ..> UC_AUTH : <<include>>
UC_FICHE_REPARATION ..> UC_AUTH : <<include>>
UC_PLANIFIER_INTERVENTION ..> UC_AUTH : <<include>>
UC_GERER_FACTURE ..> UC_AUTH : <<include>>
UC_DASHBOARD ..> UC_AUTH : <<include>>

UC_GERER_DEMANDES_MAINT ..> UC_CONSULTER_DEMANDE : <<extends>>
UC_GERER_DEMANDES_MAINT ..> UC_MODIFIER_DEMANDE : <<extends>>
UC_GERER_DEMANDES_MAINT ..> UC_DECIDER_DEMANDE : <<extends>>
UC_GERER_DEMANDES_MAINT ..> UC_FICHE_REPARATION : <<extends>>
UC_GERER_DEMANDES_MAINT ..> UC_PLANIFIER_INTERVENTION : <<extends>>
UC_GERER_DEMANDES_MAINT ..> UC_GERER_FACTURE : <<extends>>

@enduml
```

## 3) Technicien

```plantuml
@startuml
left to right direction

actor "Technicien" as Technicien

usecase "S'authentifier" as UC_AUTH
usecase "Gérer intervention" as UC_GERER_INTERVENTION
usecase "Traiter intervention" as UC_TRAITER_INTERVENTION
usecase "Consulter message diagnostic" as UC_MESSAGE_DIAGNOSTIC
usecase "Proposer solution" as UC_PROPOSER_SOLUTION
usecase "Mettre à jour statut intervention" as UC_MAJ_STATUT
usecase "Terminer intervention" as UC_TERMINER_INTERVENTION
usecase "Consulter tableau de bord" as UC_DASHBOARD

Technicien --> UC_GERER_INTERVENTION
Technicien --> UC_DASHBOARD

UC_GERER_INTERVENTION ..> UC_AUTH : <<include>>
UC_DASHBOARD ..> UC_AUTH : <<include>>

UC_GERER_INTERVENTION ..> UC_TRAITER_INTERVENTION : <<include>>
UC_GERER_INTERVENTION ..> UC_TERMINER_INTERVENTION : <<include>>

UC_TRAITER_INTERVENTION ..> UC_MESSAGE_DIAGNOSTIC : <<include>>
UC_TRAITER_INTERVENTION ..> UC_PROPOSER_SOLUTION : <<include>>
UC_TRAITER_INTERVENTION ..> UC_MAJ_STATUT : <<include>>

@enduml
```

## 4) Chef de stock

```plantuml
@startuml
left to right direction

actor "Chef de stock" as ChefStock

usecase "S'authentifier" as UC_AUTH
usecase "Consulter stock" as UC_CONSULTER_STOCK
usecase "Gérer demandes de pièces" as UC_GERER_DEMANDES_PIECES
usecase "Consulter demande de pièce" as UC_CONSULTER_DEMANDE_PIECE
usecase "Modifier état demande de pièce" as UC_MODIFIER_ETAT_DEMANDE
usecase "Préparer pièces" as UC_PREPARER_PIECES
usecase "Consulter tableau de bord" as UC_DASHBOARD

ChefStock --> UC_CONSULTER_STOCK
ChefStock --> UC_GERER_DEMANDES_PIECES
ChefStock --> UC_DASHBOARD

UC_CONSULTER_STOCK ..> UC_AUTH : <<include>>
UC_GERER_DEMANDES_PIECES ..> UC_AUTH : <<include>>
UC_DASHBOARD ..> UC_AUTH : <<include>>

UC_GERER_DEMANDES_PIECES ..> UC_CONSULTER_DEMANDE_PIECE : <<include>>
UC_GERER_DEMANDES_PIECES ..> UC_MODIFIER_ETAT_DEMANDE : <<include>>
UC_GERER_DEMANDES_PIECES ..> UC_PREPARER_PIECES : <<include>>

@enduml
```

## 5) Administrateur

```plantuml
@startuml
left to right direction

actor "Administrateur" as Admin

usecase "S'authentifier" as UC_AUTH
usecase "Gérer utilisateurs" as UC_GERER_USERS
usecase "Ajouter utilisateur" as UC_AJOUTER_USER
usecase "Modifier utilisateur" as UC_MODIFIER_USER
usecase "Supprimer utilisateur" as UC_SUPPRIMER_USER
usecase "Visualiser profil" as UC_VISUALISER_PROFIL

usecase "Gérer départements" as UC_GERER_DEPARTEMENTS
usecase "Ajouter département" as UC_AJOUTER_DEPT
usecase "Modifier département" as UC_MODIFIER_DEPT
usecase "Supprimer département" as UC_SUPPRIMER_DEPT

usecase "Consulter tableau de bord" as UC_DASHBOARD

Admin --> UC_GERER_USERS
Admin --> UC_GERER_DEPARTEMENTS
Admin --> UC_DASHBOARD

UC_GERER_USERS ..> UC_AUTH : <<include>>
UC_GERER_DEPARTEMENTS ..> UC_AUTH : <<include>>
UC_DASHBOARD ..> UC_AUTH : <<include>>

UC_GERER_USERS ..> UC_AJOUTER_USER : <<include>>
UC_GERER_USERS ..> UC_MODIFIER_USER : <<include>>
UC_GERER_USERS ..> UC_SUPPRIMER_USER : <<include>>
UC_GERER_USERS ..> UC_VISUALISER_PROFIL : <<include>>

UC_GERER_DEPARTEMENTS ..> UC_AJOUTER_DEPT : <<include>>
UC_GERER_DEPARTEMENTS ..> UC_MODIFIER_DEPT : <<include>>
UC_GERER_DEPARTEMENTS ..> UC_SUPPRIMER_DEPT : <<include>>

@enduml
```

## 6) Fournisseur

```plantuml
@startuml
left to right direction

actor "Fournisseur" as Fournisseur

usecase "S'authentifier" as UC_AUTH
usecase "Consulter demandes de pièces" as UC_CONSULTER_DEMANDES
usecase "Consulter commandes" as UC_CONSULTER_COMMANDES
usecase "Confirmer commande" as UC_CONFIRMER_COMMANDE
usecase "Mettre à jour statut de livraison" as UC_MAJ_LIVRAISON
usecase "Consulter pièces fournies" as UC_CONSULTER_PIECES

Fournisseur --> UC_CONSULTER_DEMANDES
Fournisseur --> UC_CONSULTER_COMMANDES
Fournisseur --> UC_CONFIRMER_COMMANDE
Fournisseur --> UC_MAJ_LIVRAISON
Fournisseur --> UC_CONSULTER_PIECES

UC_CONSULTER_DEMANDES ..> UC_AUTH : <<include>>
UC_CONSULTER_COMMANDES ..> UC_AUTH : <<include>>
UC_CONFIRMER_COMMANDE ..> UC_AUTH : <<include>>
UC_MAJ_LIVRAISON ..> UC_AUTH : <<include>>
UC_CONSULTER_PIECES ..> UC_AUTH : <<include>>

UC_CONSULTER_COMMANDES ..> UC_CONFIRMER_COMMANDE : <<include>>
UC_CONSULTER_COMMANDES ..> UC_MAJ_LIVRAISON : <<include>>

@enduml
```

## 7) Client

```plantuml
@startuml
left to right direction

actor "Client" as Client

usecase "S'authentifier" as UC_AUTH
usecase "Consulter état de matériel" as UC_ETAT_MATERIEL
usecase "Voir facture ou paiement" as UC_VOIR_FACTURE
usecase "Gérer commentaires" as UC_GERER_COMMENTAIRES
usecase "Ajouter commentaire" as UC_AJOUTER_COMMENTAIRE
usecase "Modifier commentaire" as UC_MODIFIER_COMMENTAIRE
usecase "Supprimer commentaire" as UC_SUPPRIMER_COMMENTAIRE

Client --> UC_ETAT_MATERIEL
Client --> UC_VOIR_FACTURE
Client --> UC_GERER_COMMENTAIRES

UC_ETAT_MATERIEL ..> UC_AUTH : <<include>>
UC_VOIR_FACTURE ..> UC_AUTH : <<include>>
UC_GERER_COMMENTAIRES ..> UC_AUTH : <<include>>

UC_GERER_COMMENTAIRES ..> UC_AJOUTER_COMMENTAIRE : <<include>>
UC_GERER_COMMENTAIRES ..> UC_MODIFIER_COMMENTAIRE : <<include>>
UC_GERER_COMMENTAIRES ..> UC_SUPPRIMER_COMMENTAIRE : <<include>>

@enduml
```

Si tu veux, je peux aussi te les transformer en version image ou en version Mermaid/Word plus propre pour un mémoire ou un rapport.

## 8) Sequence - Assignation fournisseur

```plantuml
@startuml
autonumber
actor "Chef de stock" as C
participant "Systeme" as S

C -> S: selectionner une demande de piece
C -> S: choisir un fournisseur
S -> S: verifier fournisseur actif
S -> S: calculer quantite manquante
S -> S: creer une commande
S -> S: ajouter une ligne de commande
S -> S: lier la demande a la commande
S --> C: confirmer l'assignation
@enduml
```

## 9) Sequence - Reception livraison

```plantuml
@startuml
autonumber
actor "Chef de stock" as C
participant "Systeme" as S

C -> S: declarer une livraison
S -> S: verifier statut de la demande
S -> S: verifier quantite livree
S -> S: mettre a jour le stock
S -> S: mettre a jour la demande
S -> S: mettre a jour la commande
S -> S: creer ou mettre a jour la facture fournisseur
S --> C: confirmer la reception
@enduml
```

## 10) Diagramme annoté - Endpoints par rôle

```plantuml
@startuml
left to right direction

actor "Réceptionniste" as Receptionniste
actor "Manager" as Manager
actor "Technicien" as Technicien
actor "Chef de stock" as ChefStock
actor "Fournisseur" as Fournisseur
actor "Administrateur" as Admin
actor "Client" as Client

usecase "Créer demande maintenance\nPOST /api/demande-maintenances/" as UC_DM_CREATE
note right of UC_DM_CREATE: Méthode: POST\nURL: /api/demande-maintenances/\nAuth: JWT (receptioniste)

usecase "Mes demandes (réceptionniste)\nGET /api/demande-maintenances/me/" as UC_DM_ME
note right of UC_DM_ME: Méthode: GET\nURL: /api/demande-maintenances/me/\nAuth: JWT

usecase "Créer demande pièce\nPOST /api/demande-pieces/" as UC_DP_CREATE
note right of UC_DP_CREATE: Méthode: POST\nURL: /api/demande-pieces/\nAuth: JWT (chefstock idéalement)

usecase "Assigner fournisseur\nPOST /api/demande-pieces/{id}/assigner-fournisseur/" as UC_DP_ASSIGN
note right of UC_DP_ASSIGN: Méthode: POST\nURL: /api/demande-pieces/{id}/assigner-fournisseur/\nAuth: JWT (chefstock)

usecase "Réponse fournisseur\nPOST /api/demande-pieces/{id}/reponse-fournisseur/" as UC_DP_RESPONSE
note right of UC_DP_RESPONSE: Méthode: POST\nURL: /api/demande-pieces/{id}/reponse-fournisseur/\nAuth: JWT (fournisseur)

usecase "Réception livraison\nPOST /api/demande-pieces/{id}/reception-livraison/" as UC_DP_RECEIVE
note right of UC_DP_RECEIVE: Méthode: POST\nURL: /api/demande-pieces/{id}/reception-livraison/\nAuth: JWT (chefstock)

usecase "CRUD Materiels\n/api/materiels/" as UC_MATERIELS
note right of UC_MATERIELS: Méthodes: GET/POST/PUT/PATCH/DELETE\nURL: /api/materiels/\nAuth: JWT

usecase "Interventions (mes interventions)\nGET /api/interventions/me/" as UC_INTERV_ME
note right of UC_INTERV_ME: Méthode: GET\nURL: /api/interventions/me/\nAuth: JWT (technicien)

usecase "Fiche réparation\n/api/fiche-reparations/" as UC_FICHE
note right of UC_FICHE: CRUD fiche liée à une intervention\nAuth: JWT

usecase "Commandes fournisseurs\n/api/commandes-pieces/" as UC_COMMANDES
note right of UC_COMMANDES: CRUD + action calculer_montant\nAuth: JWT (chefstock/admin)

usecase "Factures & Paiements\n/api/factures/ , /api/paiements/" as UC_FACTURES
note right of UC_FACTURES: CRUD factures et paiements\nAuth: JWT

usecase "Users admin CRUD\n/api/users/" as UC_USERS
note right of UC_USERS: CRUD utilisateurs, actions: register, register-fournisseur, me\nAuth: JWT (admin pour CRUD)

usecase "Auth JWT & OTP\n/api/token/ , /api/auth/*" as UC_AUTH
note right of UC_AUTH: Endpoints: /api/token/, /api/token/refresh/, /api/auth/send-otp/, /api/auth/send-2fa-otp/, /api/auth/login-2fa/, /api/auth/reset-password/, /api/auth/toggle-2fa/

Receptionniste --> UC_DM_CREATE
Receptionniste --> UC_DM_ME
Receptionniste --> UC_MATERIELS

ChefStock --> UC_DP_CREATE
ChefStock --> UC_DP_ASSIGN
ChefStock --> UC_DP_RECEIVE
ChefStock --> UC_COMMANDES

Fournisseur --> UC_DP_RESPONSE
Fournisseur --> UC_COMMANDES

Technicien --> UC_INTERV_ME
Technicien --> UC_FICHE

Manager --> UC_FACTURES
Manager --> UC_FICHE

Admin --> UC_USERS
Admin --> UC_COMMANDES
Admin --> UC_FACTURES

Client --> UC_FACTURES

UC_AUTH ..> UC_USERS : <<include>>
UC_AUTH ..> UC_DM_CREATE : <<include>>
UC_AUTH ..> UC_DP_CREATE : <<include>>
UC_AUTH ..> UC_COMMANDES : <<include>>

@enduml
```