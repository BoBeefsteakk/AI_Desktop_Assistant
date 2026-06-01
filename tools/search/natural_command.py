from __future__ import annotations

import importlib
import re
import unicodedata
from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.capability_registry import get_capabilities, summarize_capabilities
from tools.core import guided_action_runner, recommendation_center
from tools.search.file_indexer import search_files, show_search_results


EXIT_COMMANDS = {"0", "exit", "quit", "out", "thoat"}
HELP_COMMANDS = {"help", "?", "huong dan", "commands", "lenh"}
SEARCH_PREFIXES = {"find", "search", "tim", "locate"}
RECOMMENDATION_VISIBLE_STATES = recommendation_center.DEFAULT_VISIBLE_STATES

SKIP_ROUTE_IDS = {
    "natural_command",
    "file_location_opener",
}

INTENT_ALIASES: list[tuple[str, list[str]]] = [
    ("disk_checker", ["disk", "check disk", "o cung", "kiem tra o cung", "smart", "suc khoe o"]),
    ("process_monitor", ["ram", "cpu", "process", "process monitor", "tien trinh", "task"]),
    ("recycle_bin_cleaner", ["recycle", "recycle bin", "thung rac", "don thung rac", "empty recycle"]),
    ("junk_file_cleaner", ["junk", "file rac", "don file rac", "rac he thong"]),
    ("temp_cleaner", ["temp", "temporary", "don temp", "clean temp"]),
    ("duplicate_finder", ["duplicate", "trung lap", "file trung", "file duplicate"]),
    ("media_organizer", ["media", "gom media", "organize media", "video", "audio", "photo media"]),
    ("empty_folder_finder", ["empty folder", "folder rong", "thu muc rong"]),
    ("file_indexer", ["index", "file index", "indexer", "lap chi muc"]),
    ("startup_launcher", ["startup", "launcher", "mo app", "open app", "profile app"]),
    ("download_organizer", ["download organizer", "organize download", "sap xep download", "don download"]),
    ("download_watcher", ["download watcher", "watch download", "theo doi download"]),
    ("browser_cache_cleaner", ["cache", "browser cache", "cache trinh duyet", "don cache", "browser"]),
    ("game_booster", ["game", "booster", "game booster"]),
    ("folder_size_analyzer", ["folder size", "size folder", "folder nang", "thu muc nang"]),
    ("large_file_finder", ["large file", "file lon", "file nang", "tim file lon"]),
    ("system_advisor", ["advisor", "system advisor", "goi y", "phan tich tong quan"]),
    ("assistant_logger", ["log", "logs", "assistant log", "lich su"]),
    ("audit_center", ["audit", "audit center", "report index", "bao cao"]),
    ("behavior_tester", ["behavior test", "test behavior", "test hanh vi"]),
    ("config_manager", ["config", "settings", "cau hinh"]),
    ("undo_manager", ["undo", "restore", "khoi phuc", "manifest"]),
    ("full_system_tester", ["full test", "full system test", "test tong", "test all", "test sieu tong"]),
    ("wiztree_adapter", ["wiztree", "wiztree scan"]),
    ("external_apps_manager", ["external app", "external apps", "app ngoai", "apps manager"]),
    ("capability_registry", ["capability", "registry", "capability registry", "nang luc"]),
    ("recommendation_center", ["recommendation", "recommendations", "queue", "hang doi goi y", "goi y tiep theo"]),
    ("guided_action_runner", ["guided action", "guided runner", "lam goi y", "mo goi y", "chay goi y", "xu ly goi y"]),
]


def normalize_command(command: str) -> str:
    decomposed = unicodedata.normalize("NFD", command.lower().strip())
    without_accents = "".join(
        char for char in decomposed
        if unicodedata.category(char) != "Mn"
    )
    normalized_chars = [
        char if char.isalnum() else " "
        for char in without_accents
    ]
    return " ".join("".join(normalized_chars).split())


def _contains_phrase(normalized_command: str, phrase: str) -> bool:
    command_words = normalized_command.split()
    phrase_words = normalize_command(phrase).split()

    if not phrase_words or len(phrase_words) > len(command_words):
        return False

    for index in range(0, len(command_words) - len(phrase_words) + 1):
        if command_words[index:index + len(phrase_words)] == phrase_words:
            return True

    return False


def get_command_routes() -> list[dict[str, Any]]:
    capabilities = {
        capability["id"]: capability
        for capability in get_capabilities()
        if capability["id"] not in SKIP_ROUTE_IDS
    }

    routes = []
    for capability_id, aliases in INTENT_ALIASES:
        capability = capabilities.get(capability_id)
        if capability is None:
            continue

        phrases = sorted(
            set([*aliases, capability["name"], *capability["tags"]]),
            key=lambda item: (-len(normalize_command(item).split()), item),
        )
        routes.append({
            "capability": capability,
            "phrases": phrases,
        })

    return routes


def extract_search_query(command: str) -> str | None:
    parts = command.strip().split(maxsplit=1)
    if not parts:
        return None

    first_word = normalize_command(parts[0])
    if first_word not in SEARCH_PREFIXES:
        return None

    if len(parts) == 1:
        return ""

    return parts[1].strip()


