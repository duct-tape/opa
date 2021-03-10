import json

import click

from opa.util import (
    ask_for_password,
    execute,
    get_item,
    get_list,
    prepare_create_payload,
    print_item,
)


@click.group()
def opa():
    pass


@opa.command()
def list():
    for item in get_list(option="items"):
        click.echo(item["overview"]["title"])


@opa.command()
@click.argument("name")
def search(name):
    for item in get_list(option="items"):
        title = item["overview"]["title"]
        if name.lower() in title.lower():
            click.echo(title)


@opa.command()
@click.argument("name")
@click.option(
    "-c", "--copy", is_flag=True, help="Silently copy password value into clipboard."
)
def get(name, copy):
    data = get_item(name)
    if data is None:
        exit(1)

    print_item(data, copy)


@opa.command()
def vaults():
    for item in get_list(option="vaults"):
        click.echo(item["name"])


@opa.command()
@click.argument("name")
def insert(name):
    password = ask_for_password()
    encoded_data = prepare_create_payload(username=name, password=password)
    command = f'op create item login {encoded_data} --title="{name}"'
    result = json.loads(execute(command=command))

    print_item(
        data=get_item(result["uuid"]),
    )


@opa.command()
@click.argument("name")
@click.option(
    "-c", "--copy", is_flag=True, help="Silently copy password value into clipboard."
)
@click.option(
    "-r",
    "--recipe",
    type=str,
    help=(
        "Recipe for generated password: comma separated list of "
        "'letters','digits', 'symbols' and 0-64 for password length."
    ),
    default="letters,digits,symbols,32",
)
def gen(name, copy, recipe):
    encoded_data = prepare_create_payload(username=name)
    command = f'op create item login {encoded_data} --title="{name}" --generate-password={recipe}'
    result = json.loads(execute(command=command))

    print_item(data=get_item(result["uuid"]), copy=copy)


if __name__ == "__main__":
    opa()
