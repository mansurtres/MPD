from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("E-mail é obrigatório.")
        if not password:
            raise ValueError("Senha é obrigatória — sem ela, a conta nasce sem login.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    objects = UsuarioManager()

    COORDENACAO_GABINETE = "gabinete"
    COORDENACAO_JURIDICO = "juridico"
    COORDENACAO_COMUNICACAO = "comunicacao"
    COORDENACAO_CHOICES = [
        (COORDENACAO_GABINETE, "Gabinete"),
        (COORDENACAO_JURIDICO, "Jurídico"),
        (COORDENACAO_COMUNICACAO, "Comunicação"),
    ]

    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField("nome completo", max_length=200, blank=True)
    cargo = models.CharField("cargo", max_length=100, blank=True)
    coordenacao = models.CharField(
        "coordenação",
        max_length=15,
        choices=COORDENACAO_CHOICES,
        blank=True,
        default="",
        help_text="Define escopo de visibilidade de demandas (ADR 0041).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.nome_completo or self.email

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
