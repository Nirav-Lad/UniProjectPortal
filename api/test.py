from django.db.models import Prefetch, F
from api.models import GroupFormation,GroupStudents

def get_groups_with_students(batch_id):
    # Prefetch only the students belonging to this batch
    student_prefetch = Prefetch(
        "group_students",
        queryset=GroupStudents.objects.filter(
            student_batch_link__current_batch_id=batch_id
        ).select_related("student_batch_link__enrollment"),
        to_attr="batch_students"
    )

    groups = GroupFormation.objects.filter(
        group_students__student_batch_link__current_batch_id=batch_id
    ).distinct().prefetch_related(student_prefetch)

    response = []

    for group in groups:
        students_list = [
            {
                "name": gs.student_batch_link.enrollment.name,
                "enrollment_id": gs.student_batch_link.enrollment.enrollment_id
            }
            for gs in group.batch_students
        ]

        response.append({
            "group_id": group.id,
            "status": group.status,
            "students": students_list
        })

    return response
