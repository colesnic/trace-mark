"""TraceMark command-line interface."""

from __future__ import annotations

import asyncio
import pathlib
import time
from typing import Annotated
from uuid import UUID

import typer

from tracemark.config import Settings
from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.db.session import session_scope
from tracemark.services.subjects import (
    create_credential,
    create_subject,
    create_tenant,
    get_tenant,
    get_tenant_by_name,
    list_subjects,
    subject_fingerprint_key,
)
from tracemark.watermark.detector import (
    FingerprintCandidate,
    detect_fingerprint,
)
from tracemark.watermark.engine import apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

app = typer.Typer(
    name="tracemark",
    help="Model-agnostic forensic watermarking gateway for LLM text.",
    no_args_is_help=True,
)
tenant_app = typer.Typer(help="Tenant management.", no_args_is_help=True)
subject_app = typer.Typer(help="Subject (employee) management.", no_args_is_help=True)
app.add_typer(tenant_app, name="tenant")
app.add_typer(subject_app, name="subject")


def run(coro):
    return asyncio.run(coro)


@tenant_app.command("create")
def tenant_create(name: str) -> None:
    """Create a new tenant/organization."""

    async def _do() -> None:
        async with session_scope() as session:
            tenant = await create_tenant(session, name)
            print(f"tenant_id={tenant.id}")

    run(_do())


@tenant_app.command("get")
def tenant_get(name: str) -> None:
    """Look up a tenant by name."""

    async def _do() -> None:
        async with session_scope() as session:
            tenant = await get_tenant_by_name(session, name)
            if tenant is None:
                typer.echo(f"no tenant named {name!r}", err=True)
                raise typer.Exit(1)
            print(
                f"tenant_id={tenant.id} name={tenant.name} "
                f"key_version={tenant.key_version}"
            )

    run(_do())


@subject_app.command("create")
def subject_create(
    tenant: Annotated[UUID, typer.Option(help="Tenant UUID.")],
    external_ref: Annotated[str, typer.Option(help="External reference, e.g. employee-123.")],
) -> None:
    """Create a subject (employee) under a tenant."""

    async def _do() -> None:
        async with session_scope() as session:
            subject = await create_subject(session, tenant, external_ref)
            print(f"subject_id={subject.id}")
            print(f"pseudonymous_tag={subject.pseudonymous_tag}")

    run(_do())


@subject_app.command("list")
def subject_list(
    tenant: Annotated[UUID, typer.Option(help="Tenant UUID.")],
) -> None:
    """List subjects for a tenant."""

    async def _do() -> None:
        async with session_scope() as session:
            for s in await list_subjects(session, tenant):
                active = "active" if s.active else "inactive"
                print(f"{s.id}  {s.external_ref:24} {s.pseudonymous_tag} {active}")

    run(_do())


@subject_app.command("credential")
def subject_credential(
    tenant: Annotated[UUID, typer.Option(help="Tenant UUID.")],
    subject: Annotated[UUID, typer.Option(help="Subject UUID.")],
) -> None:
    """Create an API credential. The raw token is shown exactly once."""

    async def _do() -> None:
        async with session_scope() as session:
            token, credential = await create_credential(session, tenant, subject)
            print(f"credential_id={credential.id}")
            print(f"token={token}")

    run(_do())


@app.command("watermark")
def watermark(
    subject: Annotated[UUID, typer.Option(help="Subject UUID.")],
    text: Annotated[str, typer.Option(help="Text to watermark.")],
    policy: Annotated[str, typer.Option()] = "balanced",
    model_scope: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Apply an employee fingerprint to ``text``."""

    async def _do() -> None:
        async with session_scope() as session:
            from tracemark.db.models import Subject

            subj = await session.get(Subject, subject)
            if subj is None:
                typer.echo(f"unknown subject {subject}", err=True)
                raise typer.Exit(1)
            key = subject_fingerprint_key(subj.tenant_id, subj)
            if model_scope:
                key = derive_fingerprint(
                    master_key=Settings().resolve_master_key(),
                    tenant_id=subj.tenant_id,
                    subject_external_ref=subj.external_ref,
                    model_scope=model_scope,
                ).key
            pol = WatermarkPolicy.from_name(policy)
            result = apply_watermark(text=text, fingerprint_key=key, policy=pol)
            print(result.text)
            typer.echo(
                f"# opportunities={result.opportunities_found} "
                f"applied={result.transformations_applied}",
                err=True,
            )

    run(_do())


@app.command("detect")
def detect(
    tenant: Annotated[UUID, typer.Option(help="Tenant UUID.")],
    file: Annotated[pathlib.Path, typer.Option(help="Path to a text file.")],
    policy: Annotated[str, typer.Option()] = "balanced",
) -> None:
    """Detect which tenant subject best explains the text in ``file``."""

    async def _do() -> None:
        async with session_scope() as session:
            tenant_row = await get_tenant(session, tenant)
            if tenant_row is None:
                typer.echo(f"unknown tenant {tenant}", err=True)
                raise typer.Exit(1)
            subjects = await list_subjects(session, tenant)
            candidates = [
                FingerprintCandidate(
                    subject_tag=s.pseudonymous_tag,
                    model_scope=None,
                    key=subject_fingerprint_key(tenant, s),
                )
                for s in subjects
            ]
            text = file.read_text(encoding="utf-8")
            pol = WatermarkPolicy.from_name(policy)
            result = detect_fingerprint(text=text, candidates=candidates, policy=pol)
            print(f"detected={result.detected} reason={result.reason}")
            print(f"usable_opportunities={result.usable_opportunities}")
            print(f"candidates_tested={result.candidates_tested}")
            if result.best_candidate is not None:
                bc = result.best_candidate
                print(
                    f"best={bc.subject_tag} matches={bc.matches} rate={bc.match_rate:.3f} "
                    f"adj_p={bc.adjusted_p_value:.3e} evidence={bc.evidence_score:.2f}"
                )

    run(_do())


@app.command("db-init")
def db_init() -> None:
    """Create database tables (development convenience; prefer Alembic)."""

    async def _do() -> None:
        from tracemark.db.session import init_db

        await init_db()
        print("database initialized")

    run(_do())


@app.command("benchmark")
def benchmark() -> None:
    """Run the local fingerprint attribution benchmark (no LLM calls)."""
    from tracemark.benchmarks.benchmark import run_benchmark

    started = time.perf_counter()
    report = run_benchmark()
    elapsed = time.perf_counter() - started
    print(report)
    print(f"benchmark completed in {elapsed:.1f}s")


if __name__ == "__main__":
    app()