def extract_command_index(normalized_command: str) -> int | None:
    numbers = re.findall(r"\d+", normalized_command)
    if not numbers:
        return None
    return int(numbers[-1])


def has_recommendation_subject(normalized_command: str) -> bool:
    return any(
        _contains_phrase(normalized_command, phrase)
        for phrase in {
            "goi y",
            "recommendation",
            "queue",
            "hang doi",
            "muc",
        }
    )


def resolve_recommendation_queue_command(command: str) -> dict[str, Any] | None:
    normalized = normalize_command(command)
    if not has_recommendation_subject(normalized):
        return None

    if any(
        _contains_phrase(normalized, phrase)
        for phrase in {
            "xem goi y",
            "goi y tiep theo",
            "xem queue",
            "xem hang doi",
            "danh sach goi y",
            "list goi y",
        }
    ):
        return {
            "type": "recommendation_queue_preview",
            "states": RECOMMENDATION_VISIBLE_STATES,
        }

    index = extract_command_index(normalized)
    if index is None:
        return None

    state_phrases = {
        "handled": {"da xu ly", "danh dau da xu ly", "mark handled", "handled", "xong"},
        "deferred": {"hoan", "tam hoan", "defer", "deferred", "doi sau"},
        "ignored": {"bo qua", "ignore", "ignored"},
        "pending": {"pending", "mo lai", "dua ve pending", "cho xu ly"},
    }
    for state, phrases in state_phrases.items():
        if any(_contains_phrase(normalized, phrase) for phrase in phrases):
            return {
                "type": "recommendation_state_update",
                "index": index,
                "state": state,
            }

    if any(
        _contains_phrase(normalized, phrase)
        for phrase in {
            "lam",
            "mo",
            "chay",
            "xu ly",
            "run",
            "open",
        }
    ):
        return {
            "type": "recommendation_open",
            "index": index,
        }

    return None


def resolve_command(command: str) -> dict[str, Any]:
    normalized = normalize_command(command)

    if not normalized:
        return {"type": "empty"}

    if normalized in EXIT_COMMANDS:
        return {"type": "exit"}

    if normalized in HELP_COMMANDS:
        return {"type": "help"}

    search_query = extract_search_query(command)
    if search_query is not None:
        return {
            "type": "search",
            "query": search_query,
        }

    recommendation_decision = resolve_recommendation_queue_command(command)
    if recommendation_decision is not None:
        return recommendation_decision

    best_match: dict[str, Any] | None = None
    for route in get_command_routes():
        for phrase in route["phrases"]:
            if not _contains_phrase(normalized, phrase):
                continue

            phrase_words = normalize_command(phrase).split()
            score = len(phrase_words) * 10
            if normalize_command(phrase) == normalized:
                score += 5

            if best_match is None or score > best_match["score"]:
                best_match = {
                    "type": "capability",
                    "capability": route["capability"],
                    "matched_phrase": phrase,
                    "score": score,
                }

    if best_match is not None:
        return best_match

    return {
        "type": "unknown",
        "normalized": normalized,
    }


def requires_confirmation(capability: dict[str, Any]) -> bool:
    return (
        capability["risk_level"] != "safe"
        or bool(capability["mutates_files"])
        or bool(capability["needs_confirmation"])
    )


def confirm_capability_run(capability: dict[str, Any]) -> bool:
    if not requires_confirmation(capability):
        return True

    print("\nLenh nay se mo tool co rui ro hoac co the thay doi file:")
    print(f"- Tool: {capability['name']}")
    print(f"- Risk: {capability['risk_level']}")
    print(f"- Mutates files: {capability['mutates_files']}")
    print(f"- Undo: {capability['undo_strategy']}")
    print(f"- Summary: {capability['summary']}")
    answer = input("Nhap y de tiep tuc, phim khac de huy: ").strip()
    return normalize_command(answer) in {"y", "yes", "ok", "run", "chay", "tiep tuc"}


def execute_capability(capability: dict[str, Any]) -> None:
    module = importlib.import_module(capability["module"])
    function = getattr(module, capability["function"])
    print(f"\nDang chay: {capability['name']}")
    function()


def run_search_command(query: str) -> None:
    if not query:
        print("Can nhap tu khoa. VD: find naruto")
        return

    search_result = search_files(query)
    print(f"Source: {search_result['source']}")
    show_search_results(search_result["results"])


def get_recommendation_context_by_index(
    index: int,
    *,
    report_limit: int = 80,
    state_file: str | Path | None = None,
    include_test_reports: bool = False,
    states: set[str] | list[str] | tuple[str, ...] | None = RECOMMENDATION_VISIBLE_STATES,
) -> dict[str, Any]:
    preview = guided_action_runner.preview_guided_actions(
        report_limit=report_limit,
        state_file=state_file,
        include_test_reports=include_test_reports,
        states=states,
    )
    contexts = preview["contexts"]
    if index < 1 or index > len(contexts):
        return {
            "status": "invalid_index",
            "index": index,
            "context_count": len(contexts),
            "preview": preview,
            "context": None,
        }

    return {
        "status": "ready",
        "index": index,
        "context_count": len(contexts),
        "preview": preview,
        "context": contexts[index - 1],
    }


