"""Canais de contato compartilhados por Pessoa e Entidade (ADR 0057).

1. Renomeia EmailPessoa → EmailContato preservando dados.
2. Cria Site (modelo novo com FKs duais).
3. Torna `pessoa` nullable em Telefone/EmailContato/RedeSocial.
4. Adiciona `entidade` (FK nullable) em Telefone/EmailContato/RedeSocial.
5. Data migration: copia Entidade.email/telefone/site pros novos models.
6. Drop dos campos Entidade.email/Entidade.telefone/Entidade.site.
7. Atualiza UniqueConstraints (por dono, com condition).
"""

import django.db.models.deletion
from django.db import migrations, models


def copiar_canais_simples_de_entidade_para_models_plurais(apps, schema_editor):
    """Migra dados dos campos simples de Entidade pros models plurais.

    - Entidade.email (1 campo) → EmailContato(entidade=ent, endereco=email)
    - Entidade.telefone (1 campo, só dígitos) → Telefone(entidade=ent,
      numero=tel, tipo=celular OU fixo conforme tamanho)
    - Entidade.site (1 campo) → Site(entidade=ent, url=site)
    """
    Entidade = apps.get_model("pessoas", "Entidade")
    Telefone = apps.get_model("pessoas", "Telefone")
    EmailContato = apps.get_model("pessoas", "EmailContato")
    Site = apps.get_model("pessoas", "Site")

    for ent in Entidade.objects.all():
        email = (ent.email or "").strip()
        if email:
            EmailContato.objects.create(entidade=ent, endereco=email)
        telefone = (ent.telefone or "").strip()
        if telefone:
            digitos = "".join(ch for ch in telefone if ch.isdigit())
            tipo = "celular" if len(digitos) == 11 else "fixo"
            if digitos:
                Telefone.objects.create(entidade=ent, numero=digitos, tipo=tipo)
        site = (ent.site or "").strip()
        if site:
            Site.objects.create(entidade=ent, url=site)


def reverter_canais_de_models_plurais_para_entidade(apps, schema_editor):
    """Reverso da data migration. Pega o PRIMEIRO de cada canal e coloca
    de volta no campo simples de Entidade. Múltiplos são perdidos
    (rollback intencionalmente lossy)."""
    Entidade = apps.get_model("pessoas", "Entidade")
    for ent in Entidade.objects.all():
        primeiro_email = ent.emails.first()
        if primeiro_email:
            ent.email = primeiro_email.endereco
        primeiro_telefone = ent.telefones.first()
        if primeiro_telefone:
            ent.telefone = primeiro_telefone.numero
        primeiro_site = ent.sites.first()
        if primeiro_site:
            ent.site = primeiro_site.url
        ent.save()


