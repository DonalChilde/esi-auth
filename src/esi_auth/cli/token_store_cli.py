import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def initialize():
    """Initialize the token store."""
    pass
    # TODO implement initialize
