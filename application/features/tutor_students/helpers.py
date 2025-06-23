from collections import defaultdict


def group_tutor_students(flat_records):
    grouped = defaultdict(lambda: {"tutor_id": None, "tutor_name": None, "students": []})

    for record in flat_records:
        tutor_id = record["tutor_id"]
        if grouped[tutor_id]["tutor_id"] is None:
            grouped[tutor_id]["tutor_id"] = tutor_id
            grouped[tutor_id]["tutor_name"] = record["tutor_name"]

        grouped[tutor_id]["students"].append({
            "id": record["id"],
            "student_id": record["student_id"],
            "student_name": record["student_name"]
        })

    return list(grouped.values())