class Migration(migrations.Migration):

    dependencies = [
        ("pessoas", "0003_unicidade_canais"),
    ]

    operations = [
        # 1. Renomeia o modelo — preserva os registros existentes de EmailPessoa.
        migrations.RenameModel(old_name="EmailPessoa", new_name="EmailContato"),
        # 1a. Renomeia índices da tabela renomeada (Django gera novos hashes).
        migrations.RenameIndex(
            model_name="emailcontato",
            new_name="pessoas_ema_enderec_c71f6c_idx",
            old_name="pessoas_ema_enderec_e89ce0_idx",
        ),
        migrations.RenameIndex(
            model_name="emailcontato",
            new_name="pessoas_ema_pessoa__98d9e9_idx",
            old_name="pessoas_ema_pessoa__0a8579_idx",
        ),
        # 2. Remove constraints antigas (vão voltar com condition por dono).
        migrations.RemoveConstraint(model_name="telefone", name="telefone_unico_por_pessoa"),
        migrations.RemoveConstraint(model_name="redesocial", name="rede_social_unica_por_pessoa"),
        migrations.RemoveConstraint(model_name="emailcontato", name="email_unico_por_pessoa"),
        # 3. Torna `pessoa` nullable nos 3 models de canal.
        migrations.AlterField(
            model_name="telefone",
            name="pessoa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telefones",
                to="pessoas.pessoa",
            ),
        ),
        migrations.AlterField(
            model_name="emailcontato",
            name="pessoa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="emails",
                to="pessoas.pessoa",
            ),
        ),
        migrations.AlterField(
            model_name="redesocial",
            name="pessoa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="redes_sociais",
                to="pessoas.pessoa",
            ),
        ),
        # 4. Adiciona `entidade` (FK nullable) nos 3 models.
        migrations.AddField(
            model_name="telefone",
            name="entidade",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telefones",
                to="pessoas.entidade",
            ),
        ),
        migrations.AddField(
            model_name="emailcontato",
            name="entidade",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="emails",
                to="pessoas.entidade",
            ),
        ),
        migrations.AddField(
            model_name="redesocial",
            name="entidade",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="redes_sociais",
                to="pessoas.entidade",
            ),
        ),
        # 5. Cria o modelo Site (FKs duais, sem dados ainda).
        migrations.CreateModel(
            name="Site",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("url", models.URLField(max_length=500, verbose_name="URL")),
                (
                    "rotulo",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text='Opcional. Ex: "institucional", "projeto X", "blog".',
                        max_length=50,
                        verbose_name="rótulo",
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                (
                    "entidade",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sites",
                        to="pessoas.entidade",
                    ),
                ),
                (
                    "pessoa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sites",
                        to="pessoas.pessoa",
                    ),
                ),
            ],
            options={
                "verbose_name": "site",
                "verbose_name_plural": "sites",
                "ordering": ["criado_em"],
            },
        ),
        # 6. Data migration: copia Entidade.email/telefone/site pros models plurais.
        migrations.RunPython(
            copiar_canais_simples_de_entidade_para_models_plurais,
            reverter_canais_de_models_plurais_para_entidade,
        ),
        # 7. Drop dos campos simples agora que os dados foram migrados.
        migrations.RemoveField(model_name="entidade", name="email"),
        migrations.RemoveField(model_name="entidade", name="telefone"),
        migrations.RemoveField(model_name="entidade", name="site"),
        # 8. Índices novos.
        migrations.AddIndex(
            model_name="telefone",
            index=models.Index(fields=["entidade"], name="pessoas_tel_entidad_f3e39d_idx"),
        ),
        migrations.AddIndex(
            model_name="emailcontato",
            index=models.Index(fields=["entidade"], name="pessoas_ema_entidad_88f9eb_idx"),
        ),
        migrations.AddIndex(
            model_name="redesocial",
            index=models.Index(fields=["entidade"], name="pessoas_red_entidad_6f7755_idx"),
        ),
        migrations.AddIndex(
            model_name="site",
            index=models.Index(fields=["pessoa"], name="pessoas_sit_pessoa__05500c_idx"),
        ),
        migrations.AddIndex(
            model_name="site",
            index=models.Index(fields=["entidade"], name="pessoas_sit_entidad_71d875_idx"),
        ),
        # 9. Constraints unique por dono (condition Q evita conflito com nulos).
        migrations.AddConstraint(
            model_name="telefone",
            constraint=models.UniqueConstraint(
                condition=models.Q(("pessoa__isnull", False)),
                fields=("pessoa", "numero"),
                name="telefone_unico_por_pessoa",
                violation_error_message="Esta pessoa já tem este número cadastrado.",
            ),
        ),
        migrations.AddConstraint(
            model_name="telefone",
            constraint=models.UniqueConstraint(
                condition=models.Q(("entidade__isnull", False)),
                fields=("entidade", "numero"),
                name="telefone_unico_por_entidade",
                violation_error_message="Esta entidade já tem este número cadastrado.",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailcontato",
            constraint=models.UniqueConstraint(
                condition=models.Q(("pessoa__isnull", False)),
                fields=("pessoa", "endereco"),
                name="email_unico_por_pessoa",
                violation_error_message="Esta pessoa já tem este e-mail cadastrado.",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailcontato",
            constraint=models.UniqueConstraint(
                condition=models.Q(("entidade__isnull", False)),
                fields=("entidade", "endereco"),
                name="email_unico_por_entidade",
                violation_error_message="Esta entidade já tem este e-mail cadastrado.",
            ),
        ),
        migrations.AddConstraint(
            model_name="redesocial",
            constraint=models.UniqueConstraint(
                condition=models.Q(("pessoa__isnull", False)),
                fields=("pessoa", "plataforma", "valor"),
                name="rede_social_unica_por_pessoa",
                violation_error_message="Esta pessoa já tem este perfil cadastrado nesta plataforma.",
            ),
        ),
        migrations.AddConstraint(
            model_name="redesocial",
            constraint=models.UniqueConstraint(
                condition=models.Q(("entidade__isnull", False)),
                fields=("entidade", "plataforma", "valor"),
                name="rede_social_unica_por_entidade",
                violation_error_message="Esta entidade já tem este perfil cadastrado nesta plataforma.",
            ),
        ),
        migrations.AddConstraint(
            model_name="site",
            constraint=models.UniqueConstraint(
                condition=models.Q(("pessoa__isnull", False)),
                fields=("pessoa", "url"),
                name="site_unico_por_pessoa",
                violation_error_message="Esta pessoa já tem este site cadastrado.",
            ),
        ),
        migrations.AddConstraint(
            model_name="site",
            constraint=models.UniqueConstraint(
                condition=models.Q(("entidade__isnull", False)),
                fields=("entidade", "url"),
                name="site_unico_por_entidade",
                violation_error_message="Esta entidade já tem este site cadastrado.",
            ),
        ),
        # 10. CheckConstraints garantem XOR no nível do banco — impossível
        # persistir um canal com ambos donos preenchidos ou ambos vazios.
        migrations.AddConstraint(
            model_name="telefone",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(pessoa__isnull=False, entidade__isnull=True)
                    | models.Q(pessoa__isnull=True, entidade__isnull=False)
                ),
                name="telefone_dono_xor",
                violation_error_message="Telefone precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailcontato",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(pessoa__isnull=False, entidade__isnull=True)
                    | models.Q(pessoa__isnull=True, entidade__isnull=False)
                ),
                name="email_dono_xor",
                violation_error_message="E-mail precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ),
        migrations.AddConstraint(
            model_name="redesocial",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(pessoa__isnull=False, entidade__isnull=True)
                    | models.Q(pessoa__isnull=True, entidade__isnull=False)
                ),
                name="rede_social_dono_xor",
                violation_error_message="Rede social precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ),
        migrations.AddConstraint(
            model_name="site",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(pessoa__isnull=False, entidade__isnull=True)
                    | models.Q(pessoa__isnull=True, entidade__isnull=False)
                ),
                name="site_dono_xor",
                violation_error_message="Site precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ),
    ]
