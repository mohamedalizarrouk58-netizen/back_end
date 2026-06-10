from django.core.management.base import BaseCommand

from users.department_policy import MAX_SOCIETY_DEPARTMENTS, seed_default_departments


class Command(BaseCommand):
    help = 'Create the 4 default company departments (max 5 per société).'

    def handle(self, *args, **options):
        stats = seed_default_departments()

        self.stdout.write(self.style.SUCCESS('Departments ready:'))
        self.stdout.write(f'  created: {stats["created"]}')
        self.stdout.write(f'  renamed legacy: {stats["renamed"]}')
        self.stdout.write(f'  total: {stats["total"]} / {MAX_SOCIETY_DEPARTMENTS} max')

        from users.models import Department
        for dept in Department.objects.order_by('nom_dept'):
            self.stdout.write(f'  - {dept.nom_dept}')
