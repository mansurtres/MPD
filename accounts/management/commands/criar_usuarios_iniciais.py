from django.core.management.base import BaseCommand

from accounts.models import Usuario


class Command(BaseCommand):
    help = "Cria um usuário is_staff e um usuário comum para desenvolvimento local."

    def handle(self, *args, **options):
        criados = 0

        if not Usuario.objects.filter(email="admin@mpd.local").exists():
            Usuario.objects.create_superuser(
                email="admin@mpd.local",
                password="admin12345",  # pragma: allowlist secret
                nome_completo="Administrador",
                cargo="Administrador do sistema",
            )
            self.stdout.write(
                self.style.SUCCESS("Criado: admin@mpd.local (is_staff=True, senha: admin12345)")
            )
            criados += 1

        if not Usuario.objects.filter(email="usuario@mpd.local").exists():
            Usuario.objects.create_user(
                email="usuario@mpd.local",
                password="usuario12345",  # pragma: allowlist secret
                nome_completo="Usuário Teste",
                cargo="Assessor",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Criado: usuario@mpd.local (is_staff=False, senha: usuario12345)"
                )
            )
            criados += 1

        if criados == 0:
            self.stdout.write("Usuários já existem, nada criado.")
