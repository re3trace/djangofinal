
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

from .models import Course, Learner, Question, Choice, Submission


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    return render(
        request,
        'onlinecourse_app/course_details_bootstrap.html',
        {'course': course}
    )


@login_required
@require_POST
def submit(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    learner, created = Learner.objects.get_or_create(
        user=request.user
    )

    submission = Submission.objects.create(
        learner=learner,
        course=course
    )

    selected_ids = []

    for key, value in request.POST.items():
        if key.startswith('choice_'):
            selected_ids.append(value)

    valid_choices = Choice.objects.filter(
        id__in=selected_ids,
        question__lesson__course=course
    )

    submission.choices.set(valid_choices)

    return redirect(
        'onlinecourse_app:show_exam_result',
        submission_id=submission.id
    )


@login_required
def show_exam_result(request, submission_id):
    submission = get_object_or_404(
        Submission,
        id=submission_id,
        learner__user=request.user
    )

    course = submission.course

    questions = Question.objects.filter(
        lesson__course=course
    ).prefetch_related('choices')

    selected_ids = set(
        submission.choices.values_list('id', flat=True)
    )

    total_score = 0
    earned_score = 0
    exam_results = []

    for question in questions:
        correct_ids = {
            choice.id
            for choice in question.choices.all()
            if choice.is_correct
        }

        chosen_ids = {
            choice.id
            for choice in question.choices.all()
            if choice.id in selected_ids
        }

        is_correct = chosen_ids == correct_ids and bool(correct_ids)

        total_score += question.grade

        if is_correct:
            earned_score += question.grade

        exam_results.append({
            'question': question,
            'is_correct': is_correct,
            'selected_choices': [
                choice for choice in question.choices.all()
                if choice.id in chosen_ids
            ],
            'correct_choices': [
                choice for choice in question.choices.all()
                if choice.id in correct_ids
            ],
        })

    percentage = (
        round(earned_score / total_score * 100, 2)
        if total_score > 0 else 0
    )

    passed = total_score > 0 and percentage >= 70

    context = {
        'course': course,
        'submission': submission,
        'exam_results': exam_results,
        'earned_score': earned_score,
        'total_score': total_score,
        'percentage': percentage,
        'passed': passed,
    }

    return render(
        request,
        'onlinecourse_app/exam_result.html',
        context
    )
