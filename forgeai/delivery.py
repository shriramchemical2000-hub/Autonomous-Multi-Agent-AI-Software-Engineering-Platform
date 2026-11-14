"""Deterministic delivery readiness reports and portable project exports."""
from __future__ import annotations
import io, json, zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

ARTIFACT_TYPES = (
    "requirements",
    "architecture",
    "uiux_design",
    "code_bundle",
    "qa_test_plan",
    "code_review",
    "execution_report",
    "repair_report",
)

def _approved(artifacts: dict[str, dict[str, Any]], kind: str) -> bool:
    item = artifacts.get(kind)
    return bool(item and item.get("review_status") == "approved")

def build_delivery_report(project: dict[str, Any], artifacts: dict[str, dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate evidence and approvals without inferring deployment or test success."""
    code = artifacts.get("code_bundle")
    execution = artifacts.get("execution_report")
    execution_current = bool(code and execution and execution.get("content", {}).get("source_bundle_artifact_id") == code.get("id"))
    execution_passed = bool(execution_current and execution["content"].get("status") == "passed")
    checks = [
        {"key":"requirements_approved","label":"Requirements approved","passed":_approved(artifacts,"requirements"),"weight":15},
        {"key":"architecture_approved","label":"Architecture approved","passed":_approved(artifacts,"architecture"),"weight":15},
        {"key":"experience_approved","label":"UI/UX specification approved","passed":_approved(artifacts,"uiux_design"),"weight":10},
        {"key":"source_approved","label":"Source bundle approved","passed":_approved(artifacts,"code_bundle"),"weight":15},
        {"key":"qa_plan_available","label":"QA plan generated","passed":"qa_test_plan" in artifacts,"weight":10},
        {"key":"static_review_available","label":"Static code review generated","passed":"code_review" in artifacts,"weight":10},
        {"key":"current_tests_passed","label":"Current source bundle passed Docker tests","passed":execution_passed,"weight":20},
        {"key":"project_audit_available","label":"Project audit history available","passed":bool(events),"weight":5},
    ]
    score = sum(item["weight"] for item in checks if item["passed"])
    return {
        "report_version":"1.0","project_id":project["id"],"project_name":project["name"],
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "readiness_score":score,"readiness_percent":score,
        "readiness_label":"Evidence complete" if score == 100 else "Work remaining",
        "checks":checks,"blockers":[item["label"] for item in checks if not item["passed"]],
        "deployment_status":"not_deployed",
        "deployment_note":"ForgeAI does not deploy projects. Hosting, persistent storage, secrets, domain, and production validation require operator setup.",
        "execution_evidence":{"current_source_bundle":bool(execution_current),"status":execution["content"].get("status") if execution_current else "not_run_for_current_bundle","source_bundle_artifact_id":code.get("id") if code else None},
        "artifact_versions":{kind:item.get("version") for kind,item in artifacts.items()},
        "audit_event_count":len(events),
    }

def build_delivery_archive(project: dict[str, Any], artifacts: dict[str, dict[str, Any]], events: list[dict[str, Any]], report: dict[str, Any]) -> bytes:
    """Create a portable ZIP of available engineering evidence and generated source."""
    manifest = {"package_format":"forgeai-delivery-v1","project":{"id":project["id"],"name":project["name"],"brief":project.get("brief","")},"generated_at":report["generated_at"],"artifact_versions":report["artifact_versions"],"deployment_status":report["deployment_status"],"contents":sorted(artifacts.keys())}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("delivery/README.md",_delivery_readme(project,report))
        archive.writestr("delivery/manifest.json",json.dumps(manifest,indent=2,ensure_ascii=False))
        archive.writestr("delivery/readiness_report.json",json.dumps(report,indent=2,ensure_ascii=False))
        archive.writestr("delivery/project_brief.txt",project.get("brief",""))
        archive.writestr("delivery/audit_events.json",json.dumps(events,indent=2,ensure_ascii=False))
        for kind,artifact in sorted(artifacts.items()):
            archive.writestr(f"delivery/artifacts/{kind}/v{artifact['version']}.json",json.dumps({"artifact_id":artifact["id"],"version":artifact["version"],"review_status":artifact["review_status"],"review_notes":artifact.get("review_notes",""),"content":artifact["content"]},indent=2,ensure_ascii=False))
        code = artifacts.get("code_bundle")
        if code:
            for source in code["content"].get("files",[]):
                path = PurePosixPath(source["path"])
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise ValueError("Unsafe source path found while building delivery archive.")
                archive.writestr(f"delivery/source_bundle/{path.as_posix()}",source["content"])
    return buffer.getvalue()

def _delivery_readme(project: dict[str, Any], report: dict[str, Any]) -> str:
    checks = "\n".join(f"- [{'x' if item['passed'] else ' '}] {item['label']}" for item in report["checks"])
    return f"""# ForgeAI Delivery Package

## Project
- Name: {project['name']}
- Project ID: {project['id']}
- Readiness score: {report['readiness_percent']}%

## Evidence checklist
{checks}

## Important status
Deployment status: NOT DEPLOYED.

This archive contains generated engineering artifacts and, when available, the source bundle. It is not a production release certification. Review source code, install dependencies deliberately, run included tests in an isolated environment, configure persistent storage and secrets, and complete security/privacy/accessibility checks before deployment.
"""
