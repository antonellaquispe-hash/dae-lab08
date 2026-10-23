from rest_framework.routers import DefaultRouter

from .views import ExamViewSet, QuestionViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("questions", QuestionViewSet, basename="question")

urlpatterns = router.urls
