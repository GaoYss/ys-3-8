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

    def validate_status(self, value):
        if self.instance is None:
            return value
        old_status = self.instance.status
        new_status = value

        if old_status == BorrowRecord.Status.PENDING:
            if new_status in (
                BorrowRecord.Status.BORROWED,
                BorrowRecord.Status.OVERDUE,
                BorrowRecord.Status.APPROVED,
            ):
                raise serializers.ValidationError(
                    "待审批申请必须通过审批接口批准后才能进入借出状态，不能直接修改状态"
                )
            if new_status == BorrowRecord.Status.RETURNED:
                raise serializers.ValidationError("待审批申请不能直接标记为已归还")

        if old_status in (BorrowRecord.Status.BORROWED, BorrowRecord.Status.OVERDUE):
            if new_status == BorrowRecord.Status.RETURNED:
                raise serializers.ValidationError(
                    "归还操作请使用专用归还接口，不能直接修改状态"
                )
            if new_status in (
                BorrowRecord.Status.PENDING,
                BorrowRecord.Status.APPROVED,
                BorrowRecord.Status.REJECTED,
            ):
                raise serializers.ValidationError("借出中的记录不能回退到审批状态")

        if old_status == BorrowRecord.Status.REJECTED:
            if new_status in (
                BorrowRecord.Status.BORROWED,
                BorrowRecord.Status.OVERDUE,
                BorrowRecord.Status.APPROVED,
                BorrowRecord.Status.PENDING,
            ):
                raise serializers.ValidationError("已拒绝的申请不能重新进入借出或待审批状态")

        if old_status == BorrowRecord.Status.RETURNED:
            if new_status != BorrowRecord.Status.RETURNED:
                raise serializers.ValidationError("已归还的记录不能修改状态")

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

        if self.instance is not None:
            if self.instance.status == BorrowRecord.Status.PENDING:
                if attrs.get("actual_return_date") is not None:
                    raise serializers.ValidationError(
                        {"actual_return_date": "待审批申请不能登记实际归还日期"}
                    )
            if self.instance.status in (BorrowRecord.Status.BORROWED, BorrowRecord.Status.OVERDUE):
                if attrs.get("actual_return_date") is not None:
                    raise serializers.ValidationError(
                        {"actual_return_date": "归还操作请使用专用归还接口，不能直接修改实际归还日期"}
                    )

        return attrs
