"""``galaxy auth`` -- the credential-exchange endpoints on the command line.

``login`` is the command that makes the rest of the CLI work: the site API
key alone cannot authenticate a request, so every session starts by trading
an email, a password and that key for a session token (a JWT good for about
a year), which is then sent as ``Authorization: Bearer <token>``.

``--export`` exists for exactly that hand-off. It puts one shell-eval'able
line on stdout and nothing else, so the token can be adopted by the current
shell without ever being written to a file::

    eval "$(galaxy auth login --email you@example.org --export)"

Everything else the command has to say -- the password prompt included --
goes to stderr, which is why the password is prompted for in the body with
``err=True`` rather than by ``typer.Option(prompt=True)``.

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

import shlex

import typer

from ..client import _token_of
from ..exceptions import GalaxyError
from ._output import err_console, output, output_one
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
    password: str | None = typer.Option(
        None,
        "--password",
        help="Account password (prompted for, hidden, if not given).",
    ),
    key: str | None = typer.Option(
        None, "--key", help="Site API key for the login body (or GALAXY_API_KEY)."
    ),
    export: bool = typer.Option(
        False,
        "--export",
        help="Print only `export GALAXY_API_TOKEN=...` for use with eval.",
    ),
) -> None:
    """Exchange credentials for a session token.

    Blocked by ``--read-only``: a login mints a bearer token, a side effect
    worth gating like any other write.
    """
    state = get_state(ctx)
    if key:
        # Fold --key into settings *before* state.client is first touched:
        # the client is built eagerly from settings.api_key, and a
        # standalone `--key` login (no GALAXY_API_KEY / GALAXY_API_TOKEN in
        # the environment) must still be able to construct a client to log
        # in with. Settings is a plain, mutable dataclass, so this is safe.
        state.settings.api_key = key
    # Prompted here, not via typer.Option(prompt=True), so the prompt lands
    # on stderr and --export's stdout stays a single clean line.
    secret: str = (
        password
        if password is not None
        else typer.prompt("Password", hide_input=True, err=True)
    )
    result = state.client.login(email, secret, key=key)
    if export:
        token = _token_of(result)
        if not token:
            raise GalaxyError("login succeeded but returned no token")
        # Deliberately not the rich console: this line must reach stdout
        # verbatim, unwrapped and unstyled, for `eval` to consume. JWTs are
        # base64url + dots, so shlex.quote is normally a no-op on them, but
        # a hostile or unexpected token must never be able to break out of
        # the `eval "$(...)"` this line is designed to be fed into.
        typer.echo(f"export GALAXY_API_TOKEN={shlex.quote(token)}")
        return
    output_one(state, result)
    if not state.json_output:
        err_console.print(
            "Adopt this token in your shell with:\n"
            f'  eval "$(galaxy auth login --email {email} --export)"',
            highlight=False,
        )


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
