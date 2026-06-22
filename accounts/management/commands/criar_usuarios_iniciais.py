from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Usuario


class Command(BaseCommand):
    help = "Cria um usuário de cada papel (Admin, Chefe de Gabinete, Assessor) para dev local."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "criar_usuarios_iniciais usa senhas fixas em código e só pode rodar com "
                "DEBUG=True. Em produção, semeie usuários via Django Admin ou data migration."
            )

        admin, criado_admin = Usuario.objects.get_or_create(
            email="admin@mpd.local",
            defaults={
                "username": "admin@mpd.local",
                "nome_completo": "Administrador",
                "cargo": "Administrador do sistema",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if criado_admin:
            admin.set_password("admin12345")  # pragma: allowlist secret
            admin.save()
            self.stdout.write(
                self.style.SUCCESS("Criado: admin@mpd.local (is_staff=True, senha: admin12345)")
            )
        grupo_adm = Group.objects.filter(name="Administrador").first()
        if grupo_adm and not admin.groups.filter(pk=grupo_adm.pk).exists():
            admin.groups.add(grupo_adm)
            self.stdout.write("admin@mpd.local adicionado ao grupo Administrador.")

        usuario, criado_usuario = Usuario.objects.get_or_create(
            email="usuario@mpd.local",
            defaults={
                "username": "usuario@mpd.local",
                "nome_completo": "Usuário Teste",
                "cargo": "Assessor",
            },
        )
        if criado_usuario:
            usuario.set_password("usuario12345")  # pragma: allowlist secret
            usuario.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "Criado: usuario@mpd.local (is_staff=False, senha: usuario12345)"
                )
            )
        grupo_assessor = Group.objects.filter(name="Assessor").first()
        if grupo_assessor and not usuario.groups.filter(pk=grupo_assessor.pk).exists():
            usuario.groups.add(grupo_assessor)
            self.stdout.write("usuario@mpd.local adicionado ao grupo Assessor.")

        chefe, criado_chefe = Usuario.objects.get_or_create(
            email="chefe@mpd.local",
            defaults={
                "username": "chefe@mpd.local",
                "nome_completo": "Chefe de Gabinete",
                "cargo": "Chefe de Gabinete",
            },
        )
        if criado_chefe:
            chefe.set_password("chefe12345")  # pragma: allowlist secret
            chefe.save()
            self.stdout.write(self.style.SUCCESS("Criado: chefe@mpd.local (senha: chefe12345)"))
        grupo_cg = Group.objects.filter(name="Chefe de Gabinete").first()
        if grupo_cg and not chefe.groups.filter(pk=grupo_cg.pk).exists():
            chefe.groups.add(grupo_cg)
            self.stdout.write("chefe@mpd.local adicionado ao grupo Chefe de Gabinete.")

        if not criado_admin and not criado_usuario and not criado_chefe:
            self.stdout.write("Usuários já existiam; grupos sincronizados se necessário.")
