#!/usr/bin/env python
"""quizctl: a headless client for the quiz API. No screen, no browser, no clicks.

A program that another program can call must say what happened in a way a machine can read:
the EXIT CODE (did it work? why not?) and, with --json, a stable output.

    python quizctl.py exams list
    python quizctl.py questions list --exam 1 --search orm --json
    python quizctl.py questions create --exam 1 --text "¿Qué es REST?" --choice "Un estilo:ok" --choice "Un lenguaje"
    python quizctl.py questions create --exam 1 --text "..." --choice "a:ok" --choice "b" --dry-run
    python quizctl.py questions delete 7
    python quizctl.py ops                      # lists the operations the API's contract declares

Environment:  QUIZ_URL (default http://127.0.0.1:8000)  and  QUIZ_TOKEN (the token to use).

Exit codes:
    0 ok   1 other / usage   2 validation (400)   3 not allowed (401, 403)
    4 not found (404)   5 server error (5xx)   6 no connection

The command-line client keeps its HTTP status handling and request payloads in one place.
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import requests

EXIT_OK, EXIT_OTHER, EXIT_VALIDATION, EXIT_FORBIDDEN, EXIT_NOT_FOUND, EXIT_SERVER, EXIT_NETWORK = range(7)


@dataclass
class Result:
    status: int | None  # HTTP status; None = nothing sent (dry-run); 0 = no connection; -1 = usage error
    data: Any = None
    request: dict = field(default_factory=dict)
    error: str = ""


def exit_code_for(status: int) -> int:
    """Map an HTTP status to the exit code of the table above.

    2xx -> 0 · 400 -> 2 · 401 and 403 -> 3 · 404 -> 4 · 5xx -> 5 · any other status -> 1.
    """
    if 200 <= status < 300:
        return EXIT_OK
    if status == 400:
        return EXIT_VALIDATION
    if status in (401, 403):
        return EXIT_FORBIDDEN
    if status == 404:
        return EXIT_NOT_FOUND
    if 500 <= status < 600:
        return EXIT_SERVER
    return EXIT_OTHER


def build_question_payload(exam_id: int, text: str, choices: list[str]) -> dict:
    """Build the JSON body of POST /api/questions/ from the command line.

    `choices` are strings; one that ends in ':ok' is the correct one:
        ["Un estilo:ok", "Un lenguaje"]  ->
        {"exam": exam_id, "text": text,
         "choices": [{"text": "Un estilo", "is_correct": True},
                     {"text": "Un lenguaje", "is_correct": False}]}
    Do NOT validate here (how many choices, how many correct): that is the server's job,
    and the server answers 400 with the reason.
    """
    serialized_choices = []
    for choice in choices:
        is_correct = choice.endswith(":ok")
        serialized_choices.append({
            "text": choice[:-3] if is_correct else choice,
            "is_correct": is_correct,
        })
    return {"exam": exam_id, "text": text, "choices": serialized_choices}


# --- the rest of the client (already written) -------------------------------------------------


def call(method: str, path: str, env, *, params=None, body=None, dry_run=False) -> Result:
    base = env.get("QUIZ_URL", "http://127.0.0.1:8000").rstrip("/")
    token = env.get("QUIZ_TOKEN")
    if not token:  # a usage error, not a network one: nothing was tried
        return Result(status=-1, error="Falta QUIZ_TOKEN (el token con el que se llama a la API).")
    request = {"method": method, "url": base + path, "params": params or None, "json": body}
    if dry_run and method != "GET":
        return Result(status=None, request=request)  # writes are described, not sent
    try:
        response = requests.request(
            method, base + path, params=params, json=body, timeout=10,
            headers={"Authorization": f"Token {token}", "Accept": "application/json"},
        )
    except requests.RequestException as exc:
        return Result(status=0, request=request, error=str(exc))
    try:
        data = response.json() if response.content else None
    except ValueError:
        data = response.text
    return Result(status=response.status_code, data=data, request=request)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quizctl", description="Cliente de consola de la API de cuestionarios")
    parser.add_argument("--json", action="store_true", help="salida JSON estable, para otros programas")
    parser.add_argument("--dry-run", action="store_true", help="en escrituras, muestra la petición sin enviarla")
    sub = parser.add_subparsers(dest="resource", required=True)

    exams = sub.add_parser("exams").add_subparsers(dest="action", required=True)
    exams.add_parser("list")
    exams.add_parser("get").add_argument("id", type=int)

    questions = sub.add_parser("questions").add_subparsers(dest="action", required=True)
    listing = questions.add_parser("list")
    listing.add_argument("--exam", type=int)
    listing.add_argument("--search")
    listing.add_argument("--page", type=int)
    questions.add_parser("get").add_argument("id", type=int)
    create = questions.add_parser("create")
    create.add_argument("--exam", type=int, required=True)
    create.add_argument("--text", required=True)
    create.add_argument("--choice", action="append", default=[], help="texto de la opción; «:ok» marca la correcta")
    questions.add_parser("delete").add_argument("id", type=int)

    sub.add_parser("ops")
    return parser


def dispatch(args, env) -> Result:
    dry = args.dry_run
    if args.resource == "exams":
        if args.action == "list":
            return call("GET", "/api/exams/", env)
        return call("GET", f"/api/exams/{args.id}/", env)
    if args.resource == "questions":
        if args.action == "list":
            params = {k: v for k, v in (("exam", args.exam), ("search", args.search), ("page", args.page)) if v}
            return call("GET", "/api/questions/", env, params=params)
        if args.action == "get":
            return call("GET", f"/api/questions/{args.id}/", env)
        if args.action == "create":
            body = build_question_payload(args.exam, args.text, args.choice)
            return call("POST", "/api/questions/", env, body=body, dry_run=dry)
        return call("DELETE", f"/api/questions/{args.id}/", env, dry_run=dry)
    # ops: the contract, read from the API itself
    result = call("GET", "/api/schema/", env, params={"format": "json"})
    if result.status == 200:
        result.data = [
            {"operation": op.get("operationId"), "method": method.upper(), "path": path}
            for path, methods in result.data["paths"].items()
            for method, op in methods.items()
            if method in ("get", "post", "put", "patch", "delete")
        ]
    return result


def render(result: Result, as_json: bool, out) -> None:
    if as_json:
        out.write(json.dumps({"status": result.status, "data": result.data, "error": result.error or None,
                              "request": result.request if result.status is None else None},
                             ensure_ascii=False) + "\n")
        return
    if result.status is None:
        out.write(f"[dry-run] {result.request['method']} {result.request['url']}\n")
        if result.request["json"] is not None:
            out.write(json.dumps(result.request["json"], ensure_ascii=False, indent=2) + "\n")
    elif result.error:
        out.write(f"ERROR: {result.error}\n")
    elif result.status >= 400:
        out.write(f"HTTP {result.status}: {json.dumps(result.data, ensure_ascii=False)}\n")
    elif isinstance(result.data, list):
        for row in result.data:
            out.write("  ".join(str(v) for v in row.values()) + "\n")
    elif isinstance(result.data, dict) and "results" in result.data:
        out.write(f"{result.data['count']} en total (página con {len(result.data['results'])})\n")
        for row in result.data["results"]:
            out.write(f"  #{row['id']}  {row.get('title') or row.get('text')}\n")
    else:
        out.write(json.dumps(result.data, ensure_ascii=False, indent=2) + "\n" if result.data is not None
                  else f"HTTP {result.status} (sin contenido)\n")


def main(argv=None, env=None, out=None) -> int:
    env = os.environ if env is None else env
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    result = dispatch(args, env)
    render(result, args.json, out)
    if result.status is None:
        return EXIT_OK  # a dry-run that was described correctly
    if result.status == -1:
        return EXIT_OTHER
    if result.status == 0:
        return EXIT_NETWORK
    return exit_code_for(result.status)


if __name__ == "__main__":
    sys.exit(main())
