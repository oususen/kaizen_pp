from rest_framework import routers

from .views import DepartmentViewSet, ProposalViewSet

router = routers.DefaultRouter()
router.register(r"departments", DepartmentViewSet)
router.register(r"proposals", ProposalViewSet)

urlpatterns = router.urls
