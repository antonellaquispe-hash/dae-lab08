from rest_framework.routers import DefaultRouter

from .views import ChoiceViewSet, ExamViewSet, QuestionViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("questions", QuestionViewSet, basename="question")
router.register("choices", ChoiceViewSet, basename="choice")

urlpatterns = router.urls
