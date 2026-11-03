#!/usr/bin/env python3
"""
conventions.yaml 기준으로 FastAPI 도메인 파일의 컨벤션을 검증합니다.
PostToolUse Write 훅에서 자동 실행됩니다.

Usage: python scripts/validate_conventions.py <file_path>
"""

import ast
import re
import sys
from pathlib import Path


def load_conventions():
    try:
        import yaml
    except ImportError:
        return None

    conventions_path = Path(__file__).parent.parent / ".claude/skills/new-domain/conventions.yaml"
    if not conventions_path.exists():
        return None

    with open(conventions_path) as f:
        return yaml.safe_load(f)


def detect_file_type(path: Path) -> str:
    """파일 경로에서 도메인 파일 타입 감지."""
    name = path.name
    parts = path.parts

    # src/domains/{domain}/ 하위 파일인지 확인
    if "domains" not in parts:
        return "unknown"

    if name == "router.py":
        return "router"
    if name == "service.py":
        return "service"
    if name == "models.py":
        return "models"
    if name == "schemas.py":
        return "schemas"
    return "unknown"


def extract_domain_from_path(path: Path) -> str:
    """경로에서 도메인명 추출."""
    parts = path.parts
    try:
        idx = parts.index("domains")
        return parts[idx + 1] if idx + 1 < len(parts) else ""
    except ValueError:
        return ""


def parse_python_file(file_path: Path):
    """Python 파일을 AST로 파싱."""
    try:
        source = file_path.read_text(encoding="utf-8")
        return ast.parse(source), source
    except (SyntaxError, UnicodeDecodeError):
        return None, None


def check_router(tree, source: str, domain: str, conventions: dict) -> list[str]:
    """router.py 컨벤션 검증."""
    issues = []

    # 함수명 패턴: {domain}_{action}
    expected_prefix = domain + "_"
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        fname = node.name
        # 내부 헬퍼 함수 제외 (get_current_user 등)
        if fname.startswith("get_current") or fname.startswith("_"):
            continue
        if not fname.startswith(expected_prefix):
            issues.append(
                f"  [router] 함수명 '{fname}'은 '{expected_prefix}{{action}}' 패턴이어야 합니다"
            )

    # prefix 확인
    if f'prefix="/api/{domain}"' not in source and f"prefix='/api/{domain}'" not in source:
        issues.append(f"  [router] APIRouter prefix가 '/api/{domain}'이어야 합니다")

    # 인증 필요 엔드포인트에 get_current_user 확인
    auth_actions = ["create", "update", "delete", "vote"]
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        fname = node.name
        action = fname.replace(expected_prefix, "", 1)
        if action in auth_actions:
            func_src = ast.get_source_segment(source, node) or ""
            if "get_current_user_with_async" not in func_src:
                issues.append(
                    f"  [router] '{fname}' 엔드포인트에 인증 의존성(get_current_user_with_async)이 없습니다"
                )

    return issues


def check_service(tree, source: str, domain: str, conventions: dict) -> list[str]:
    """service.py 컨벤션 검증."""
    issues = []

    crud_actions = ["get", "create", "update", "delete", "vote"]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        fname = node.name
        if fname.startswith("_"):
            continue
        # 서비스 함수명: {action}_{domain} 패턴
        has_valid_pattern = any(
            fname.startswith(f"{action}_{domain}") for action in crud_actions
        )
        # list 함수는 get_{domain}_list
        if not has_valid_pattern and not fname.startswith(f"get_{domain}"):
            issues.append(
                f"  [service] 함수명 '{fname}'은 '{{action}}_{domain}' 패턴이어야 합니다"
            )

    return issues


def check_models(tree, source: str, domain: str, conventions: dict) -> list[str]:
    """models.py 컨벤션 검증."""
    issues = []
    domain_class = domain.capitalize()
    required_fields = {"id", "create_date", "modify_date", "user_id"}
    found_fields = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name != domain_class:
            continue

        # __tablename__ 소문자 확인
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            tname = item.value.value
                            if tname != tname.lower():
                                issues.append(
                                    f"  [models] __tablename__ '{tname}'은 소문자여야 합니다"
                                )
                    # 필드 존재 확인
                    if isinstance(target, ast.Name) and target.id in required_fields:
                        found_fields.add(target.id)

        missing = required_fields - found_fields
        if missing:
            issues.append(
                f"  [models] 필수 필드 누락: {', '.join(sorted(missing))}"
            )

    return issues


def check_schemas(tree, source: str, domain: str, conventions: dict) -> list[str]:
    """schemas.py 컨벤션 검증."""
    issues = []
    domain_cap = domain.capitalize()
    expected_schemas = {
        domain_cap,
        f"{domain_cap}List",
        f"{domain_cap}Create",
        f"{domain_cap}Update",
        f"{domain_cap}Delete",
    }

    defined_classes = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }

    # BaseModel 상속 여부 간략 확인
    missing = expected_schemas - defined_classes
    if missing:
        issues.append(
            f"  [schemas] 다음 스키마 클래스가 없습니다: {', '.join(sorted(missing))}"
        )

    return issues


def validate_file(file_path_str: str):
    file_path = Path(file_path_str).resolve()

    if not file_path.exists() or not file_path.suffix == ".py":
        return  # .py 파일이 아니면 스킵

    conventions = load_conventions()

    file_type = detect_file_type(file_path)
    if file_type == "unknown":
        return  # 도메인 파일이 아님

    domain = extract_domain_from_path(file_path)
    if not domain:
        return

    tree, source = parse_python_file(file_path)
    if tree is None:
        return

    checker_map = {
        "router": check_router,
        "service": check_service,
        "models": check_models,
        "schemas": check_schemas,
    }

    checker = checker_map.get(file_type)
    if not checker:
        return

    issues = checker(tree, source, domain, conventions or {})

    if issues:
        print(f"\n⚠️  컨벤션 검사 결과: {file_path.name} ({domain} 도메인)")
        for issue in issues:
            print(issue)
        print()
    else:
        print(f"✅ 컨벤션 검사 통과: {file_path.name} ({domain} 도메인)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_conventions.py <file_path>")
        sys.exit(1)

    validate_file(sys.argv[1])
