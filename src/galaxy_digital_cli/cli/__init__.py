import typer

app = typer.Typer(help="CLI for the Galaxy Digital Get Connected API.")


@app.callback()
def main() -> None:
    """Galaxy Digital API command line interface."""
