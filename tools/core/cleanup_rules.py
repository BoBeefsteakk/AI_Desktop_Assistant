from __future__ import annotations

from typing import Any

from tools.core.risk_classifier import PROTECTED, REVIEW_REQUIRED, SAFE_DELETE


CLEANUP_RULE_SCHEMA = "cleanup_rule_registry_v1"


def build_cleanup_rule_registry() -> dict[str, Any]:
    return {
        "schema": CLEANUP_RULE_SCHEMA,
        "status": "ready",
        "source_of_truth": "tools.core.risk_classifier.classify_file_risk",
        "rules": [
            {
                "risk": SAFE_DELETE,
                "recommended_decision": "delete_candidate",
                "plan_action": "delete_candidate",
                "can_recommend_delete": True,
                "reason_text": "Chi file duoc Risk Classifier xep safe_delete moi duoc de xuat xoa.",
            },
            {
                "risk": REVIEW_REQUIRED,
                "recommended_decision": "manual_review",
                "plan_action": "manual_review",
                "can_recommend_delete": False,
                "reason_text": "File review_required phai xem tay; khong duoc de xuat xoa mac dinh.",
            },
            {
                "risk": PROTECTED,
                "recommended_decision": "keep",
                "plan_action": "keep",
                "can_recommend_delete": False,
                "reason_text": "File protected bi khoa va chi duoc giu.",
            },
        ],
        "safety_contract": {
            "read_only": True,
            "executes_file_operations": False,
            "delete_candidate_requires_safe_delete_risk": True,
            "review_required_can_recommend_delete": False,
            "protected_can_recommend_delete": False,
        },
    }


def get_cleanup_recommendation(risk_result: dict[str, Any]) -> dict[str, Any]:
    risk = str(risk_result.get("risk") or REVIEW_REQUIRED)
    registry = build_cleanup_rule_registry()
    rule = next(
        (item for item in registry["rules"] if item["risk"] == risk),
        next(item for item in registry["rules"] if item["risk"] == REVIEW_REQUIRED),
    )
    return {
        **rule,
        "risk_category": risk_result.get("category"),
        "matched_rule": risk_result.get("matched_rule"),
        "classifier_reason": risk_result.get("reason"),
    }


def validate_cleanup_rule_registry() -> dict[str, Any]:
    registry = build_cleanup_rule_registry()
    issues = []
    rules = registry["rules"]
    delete_rules = [item for item in rules if item["recommended_decision"] == "delete_candidate"]

    if len(delete_rules) != 1 or delete_rules[0]["risk"] != SAFE_DELETE:
        issues.append("delete_candidate must be mapped only from safe_delete risk.")

    for rule in rules:
        if rule["risk"] in {REVIEW_REQUIRED, PROTECTED} and rule["can_recommend_delete"]:
            issues.append(f"{rule['risk']} must never recommend delete.")

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
        "schema": registry["schema"],
        "rule_count": len(rules),
    }
