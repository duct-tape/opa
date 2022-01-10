#!/bin/env python
import json
import os
import re
import subprocess
import click
import keyring
import pyperclip


SESSION_PREFIX = os.environ.get("OPA_PREFIX", "my")



@click.group()
def opa():
    pass

@opa.command("init")
@click.argument("email", required=True)
@click.argument("secret", required=True)
@click.option("-a", "--address", "address", default="https://my.1password.com")
def opa_init(email, secret, address):
    try:
        output = subprocess.check_output(
            f'op signin {address} {email} {secret} --account={SESSION_PREFIX}',
            shell=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
    else:
        click.echo(output)


@opa.command('items')
@click.option("-s", "--search", "search")
def opa_items(search):
    """List items."""
    for item in list_items(search_term=search):
        print(item["overview"]["title"])


@opa.command('search')
@click.argument("name")
@click.option('-c', '--copy', 'copy', default=False, is_flag=True)
def opa_search(name, copy):
    """Search items by name."""
    cache = {}
    item_id = None
    for item_id, item in enumerate(list_items(search_term=name)):
        cache[item_id + 1] = item["uuid"]
        click.echo("{}: {}".format(item_id + 1, item["overview"]["title"]))

    if item_id is None:
        return

    if item_id == 0:
        key = 1
    else:
        key = click.prompt(
            "Which Items would you like to {}? [1-{}]".format(
                "copy" if copy else "see",
                item_id + 1
            )
        )
    try:
        item_uuid = cache[int(key)]
    except (KeyError, ValueError):
        click.echo("Incorrect item provided.", err=True)
    else:
        get_item(item_uuid, copy)


@opa.command('get')
@click.argument("name")
@click.option('-c', '--copy', 'copy', default=False, is_flag=True)
def opa_get(name, copy):
    """Get item and copy into clipboard, if needed."""
    get_item(name, copy)


def list_items(search_term=None):
    command = "op list items"
    result = execute(command=command)

    if result is None:
        return []

    items = json.loads(result)
    for item in items:
        if search_term is None or \
           search_term.lower() in item["overview"]["title"].lower():
            yield item


def get_item(name, copy):
    """Get single item information by name or uuid.
    Copy password to clipboard, if -c flag provided."""
    command = f'op get item "{name}"'
    result = execute(command=command)

    if result is None:
        return

    try:
        data = json.loads(result)
    except ValueError:
        print(repr(result))
        return

    display(data, copy)


def display(data, copy):
    """Display Item information."""
    for field in get_fields(data):
        value = field.get("v", field.get("value"))
        name = field.get("t", field.get("name"))
        if value is not None:
            if copy:
                if name == "password":
                    pyperclip.copy(value)
                    click.echo("Password copied to clipboard")
                    break
            else:
                print("{}: {}".format(name, value))


def login(reset=False):
    """
    Perform login operation, ask for password and save session key into keyring
    """
    key = None
    if not reset:
        key = keyring.get_password("opa", "key")
    if key is None:
        key = click.prompt("Please enter Master Password", hide_input=True)
        keyring.set_password("opa", "key", key)

    if key is None:
        raise Exception("Failed to log in.")

    try:
        output = subprocess.check_output(
            f'echo "{key}" | op signin {SESSION_PREFIX}',
            shell=True
        )
    except subprocess.CalledProcessError as e:
        print("Failed to log in.")
        print(f"  {e}")
        raise Exception(1)

    session_key = re.findall(
        r'export OP_SESSION_{}="(?P<key>.*)"'.format(SESSION_PREFIX),
        output.decode('utf-8'))[0]
    keyring.set_password("opa", "session", session_key)
    return session_key


def execute(command, **kwargs):
    """Execute command with session key. Login, if necessary"""
    session_key = get_session_key()
    if not session_key:
        session_key = login()

    env = dict(os.environ, OP_SESSION_my=session_key)
    result = None
    try:
        result = subprocess.check_output(
            command,
            shell=True,
            env=env,
            stderr=subprocess.STDOUT,
            **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf-8"))
        if "You are not currently signed in" in e.output.decode("utf-8"):
            session_key = login()
            env = dict(os.environ, OP_SESSION_my=session_key)
            result = subprocess.check_output(command, shell=True, env=env)

    return result


def get_fields(data):
    """Fetch fields from details or sections"""
    for field in data["details"].get("fields", []):
        yield field

    sections = data["details"].get("sections", [])
    for section in sections:
        for field in section.get("fields", []):
            yield field


def get_session_key():
    return keyring.get_password("opa", "session")


if __name__ == '__main__':
    opa()
