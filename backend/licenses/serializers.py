from django.utils import timezone
from rest_framework import serializers

from .models import BorrowRecord, License


class LicenseSerializer(serializers.ModelSerializer):
    days_until_expiry = serializers.IntegerField(read_only=True)
    computed_status = serializers.CharField(read_only=True)
    license_type_display = serializers.CharField(source="get_license_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = License
        fields = [
            "id",
            "name",
            "license_no",
            "license_type",
            "license_type_display",
            "issuing_authority",
            "owner_department",
            "keeper",
            "issue_date",
            "expiry_date",
            "reminder_days",
            "status",
            "status_display",
            "computed_status",
            "days_until_expiry",
            "is_expired",
            "notes",
            "created_at",
            "updated_at",
        ]

    def get_is_expired(self, obj):
        return obj.computed_status == License.Status.EXPIRED


class BorrowRecordSerializer(serializers.ModelSerializer):
    license_name = serializers.CharField(source="license.name", read_only=True)
    license_keeper = serializers.CharField(source="license.keeper", read_only=True)
    computed_status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BorrowRecord
        fields = [
            "id",
            "license",
            "license_name",
            "license_keeper",
            "borrower",
            "borrower_department",
            "purpose",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "status",
            "status_display",
            "computed_status",
            "approver",
            "approved_at",
            "approval_notes",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approver", "approved_at", "approval_notes"]

    def validate_license(self, value):
        if value.computed_status == License.Status.EXPIRED:
            raise serializers.ValidationError("已过期的证照不能发起借用")
        return value

    def validate(self, attrs):
        borrow_date = attrs.get("borrow_date", getattr(self.instance, "borrow_date", None))
        expected_return_date = attrs.get("expected_return_date", getattr(self.instance, "expected_return_date", None))
        actual_return_date = attrs.get("actual_return_date", getattr(self.instance, "actual_return_date", None))

        if expected_return_date and borrow_date and expected_return_date < borrow_date:
            raise serializers.ValidationError({"expected_return_date": "预计归还日期不能早于借出日期"})
        if actual_return_date and borrow_date and actual_return_date < borrow_date:
            raise serializers.ValidationError({"actual_return_date": "实际归还日期不能早于借出日期"})

        if self.instance is None:
            attrs["status"] = BorrowRecord.Status.PENDING

        return attrs
