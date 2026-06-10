"""Department limits and default structure for the organisation."""

MAX_SOCIETY_DEPARTMENTS = 5

DEFAULT_DEPARTMENTS = [
    {
        'nom_dept': 'Maintenance Industrielle',
        'description': 'Coordination des interventions, planification et suivi des demandes de maintenance.',
    },
    {
        'nom_dept': 'Atelier Mécanique',
        'description': 'Réparation mécanique, usinage et maintenance des équipements de production.',
    },
    {
        'nom_dept': 'Électricité & Automatisme',
        'description': 'Maintenance électrique, câblage, automates et systèmes de contrôle.',
    },
    {
        'nom_dept': 'Logistique & Stock',
        'description': 'Gestion des pièces détachées, approvisionnement et magasin technique.',
    },
]

# Old placeholder names mapped to canonical departments (keeps user assignments).
LEGACY_DEPARTMENT_ALIASES = {
    'it dep': 'Maintenance Industrielle',
    'it': 'Maintenance Industrielle',
}


def society_department_count():
    from .models import Department
    return Department.objects.count()


def can_create_department():
    from .models import Department
    return Department.objects.count() < MAX_SOCIETY_DEPARTMENTS


def department_limit_error_message():
    return (
        f'Une société ne peut pas avoir plus de {MAX_SOCIETY_DEPARTMENTS} départements. '
        f'Supprimez ou fusionnez un département avant d\'ajouter un nouveau.'
    )


def seed_default_departments():
    from .models import Department

    created = 0
    renamed = 0

    for old_name, new_name in LEGACY_DEPARTMENT_ALIASES.items():
        legacy = Department.objects.filter(nom_dept__iexact=old_name).first()
        if not legacy:
            continue
        canonical = Department.objects.filter(nom_dept__iexact=new_name).exclude(id=legacy.id).first()
        if canonical:
            legacy.employees.update(department=canonical)
            legacy.delete()
            renamed += 1
        else:
            legacy.nom_dept = new_name
            legacy.save(update_fields=['nom_dept'])
            renamed += 1

    for item in DEFAULT_DEPARTMENTS:
        _, was_created = Department.objects.get_or_create(
            nom_dept=item['nom_dept'],
            defaults={'description': item['description']},
        )
        if was_created:
            created += 1

    return {
        'created': created,
        'renamed': renamed,
        'total': Department.objects.count(),
        'max': MAX_SOCIETY_DEPARTMENTS,
    }
