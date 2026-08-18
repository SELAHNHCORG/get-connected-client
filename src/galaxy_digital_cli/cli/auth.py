"""``galaxy auth`` -- the credential-exchange endpoints on the command line.

Login and authenticate are writes in the sense that ``--read-only`` blocks
them: each mints a credential (a session token, or a one-click login link),
a side effect worth gating like any other write. They are *not* run through
:func:`~galaxy_digital_cli.cli._confirm.confirm_write`, though -- an auth
exchange the operator just typed a password into does not benefit from a
second "are you sure?" prompt, and neither command ever echoes the password:
it is always collected via a hidden prompt (or ``--password`` for scripting,
at the operator's own risk).
"""

from __future__ import annotations

import typer

from ._output import output, output_one
from ._state import get_state, handle_errors

auth_app = typer.Typer(help="Login and authenticate.", no_args_is_help=True)

_EMAIL = typer.Option(..., "--email", help="Account email address.")
_PASSWORD = typer.Option(
    ...,
    "--password",
    prompt=True,
    hide_input=True,
    help="Account password (prompted for, hidden, if not given).",
)


@auth_app.command("login")
@handle_errors
def login(
    ctx: typer.Context,
    email: str = _EMAIL,
    password: str = _PASSWORD,
    key: str | None = typer.Option(
        None, "--key", help="API key, if the site requires one for login."
    ),
) -> None:
    """Exchange credentials for a session token.

    Blocked by ``--read-only``: a login mints a bearer token, a side effect
    worth gating like any other write.
    """
    state = get_state(ctx)
    output_one(state, state.client.auth.login(email, password, key=key))


@auth_app.command("authenticate")
@handle_errors
def authenticate(
    ctx: typer.Context, email: str = _EMAIL, password: str = _PASSWORD
) -> None:
    """Verify credentials and mint a one-click login link.

    Blocked by ``--read-only`` for the same reason as ``login``.
    """
    state = get_state(ctx)
    output(
        state,
        state.client.auth.authenticate(email, password),
        ["link", "expires", "now"],
        title="One-Click Links",
    )
