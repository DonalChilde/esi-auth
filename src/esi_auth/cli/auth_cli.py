import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def add():
    """Add an authorized character."""
    pass
    # TODO implement add


@app.command()
def remove():
    """Remove an authorized character."""
    pass
    # TODO implement remove


@app.command()
def list():
    """List authorized characters."""
    pass
    # TODO implement list


@app.command()
def refresh():
    """Refresh tokens for authorized characters."""
    pass
    # TODO implement refresh


@app.command()
def backup():
    """Backup the database of authorized characters."""
    pass
    # TODO implement backup


@app.command()
def restore():
    """Restore the database of authorized characters from a backup."""
    pass
    # TODO implement restore