def run_recommendation_queue_preview(
    *,
    report_limit: int = 80,
    state_file: str | Path | None = None,
    include_test_reports: bool = False,
) -> dict[str, Any]:
    preview = guided_action_runner.preview_guided_actions(
        report_limit=report_limit,
        state_file=state_file,
        include_test_reports=include_test_reports,
        states=RECOMMENDATION_VISIBLE_STATES,
    )
    print(f"Ready actions: {preview['ready_count']}")
    print(f"Blocked actions: {preview['blocked_count']}")
    print(f"State file: {preview['sync_result']['state_file']}")
    guided_action_runner.print_guided_actions(preview["contexts"])
    return preview


def run_recommendation_state_command(
    index: int,
    state: str,
    *,
    report_limit: int = 80,
    state_file: str | Path | None = None,
    include_test_reports: bool = False,
) -> dict[str, Any]:
    lookup = get_recommendation_context_by_index(
        index,
        report_limit=report_limit,
        state_file=state_file,
        include_test_reports=include_test_reports,
    )
    if lookup["status"] != "ready":
        print(f"Khong tim thay recommendation so {index}.")
        return {
            "status": "invalid_index",
            "index": index,
            "context_count": lookup["context_count"],
        }

    context = lookup["context"]
    recommendation = context["recommendation"]
    event = recommendation_center.update_recommendation_state(
        recommendation["fingerprint"],
        state,
        note="Updated from Natural Command v3.",
        state_file=state_file,
    )
    log_action(
        "natural_command",
        "recommendation_state_update",
        "success",
        {
            "index": index,
            "state": state,
            "fingerprint": recommendation["fingerprint"],
            "recommendation_id": recommendation.get("id"),
        },
    )
    print(f"Da cap nhat recommendation {index} -> {state}.")
    return {
        "status": "success",
        "state": state,
        "event": event,
        "recommendation": recommendation,
    }


def run_recommendation_open_command(
    index: int,
    *,
    report_limit: int = 80,
    state_file: str | Path | None = None,
    include_test_reports: bool = False,
    dry_run: bool = False,
    require_confirmation: bool = True,
) -> dict[str, Any]:
    lookup = get_recommendation_context_by_index(
        index,
        report_limit=report_limit,
        state_file=state_file,
        include_test_reports=include_test_reports,
    )
    if lookup["status"] != "ready":
        print(f"Khong tim thay recommendation so {index}.")
        return {
            "status": "invalid_index",
            "executed": False,
            "index": index,
            "context_count": lookup["context_count"],
        }

    context = lookup["context"]
    if require_confirmation and not guided_action_runner.confirm_guided_action(context):
        print("Da huy.")
        return {
            "status": "cancelled",
            "executed": False,
            "index": index,
        }

    result = guided_action_runner.execute_guided_action(context, dry_run=dry_run)
    print(f"Guided action status: {result['status']}")
    if result.get("report"):
        print(f"Report: {result['report']}")
    return result


def print_help() -> None:
    summary = summarize_capabilities()
    print("\n========== NATURAL COMMAND V3 ==========")
    print("VD lenh:")
    print("- check disk")
    print("- ram")
    print("- don cache")
    print("- duplicate")
    print("- folder size")
    print("- find ten_file")
    print("- test tong")
    print("- capability")
    print("- xem goi y")
    print("- lam goi y so 1")
    print("- hoan muc 2")
    print("- danh dau muc 3 da xu ly")
    print("- lam goi y")
    print(f"\nDang co {summary['total']} capability trong registry.")
    print("Tool co risk medium/dangerous hoac co the thay doi file se hoi xac nhan truoc.")


def handle_command(command: str) -> bool:
    decision = resolve_command(command)

    if decision["type"] == "exit":
        return False

    if decision["type"] == "empty":
        return True

    if decision["type"] == "help":
        print_help()
        return True

    if decision["type"] == "search":
        run_search_command(decision["query"])
        return True

    if decision["type"] == "recommendation_queue_preview":
        run_recommendation_queue_preview()
        return True

    if decision["type"] == "recommendation_state_update":
        run_recommendation_state_command(decision["index"], decision["state"])
        return True

    if decision["type"] == "recommendation_open":
        run_recommendation_open_command(decision["index"])
        return True

    if decision["type"] == "capability":
        capability = decision["capability"]
        print(
            f"Matched: {capability['name']} "
            f"(risk={capability['risk_level']}, undo={capability['undo_strategy']})"
        )
        if confirm_capability_run(capability):
            execute_capability(capability)
        else:
            print("Da huy lenh.")
        return True

    print("Chua hieu lenh. Go 'help' de xem vi du.")
    return True


def run_natural_command() -> None:
    print("Nhap lenh tu nhien. Go 'help' de xem vi du, 'exit' de thoat.")
    while True:
        command = input("\nAssistant> ")
        if not handle_command(command):
            break


if __name__ == "__main__":
    run_natural_command()
