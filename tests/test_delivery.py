import io, json, zipfile
from forgeai.delivery import build_delivery_archive, build_delivery_report

def _artifact(status="approved", content=None, artifact_id=1, version=1):
    return {"id":artifact_id,"version":version,"review_status":status,"review_notes":"","content":content or {}}

def test_readiness_requires_test_result_for_exact_current_source():
    project={"id":4,"name":"Demo","brief":"Build demo"}
    artifacts={"requirements":_artifact(),"architecture":_artifact(),"uiux_design":_artifact(),"code_bundle":_artifact(content={"files":[]},artifact_id=40),"qa_test_plan":_artifact(),"code_review":_artifact(),"execution_report":_artifact(content={"status":"passed","source_bundle_artifact_id":39})}
    report=build_delivery_report(project,artifacts,[{"event_type":"created"}])
    assert report["execution_evidence"]["status"]=="not_run_for_current_bundle"
    assert report["deployment_status"]=="not_deployed"
    assert report["readiness_percent"]==80

def test_current_bundle_pass_and_all_artifacts_score_full_readiness():
    project={"id":4,"name":"Demo","brief":"Build demo"}
    artifacts={"requirements":_artifact(),"architecture":_artifact(),"uiux_design":_artifact(),"code_bundle":_artifact(content={"files":[]},artifact_id=40),"qa_test_plan":_artifact(),"code_review":_artifact(),"execution_report":_artifact(content={"status":"passed","source_bundle_artifact_id":40})}
    report=build_delivery_report(project,artifacts,[{"event_type":"created"}])
    assert report["readiness_percent"]==100
    assert report["deployment_status"]=="not_deployed"

def test_delivery_archive_contains_artifacts_source_and_report():
    project={"id":4,"name":"Demo","brief":"Build demo"}
    artifacts={"code_bundle":_artifact(content={"files":[{"path":"src/main.py","content":"print('hello')"}]})}
    events=[{"event_type":"project_created","details":"created"}]
    report=build_delivery_report(project,artifacts,events)
    payload=build_delivery_archive(project,artifacts,events,report)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=set(archive.namelist())
        assert "delivery/source_bundle/src/main.py" in names
        assert "delivery/readiness_report.json" in names
        manifest=json.loads(archive.read("delivery/manifest.json"))
        assert manifest["deployment_status"]=="not_deployed"

def test_delivery_archive_rejects_unsafe_source_paths():
    project={"id":4,"name":"Demo","brief":""}
    artifacts={"code_bundle":_artifact(content={"files":[{"path":"../escape.py","content":"bad"}]})}
    report=build_delivery_report(project,artifacts,[])
    try:
        build_delivery_archive(project,artifacts,[],report)
    except ValueError as exc:
        assert "Unsafe source path" in str(exc)
    else:
        raise AssertionError("Unsafe path should be rejected.")
