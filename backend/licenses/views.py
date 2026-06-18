from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import BorrowRecord, License
from .serializers import BorrowRecordSerializer, LicenseSerializer
from .services import dashboard_stats, refresh_borrow_status, refresh_license_status


class LicenseViewSet(viewsets.ModelViewSet):
    serializer_class = LicenseSerializer

    def get_queryset(self):
        queryset = License.objects.all()
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")
        license_type = self.request.query_params.get("type")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(license_no__icontains=search)
                | Q(issuing_authority__icontains=search)
                | Q(owner_department__icontains=search)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if license_type:
            queryset = queryset.filter(license_type=license_type)
        return queryset

    def perform_create(self, serializer):
        license_obj = serializer.save()
        refresh_license_status(license_obj)

    def perform_update(self, serializer):
        license_obj = serializer.save()
        refresh_license_status(license_obj)


class BorrowRecordViewSet(viewsets.ModelViewSet):
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        queryset = BorrowRecord.objects.select_related("license")
        status_filter = self.request.query_params.get("status")
        license_id = self.request.query_params.get("license")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if license_id:
            queryset = queryset.filter(license_id=license_id)
        return queryset

    def perform_create(self, serializer):
        record = serializer.save()
        refresh_borrow_status(record)

    def perform_update(self, serializer):
        record = serializer.save()
        refresh_borrow_status(record)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.status != BorrowRecord.Status.PENDING:
            return Response(
                {"detail": "只有待审批的申请可以批准"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        keeper = record.license.keeper
        if not keeper or not keeper.strip():
            return Response(
                {"detail": "该证照未指定保管人，请先在证照信息中设置保管人后再审批"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approval_notes = request.data.get("approval_notes", "")
        record.status = BorrowRecord.Status.BORROWED
        record.approver = keeper.strip()
        record.approved_at = timezone.now()
        record.approval_notes = approval_notes
        record.save()
        refresh_borrow_status(record)
        serializer = self.get_serializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        record = self.get_object()
        if record.status != BorrowRecord.Status.PENDING:
            return Response(
                {"detail": "只有待审批的申请可以拒绝"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        keeper = record.license.keeper
        if not keeper or not keeper.strip():
            return Response(
                {"detail": "该证照未指定保管人，请先在证照信息中设置保管人后再审批"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approval_notes = request.data.get("approval_notes", "")
        record.status = BorrowRecord.Status.REJECTED
        record.approver = keeper.strip()
        record.approved_at = timezone.now()
        record.approval_notes = approval_notes
        record.save()
        serializer = self.get_serializer(record)
        return Response(serializer.data)


@api_view(["GET"])
def stats_view(_request):
    stats = dashboard_stats()
    return Response(
        {
            **{key: value for key, value in stats.items() if key not in {"upcoming_expiries", "expired"}},
            "upcoming_expiries": LicenseSerializer(stats["upcoming_expiries"], many=True).data,
            "expired": LicenseSerializer(stats["expired"], many=True).data,
        }
    )
