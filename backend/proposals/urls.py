from rest_framework import routers
from django.urls import path

from .views import (
    CurrentEmployeeView,
    DepartmentViewSet,
    EmployeeViewSet,
    ImprovementProposalViewSet,
)

router = routers.DefaultRouter()
router.register(r"departments", DepartmentViewSet)
router.register(r"employees", EmployeeViewSet)
router.register(r"improvement-proposals", ImprovementProposalViewSet, basename="improvement-proposals")

urlpatterns = router.urls + [
    path("employees/me/", CurrentEmployeeView.as_view(), name="employees-me"),
]
