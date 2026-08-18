"""``galaxy clusters``/``causes``/``interests``/``impacts``/``registration-questions``.

Small namespaces bundled in one module: ``clusters`` is create/delete
(agencies attach to clusters -- see ``galaxy agencies clusters``); the other
four are flat, read-only lookups the site defines up front, each a single
``list`` command.
"""

from __future__ import annotations

import typer

from ._confirm import confirm_write
from ._output import output, output_result
from ._state import get_state, handle_errors

clusters_app = typer.Typer(help="Manage clusters.", no_args_is_help=True)
causes_app = typer.Typer(help="List site causes.", no_args_is_help=True)
interests_app = typer.Typer(help="List site interests.", no_args_is_help=True)
impacts_app = typer.Typer(help="List site impact areas.", no_args_is_help=True)
registration_questions_app = typer.Typer(
    help="List the site's custom registration questions.", no_args_is_help=True
)

_CLUSTER_ID = typer.Argument(..., help="ID of the cluster.")


# ---------------------------------------------------------------------------
# clusters
# ---------------------------------------------------------------------------


@clusters_app.command("list")
@handle_errors
def list_clusters(ctx: typer.Context) -> None:
    """List clusters."""
    state = get_state(ctx)
    output(state, state.client.clusters.list(), ["id", "name"], title="Clusters")


@clusters_app.command("create")
@handle_errors
def create_cluster(
    ctx: typer.Context, name: str = typer.Option(..., "--name", help="Cluster name.")
) -> None:
    """Create a cluster."""
    state = get_state(ctx)
    fields = {"name": name}
    confirm_write(state, f"POST {state.client.clusters.url()}", fields)
    output_result(state, state.client.clusters.create(**fields))


@clusters_app.command("delete")
@handle_errors
def delete_cluster(ctx: typer.Context, id: int = _CLUSTER_ID) -> None:
    """Delete a cluster."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.clusters.url(id)}")
    state.client.clusters.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# lookups: causes, interests, impacts, registration questions
# ---------------------------------------------------------------------------


@causes_app.command("list")
@handle_errors
def list_causes(ctx: typer.Context) -> None:
    """List the site's available causes."""
    state = get_state(ctx)
    output(state, state.client.lookups.causes(), ["id", "name"], title="Causes")


@interests_app.command("list")
@handle_errors
def list_interests(ctx: typer.Context) -> None:
    """List the site's available interests."""
    state = get_state(ctx)
    output(state, state.client.lookups.interests(), ["id", "name"], title="Interests")


@impacts_app.command("list")
@handle_errors
def list_impacts(ctx: typer.Context) -> None:
    """List the site's available impact areas."""
    state = get_state(ctx)
    output(
        state,
        state.client.lookups.impacts(),
        ["id", "impact_name"],
        title="Impacts",
    )


@registration_questions_app.command("list")
@handle_errors
def list_registration_questions(ctx: typer.Context) -> None:
    """List the site's custom registration questions."""
    state = get_state(ctx)
    output(
        state,
        state.client.lookups.registration_questions(),
        ["id", "q_label", "q_type"],
        title="Registration Questions",
    )
