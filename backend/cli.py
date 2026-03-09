"""DataPilot CLI — Test from the terminal"""
import json, sys
import click
import httpx

API_BASE = "http://localhost:8000"


@click.group()
def cli():
    """DataPilot CLI"""
    pass


@cli.command()
@click.option("--host", required=True)
@click.option("--port", default=5432)
@click.option("--db", required=True)
@click.option("--user", required=True)
@click.option("--password", required=True, prompt=True, hide_input=True)
@click.option("--alias", default="My Database")
@click.option("--schemas", default="public")
def connect(host, port, db, user, password, alias, schemas):
    """Connect and introspect a PostgreSQL database."""
    click.echo(f"\n🔌 Connecting to {host}:{port}/{db}...")
    payload = {"host": host, "port": port, "database": db, "username": user,
               "password": password, "alias": alias, "schemas": schemas.split(",")}
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{API_BASE}/connect", json=payload)
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\n✅ Connected!")
        click.echo(f"   Connection ID : {data['connection_id']}")
        click.echo(f"   Tables found  : {data['total_tables']}")
        click.echo(f"\n💡 Save this ID: {data['connection_id']}")
    else:
        click.echo(f"\n❌ Failed: {response.json().get('detail', response.text)}")
        sys.exit(1)


@cli.command()
@click.option("--connection-id", required=True)
@click.option("--max-rows", default=10)
@click.argument("question")
def ask(connection_id, max_rows, question):
    """Ask a question about your database."""
    click.echo(f"\n🤔 {question}\n")
    payload = {"connection_id": connection_id, "question": question,
               "options": {"max_rows": max_rows, "include_sql": True}}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{API_BASE}/ask", json=payload)
    if response.status_code == 200:
        data = response.json()
        click.echo(f"💬 {data['answer']}")
        if data.get("sql_result"):
            click.echo(f"\n📝 SQL: {data['sql_result']['sql']}")
            rows = data["sql_result"]["rows"]
            if rows:
                click.echo(f"\n📊 Results:")
                for row in rows[:10]:
                    click.echo(f"   {row}")
    else:
        click.echo(f"\n❌ {response.json().get('detail', response.text)}")


@cli.command()
@click.option("--connection-id", required=True)
def repl(connection_id):
    """Interactive question mode."""
    click.echo(f"\n🚀 DataPilot REPL | connection: {connection_id}")
    click.echo("   Type a question, or \'quit\' to exit.\n")
    session_id = None
    while True:
        try:
            question = click.prompt("You")
        except (click.Abort, EOFError):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        payload = {"connection_id": connection_id, "question": question,
                   "session_id": session_id, "options": {"max_rows": 20}}
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{API_BASE}/ask", json=payload)
        if r.status_code == 200:
            data = r.json()
            session_id = data.get("session_id")
            click.echo(f"\nDataPilot: {data['answer']}")
            if data.get("sql_result"):
                click.echo(f"SQL: {data['sql_result']['sql']}")
            click.echo()
        else:
            click.echo(f"\n❌ {r.json().get('detail', r.text)}\n")
    click.echo("Goodbye! 👋")


@cli.command()
def health():
    """Check if the API is running."""
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5.0)
        data = r.json()
        click.echo(f"✅ API is running | status={data['status']} | env={data['environment']}")
    except Exception as e:
        click.echo(f"❌ API not reachable: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
