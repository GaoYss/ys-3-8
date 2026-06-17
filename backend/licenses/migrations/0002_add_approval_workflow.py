from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("licenses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="borrowrecord",
            name="approver",
            field=models.CharField(blank=True, max_length=60, verbose_name="审批人"),
        ),
        migrations.AddField(
            model_name="borrowrecord",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="审批时间"),
        ),
        migrations.AddField(
            model_name="borrowrecord",
            name="approval_notes",
            field=models.TextField(blank=True, verbose_name="审批备注"),
        ),
        migrations.AlterField(
            model_name="borrowrecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "待审批"),
                    ("approved", "已批准"),
                    ("rejected", "已拒绝"),
                    ("borrowed", "借出中"),
                    ("returned", "已归还"),
                    ("overdue", "逾期未还"),
                ],
                default="pending",
                max_length=32,
                verbose_name="状态",
            ),
        ),
        migrations.AlterModelOptions(
            name="borrowrecord",
            options={"ordering": ["-created_at"]},
        ),
    ]
