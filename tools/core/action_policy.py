from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import DATA_DIR
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report, read_recent_report_index


ACTION_POLICY_FILE = DATA_DIR / "action_policy.jsonl"

VALID_DECISIONS = {
    "keep",
    "move_later",
    "delete_candidate",
    "ignore_forever",
    "needs_backup",
    "manual_only",
}
VALID_TARGET_TYPES = {
    "path_exact",
    "path_prefix",
    "path_contains",
    "context",
    "recommendation",
    "file_extension",
}
DECISION_PRIORITY = {
    "ignore_forever": 0,
    "manual_only": 1,
    "needs_backup": 2,
    "move_later": 3,
    "keep": 4,
    "delete_candidate": 5,
}
POLICY_CONFIRMATION_TOKENS = {
    "manual_only": "OPEN_MANUAL",
    "needs_backup": "OPEN_BACKUP",
    "move_later": "OPEN_MOVE_LATER",
    "delete_candidate": "OPEN_DELETE_CANDIDATE",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_decision(value: Any, default: str = "manual_only") -> str:
    decision = str(value or "").strip().lower()
    return decision if decision in VALID_DECISIONS else default


def normalize_target_type(value: Any, default: str = "path_contains") -> str:
    target_type = str(value or "").strip().lower()
    return target_type if target_type in VALID_TARGET_TYPES else default


def get_policy_file(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else ACTION_POLICY_FILE


def make_policy_fingerprint(policy: dict[str, Any]) -> str:
    parts = [
        str(policy.get("target_type") or ""),
        str(policy.get("target") or ""),
        str(policy.get("source") or ""),
    ]
    payload = "\n".join(part.strip().lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def make_policy(
    *,
    target_type: str,
    target: str,
    decision: str,
    reason: str,
    source: str = "manual",
    context: str | None = None,
    recommendation_id: str | None = None,
    tags: list[str] | None = None,
    active: bool = True,
) -> dict[str, Any]:
    policy = {
        "target_type": normalize_target_type(target_type),
        "target": str(target).strip(),
        "decision": normalize_decision(decision),
        "reason": str(reason).strip(),
        "source": str(source).strip() or "manual",
        "context": str(context).strip() if context else None,
        "recommendation_id": str(recommendation_id).strip() if recommendation_id else None,
        "tags": tags or [],
        "active": bool(active),
        "updated_at": now_iso(),
    }
    policy["fingerprint"] = make_policy_fingerprint(policy)
    return policy


def append_policy_event(
    policy: dict[str, Any],
    *,
    policy_file: str | Path | None = None,
) -> dict[str, Any]:
    path = get_policy_file(policy_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    normalized = make_policy(
        target_type=str(policy.get("target_type") or ""),
        target=str(policy.get("target") or ""),
        decision=str(policy.get("decision") or ""),
        reason=str(policy.get("reason") or ""),
        source=str(policy.get("source") or "manual"),
        context=policy.get("context"),
        recommendation_id=policy.get("recommendation_id"),
        tags=list(policy.get("tags") or []),
        active=bool(policy.get("active", True)),
    )

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(normalized, ensure_ascii=False) + "\n")

    return normalized


def read_policy_events(policy_file: str | Path | None = None) -> list[dict[str, Any]]:
    path = get_policy_file(policy_file)
    if not path.exists():
        return []

    events = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                target = str(data.get("target") or "").strip()
                if not target:
                    continue
                data["target_type"] = normalize_target_type(data.get("target_type"))
                data["decision"] = normalize_decision(data.get("decision"))
                data["fingerprint"] = str(data.get("fingerprint") or make_policy_fingerprint(data))
                data["active"] = bool(data.get("active", True))
                events.append(data)
    except OSError:
        return []

    return events


def get_active_policies(policy_file: str | Path | None = None) -> list[dict[str, Any]]:
    latest_by_fingerprint: dict[str, dict[str, Any]] = {}
    for event in read_policy_events(policy_file):
        latest_by_fingerprint[event["fingerprint"]] = event

    return [
        item for item in latest_by_fingerprint.values()
        if item.get("active", True)
    ]


def classify_path_context(path: str | Path) -> str:
    file_path = Path(path)
    lower_path = str(file_path).lower()
    parts = {part.lower() for part in file_path.parts}

    if "riot games" in lower_path or "league of legends" in lower_path:
        return "game_data"
    if "steamapps" in parts and "workshop" in parts:
        return "app_managed_steam_workshop"
    if lower_path.startswith(r"d:\downloads\app"):
        return "downloads_app_installer_bundle"
    if lower_path.startswith(r"d:\backup"):
        return "backup_or_export_asset"
    if "downloads" in parts:
        return "downloads_nested_file"
    return "unknown_user_file"


def policy_matches_path(policy: dict[str, Any], path: str | Path) -> bool:
    file_path = Path(path)
    lower_path = str(file_path).lower()
    target = str(policy.get("target") or "").lower()
    target_type = normalize_target_type(policy.get("target_type"))

    if target_type == "path_exact":
        return lower_path == target
    if target_type == "path_prefix":
        prefix = target.rstrip("\\/")
        return (
            lower_path == prefix
            or lower_path.startswith(prefix + "\\")
            or lower_path.startswith(prefix + "/")
        )
    if target_type == "path_contains":
        return target in lower_path
    if target_type == "file_extension":
        wanted = target if target.startswith(".") else f".{target}"
        return file_path.suffix.lower() == wanted
    if target_type == "context":
        return classify_path_context(file_path) == target
    return False


def get_matching_policies_for_path(
    path: str | Path,
    *,
    policy_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    matches = [
        policy for policy in get_active_policies(policy_file)
        if policy_matches_path(policy, path)
    ]
    return sorted(
        matches,
        key=lambda item: (
            DECISION_PRIORITY.get(item.get("decision"), 99),
            str(item.get("updated_at") or ""),
        ),
    )


def get_primary_policy_for_path(
    path: str | Path,
    *,
    policy_file: str | Path | None = None,
) -> dict[str, Any] | None:
    matches = get_matching_policies_for_path(path, policy_file=policy_file)
    return matches[0] if matches else None


def get_policy_for_recommendation(
    recommendation: dict[str, Any],
    *,
    policy_file: str | Path | None = None,
) -> dict[str, Any] | None:
    recommendation_id = str(recommendation.get("id") or "").strip()
    if not recommendation_id:
        return None

    matches = [
        policy for policy in get_active_policies(policy_file)
        if policy.get("target_type") == "recommendation"
        and str(policy.get("target") or "") == recommendation_id
    ]
    matches.sort(
        key=lambda item: (
            DECISION_PRIORITY.get(item.get("decision"), 99),
            str(item.get("updated_at") or ""),
        )
    )
    return matches[0] if matches else None


def get_attached_or_lookup_recommendation_policy(
    recommendation: dict[str, Any],
    *,
    policy_file: str | Path | None = None,
) -> dict[str, Any] | None:
    attached_decision = recommendation.get("action_policy_decision")
    if attached_decision:
        return {
            "fingerprint": recommendation.get("action_policy_id"),
            "decision": normalize_decision(attached_decision),
            "reason": recommendation.get("action_policy_reason") or "Policy attached to recommendation.",
            "target_type": "recommendation",
            "target": recommendation.get("id"),
            "source": "attached_recommendation",
            "active": True,
        }
    return get_policy_for_recommendation(recommendation, policy_file=policy_file)


def build_policy_gate(
    recommendation: dict[str, Any],
    *,
    capability: dict[str, Any] | None = None,
    policy_file: str | Path | None = None,
) -> dict[str, Any]:
    policy = get_attached_or_lookup_recommendation_policy(
        recommendation,
        policy_file=policy_file,
    )
    if policy is None:
        return {
            "status": "no_policy",
            "can_open_target": True,
            "requires_strong_confirmation": False,
            "confirmation_token": "OPEN",
            "decision": None,
            "reason": "No action policy matched this recommendation.",
            "policy": None,
            "warnings": [],
        }

    decision = normalize_decision(policy.get("decision"))
    target_tool_id = capability.get("id") if capability else recommendation.get("suggested_tool_id")
    target_mutates_files = bool(capability.get("mutates_files")) if capability else False

    if decision == "ignore_forever":
        return {
            "status": "policy_blocked",
            "can_open_target": False,
            "requires_strong_confirmation": False,
            "confirmation_token": None,
            "decision": decision,
            "reason": policy.get("reason") or "Action policy blocks this recommendation.",
            "policy": policy,
            "warnings": [
                "This recommendation is ignored by policy and should not open cleanup tools.",
            ],
            "target_tool_id": target_tool_id,
            "target_mutates_files": target_mutates_files,
        }

    if decision == "keep":
        return {
            "status": "policy_kept",
            "can_open_target": False,
            "requires_strong_confirmation": False,
            "confirmation_token": None,
            "decision": decision,
            "reason": policy.get("reason") or "Action policy says to keep this item.",
            "policy": policy,
            "warnings": [
                "This recommendation is marked keep; no action should be opened from the runner.",
            ],
            "target_tool_id": target_tool_id,
            "target_mutates_files": target_mutates_files,
        }

    if decision in POLICY_CONFIRMATION_TOKENS:
        warnings = {
            "manual_only": "Manual-only policy: review exact files before any cleanup.",
            "needs_backup": "Backup policy: confirm backup/keep decision before any destructive action.",
            "move_later": "Move-later policy: choose destination before moving files.",
            "delete_candidate": "Delete-candidate policy: requires exact file selection and final confirmation.",
        }
        return {
            "status": "policy_confirmation_required",
            "can_open_target": True,
            "requires_strong_confirmation": True,
            "confirmation_token": POLICY_CONFIRMATION_TOKENS[decision],
            "decision": decision,
            "reason": policy.get("reason") or warnings[decision],
            "policy": policy,
            "warnings": [warnings[decision]],
            "target_tool_id": target_tool_id,
            "target_mutates_files": target_mutates_files,
        }

    return {
        "status": "policy_allowed",
        "can_open_target": True,
        "requires_strong_confirmation": False,
        "confirmation_token": "OPEN",
        "decision": decision,
        "reason": policy.get("reason") or "Action policy allows opening the suggested tool.",
        "policy": policy,
        "warnings": [],
        "target_tool_id": target_tool_id,
        "target_mutates_files": target_mutates_files,
    }


def get_latest_report_by_tool(tool_name: str, *, limit: int = 500) -> dict[str, Any] | None:
    records = read_recent_report_index(limit=limit)
    for record in reversed(records):
        if record.get("tool") == tool_name:
            return record
    return None


def safe_read_report(path: str | Path) -> dict[str, Any] | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        with report_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_default_policies() -> list[dict[str, Any]]:
    return [
        make_policy(
            target_type="path_contains",
            target="Riot Games",
            decision="ignore_forever",
            reason="User marked Riot Games as game data; assistant must not delete or move it automatically.",
            source="step4_baseline",
            context="game_data",
            tags=["game", "protected_by_user"],
        ),
        make_policy(
            target_type="path_contains",
            target="League of Legends",
            decision="ignore_forever",
            reason="League of Legends files are game data and should stay outside cleanup automation.",
            source="step4_baseline",
            context="game_data",
            tags=["game", "protected_by_user"],
        ),
        make_policy(
            target_type="path_prefix",
            target=r"D:\Steam\steamapps\workshop",
            decision="ignore_forever",
            reason="Steam Workshop content is app-managed; moving/deleting can break subscriptions.",
            source="step4_baseline",
            context="app_managed_steam_workshop",
            tags=["steam", "app_managed"],
        ),
        make_policy(
            target_type="path_prefix",
            target=r"D:\Downloads\app",
            decision="manual_only",
            reason="Downloads app installer bundles require user choice before keep/move/delete.",
            source="step4_baseline",
            context="downloads_app_installer_bundle",
            tags=["downloads", "installer", "manual"],
        ),
        make_policy(
            target_type="path_prefix",
            target=r"D:\backup",
            decision="needs_backup",
            reason="Backup/export assets should not be deleted until user confirms backup/keep policy.",
            source="step4_baseline",
            context="backup_or_export_asset",
            tags=["backup", "manual"],
        ),
        make_policy(
            target_type="recommendation",
            target="large-archive-files",
            decision="manual_only",
            reason="Large archive/installers include Premiere and backup assets; user must choose individual files.",
            source="step4_baseline",
            recommendation_id="large-archive-files",
            tags=["recommendation", "archives"],
        ),
        make_policy(
            target_type="recommendation",
            target="large-video-files",
            decision="move_later",
            reason="Large videos may be moved only after user selects destination and keep policy.",
            source="step4_baseline",
            recommendation_id="large-video-files",
            tags=["recommendation", "video"],
        ),
        make_policy(
            target_type="context",
            target="downloads_app_installer_bundle",
            decision="manual_only",
            reason="Installer bundle context stays manual-only.",
            source="step4_baseline",
            tags=["context", "installer"],
        ),
        make_policy(
            target_type="context",
            target="backup_or_export_asset",
            decision="needs_backup",
            reason="Backup/export context requires backup/keep decision.",
            source="step4_baseline",
            tags=["context", "backup"],
        ),
        make_policy(
            target_type="context",
            target="app_managed_steam_workshop",
            decision="ignore_forever",
            reason="App-managed Steam Workshop context is ignored by assistant cleanup.",
            source="step4_baseline",
            tags=["context", "steam"],
        ),
        make_policy(
            target_type="context",
            target="game_data",
            decision="ignore_forever",
            reason="Game data context is ignored by assistant cleanup unless user explicitly changes policy.",
            source="step4_baseline",
            tags=["context", "game"],
        ),
    ]


def seed_default_action_policies(policy_file: str | Path | None = None) -> dict[str, Any]:
    existing = {
        item["fingerprint"]: item
        for item in get_active_policies(policy_file)
    }
    created = []
    unchanged = []

    for policy in build_default_policies():
        if policy["fingerprint"] in existing:
            unchanged.append(existing[policy["fingerprint"]])
            continue
        created.append(append_policy_event(policy, policy_file=policy_file))

    return {
        "status": "success",
        "policy_file": str(get_policy_file(policy_file)),
        "created_count": len(created),
        "unchanged_count": len(unchanged),
        "created": created,
    }


def summarize_action_policies(policy_file: str | Path | None = None) -> dict[str, Any]:
    policies = get_active_policies(policy_file)
    summary = {
        "total": len(policies),
        "by_decision": {decision: 0 for decision in sorted(VALID_DECISIONS)},
        "by_target_type": {target_type: 0 for target_type in sorted(VALID_TARGET_TYPES)},
        "ignore_forever_count": 0,
        "manual_only_count": 0,
        "delete_candidate_count": 0,
    }

    for policy in policies:
        decision = normalize_decision(policy.get("decision"))
        target_type = normalize_target_type(policy.get("target_type"))
        summary["by_decision"][decision] += 1
        summary["by_target_type"][target_type] += 1
        if decision == "ignore_forever":
            summary["ignore_forever_count"] += 1
        elif decision == "manual_only":
            summary["manual_only_count"] += 1
        elif decision == "delete_candidate":
            summary["delete_candidate_count"] += 1

    return summary


def validate_action_policies(policy_file: str | Path | None = None) -> dict[str, Any]:
    issues = []
    policies = get_active_policies(policy_file)

    for policy in policies:
        if normalize_target_type(policy.get("target_type"), default="") not in VALID_TARGET_TYPES:
            issues.append(f"Invalid target_type: {policy}")
        if normalize_decision(policy.get("decision"), default="") not in VALID_DECISIONS:
            issues.append(f"Invalid decision: {policy}")
        if not str(policy.get("target") or "").strip():
            issues.append(f"Missing target: {policy}")

    required_matches = {
        "riot_games": any(
            item["target_type"] == "path_contains"
            and "riot games" in str(item["target"]).lower()
            and item["decision"] == "ignore_forever"
            for item in policies
        ),
        "steam_workshop": any(
            item["target_type"] == "path_prefix"
            and "steamapps\\workshop" in str(item["target"]).lower()
            and item["decision"] == "ignore_forever"
            for item in policies
        ),
        "downloads_app": any(
            item["target_type"] == "path_prefix"
            and str(item["target"]).lower().startswith(r"d:\downloads\app")
            and item["decision"] == "manual_only"
            for item in policies
        ),
        "backup": any(
            item["target_type"] == "path_prefix"
            and str(item["target"]).lower().startswith(r"d:\backup")
            and item["decision"] == "needs_backup"
            for item in policies
        ),
        "large_archive_recommendation": any(
            item["target_type"] == "recommendation"
            and item["target"] == "large-archive-files"
            for item in policies
        ),
        "large_video_recommendation": any(
            item["target_type"] == "recommendation"
            and item["target"] == "large-video-files"
            for item in policies
        ),
    }
    missing_required = [
        name for name, exists in required_matches.items()
        if not exists
    ]
    if missing_required:
        issues.append(f"Missing required baseline policies: {missing_required}")

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
        "policy_count": len(policies),
        "required_matches": required_matches,
        "policy_file": str(get_policy_file(policy_file)),
    }


def build_step3_policy_coverage(policy_file: str | Path | None = None) -> dict[str, Any]:
    latest = get_latest_report_by_tool("step3_deferred_storage_review")
    if latest is None:
        return {
            "status": "missing_step3_report",
            "covered_count": 0,
            "uncovered_count": 0,
            "items": [],
        }

    report_data = safe_read_report(str(latest.get("report_path") or ""))
    if report_data is None:
        return {
            "status": "invalid_step3_report",
            "report": latest.get("report_path"),
            "covered_count": 0,
            "uncovered_count": 0,
            "items": [],
        }

    results = report_data.get("results", {})
    archive_items = (
        results.get("archive_review", {}).get("items", [])
        if isinstance(results, dict) else []
    )
    video_items = (
        results.get("video_review", {}).get("items", [])
        if isinstance(results, dict) else []
    )
    records = []

    for item in [*archive_items, *video_items]:
        path = item.get("path")
        if not path:
            continue
        policy = get_primary_policy_for_path(path, policy_file=policy_file)
        records.append({
            "path": path,
            "context": classify_path_context(path),
            "covered": policy is not None,
            "decision": policy.get("decision") if policy else None,
            "policy_id": policy.get("fingerprint") if policy else None,
            "policy_reason": policy.get("reason") if policy else None,
        })

    covered_count = sum(1 for item in records if item["covered"])
    return {
        "status": "success",
        "source_report": latest.get("report_path"),
        "covered_count": covered_count,
        "uncovered_count": len(records) - covered_count,
        "items": records,
    }


def build_action_policy_health(policy_file: str | Path | None = None) -> dict[str, Any]:
    return {
        "schema": "action_policy_v1",
        "policy_file": str(get_policy_file(policy_file)),
        "summary": summarize_action_policies(policy_file),
        "validation": validate_action_policies(policy_file),
        "step3_coverage": build_step3_policy_coverage(policy_file),
    }


def export_action_policy_report(policy_file: str | Path | None = None) -> dict[str, Any]:
    health = build_action_policy_health(policy_file)
    validation = health["validation"]
    status = "success" if validation["status"] == "valid" else "warning"
    summary = health["summary"]

    report = create_report(
        tool_name="action_policy",
        action="export_policy",
        status=status,
        risk_level="safe",
        input_data={
            "policy_file": health["policy_file"],
        },
        results={
            "health": health,
            "policies": get_active_policies(policy_file),
        },
        recommendations=[
            "Policy decisions are read-only guidance and do not execute cleanup.",
            "Keep game data and app-managed folders ignored unless user changes policy explicitly.",
            "Use delete_candidate only after user selects exact files.",
        ],
        summary={
            "policy_count": summary["total"],
            "ignore_forever_count": summary["ignore_forever_count"],
            "manual_only_count": summary["manual_only_count"],
            "delete_candidate_count": summary["delete_candidate_count"],
            "validation_status": validation["status"],
            "step3_uncovered_count": health["step3_coverage"]["uncovered_count"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["action_policy", "read_only", "decision_layer"],
    )

    log_action(
        "action_policy",
        "export_action_policy_report",
        status,
        {
            "report": str(report),
            "policy_count": summary["total"],
            "validation_status": validation["status"],
        },
    )

    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "health": health,
    }


def print_policy_table(policies: list[dict[str, Any]]) -> None:
    if not policies:
        print("Chua co action policy.")
        return

    print("\n========== ACTION POLICIES ==========")
    for index, policy in enumerate(policies, start=1):
        print(
            f"{index:>2}. {policy['decision']:<15} | "
            f"{policy['target_type']:<12} | {policy['target']}"
        )
        print(f"    Reason: {policy.get('reason')}")
        print(f"    ID: {policy.get('fingerprint')}")


def add_manual_policy_from_input() -> dict[str, Any] | None:
    print("Target type: path_exact, path_prefix, path_contains, context, recommendation, file_extension")
    target_type = normalize_target_type(input("Nhap target_type: ").strip(), default="")
    if not target_type:
        print("Target type khong hop le.")
        return None

    print("Decision: keep, move_later, delete_candidate, ignore_forever, needs_backup, manual_only")
    decision = normalize_decision(input("Nhap decision: ").strip(), default="")
    if not decision:
        print("Decision khong hop le.")
        return None

    target = input("Nhap target/pattern/recommendation id: ").strip()
    if not target:
        print("Target khong duoc rong.")
        return None

    reason = input("Nhap ly do ngan: ").strip() or "Manual policy."
    policy = make_policy(
        target_type=target_type,
        target=target,
        decision=decision,
        reason=reason,
        source="manual",
        tags=["manual"],
    )
    saved = append_policy_event(policy)
    log_action(
        "action_policy",
        "add_manual_policy",
        "success",
        {
            "policy_id": saved["fingerprint"],
            "target_type": saved["target_type"],
            "decision": saved["decision"],
        },
    )
    print(f"Da them policy: {saved['fingerprint']}")
    return saved


def run_action_policy_manager() -> None:
    while True:
        print("""
========== ACTION POLICY MANAGER ==========
1. Xem summary policy
2. List active policy
3. Seed baseline policy Step 4
4. Them manual policy
5. Xuat action policy report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print(build_action_policy_health())

        elif choice == "2":
            print_policy_table(get_active_policies())

        elif choice == "3":
            result = seed_default_action_policies()
            print(result)

        elif choice == "4":
            add_manual_policy_from_input()

        elif choice == "5":
            export_action_policy_report()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_action_policy_manager()
