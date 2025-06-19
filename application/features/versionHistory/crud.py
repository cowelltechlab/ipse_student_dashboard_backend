from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.cosmos import ContainerProxy
from application.features.versionHistory.schemas import AssignmentVersionCreate, AssignmentVersionUpdate

def get_doc_id(student_id: int, assignment_id: str) -> str:
    return f"{student_id}:{assignment_id}"

def create_or_append_version(container: ContainerProxy, student_id: int, assignment_id: str, new_version: AssignmentVersionCreate):
    doc_id = get_doc_id(student_id, assignment_id)
    version_dict = new_version.model_dump()
    
    partition_key = str(student_id)  # make sure this matches your container's partition key type

    try:
        doc = container.read_item(item=doc_id, partition_key=partition_key)
        versions = doc.get("versions", [])

        # check for duplicate version_number
        for v in versions:
            if v.get("version_number") == version_dict.get("version_number"):
                raise ValueError(f"Version {version_dict.get('version_number')} already exists")

        versions.append(version_dict)
        doc["versions"] = versions
        container.replace_item(item=doc_id, body=doc)
    except CosmosResourceNotFoundError:
        doc = {
            "id": doc_id,
            "student_id": partition_key,
            "assignment_id": assignment_id,
            "versions": [version_dict]
        }
        container.create_item(doc)
    return doc

def get_all_versions(container: ContainerProxy, student_id: int, assignment_id: str):
    doc_id = get_doc_id(student_id, assignment_id)
    try:
        doc = container.read_item(item=doc_id, partition_key=student_id)
        return doc.get("versions", [])
    except CosmosResourceNotFoundError:
        return []

def get_version(container: ContainerProxy, student_id: int, assignment_id: str, version_number: int):
    doc_id = get_doc_id(student_id, assignment_id)
    doc = container.read_item(item=doc_id, partition_key=student_id)
    versions = doc.get("versions", [])
    for v in versions:
        if v.get("version_number") == version_number:
            return v
    raise CosmosResourceNotFoundError(f"Version {version_number} not found")

def update_version(container: ContainerProxy, student_id: int, assignment_id: str, version_number: int, update_data: AssignmentVersionUpdate):
    doc_id = get_doc_id(student_id, assignment_id)
    doc = container.read_item(item=doc_id, partition_key=student_id)
    versions = doc.get("versions", [])

    updated = False
    for idx, v in enumerate(versions):
        if v.get("version_number") == version_number:
            update_dict = update_data.model_dump(exclude_unset=True)
            versions[idx].update(update_dict)
            updated = True
            break

    if not updated:
        raise CosmosResourceNotFoundError(f"Version {version_number} not found")

    doc["versions"] = versions
    container.replace_item(item=doc_id, body=doc)
    return versions[idx]

def delete_version(container: ContainerProxy, student_id: int, assignment_id: str, version_number: int):
    doc_id = get_doc_id(student_id, assignment_id)
    doc = container.read_item(item=doc_id, partition_key=student_id)
    versions = doc.get("versions", [])

    new_versions = [v for v in versions if v.get("version_number") != version_number]
    if len(new_versions) == len(versions):
        raise CosmosResourceNotFoundError(f"Version {version_number} not found")

    doc["versions"] = new_versions
    container.replace_item(item=doc_id, body=doc)
