#!/bin/env python
import json
import os
import re
import subprocess
import click
import keyring
import pyperclip


SESSION_PREFIX = os.environ.get("OPA_PREFIX", "my")


@click.command()
@click.argument("name")
@click.option("-c",
              "copy",
              is_flag=True,
              help="Silently copy password value into clipboard.")
@click.option("-l",
              "list_items",
              is_flag=True,
              help="List available items")
def opa(name, copy, list_items):
    """1Password helper utility."""
    if list_items:
        get_items_list()
    else:
        get_item(name, copy)


def get_items_list():
    """List items."""
    command = "op list items"
    result = execute(command=command)

    data = json.loads(result)
    for item in data:
        print(item["overview"]["title"])


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

    for field in get_fields(data):
        value = field.get("v", field.get("value"))
        name = field.get("t", field.get("name"))
        if value is not None:
            if copy:
                if name == "password":
                    pyperclip.copy(value)
            else:
                print("{}: {}".format(name, value))


def login():
    """
    Perform login operation, ask for password and save session key into keyring
    """
    key = keyring.get_password("opa", "key")
    if key is None:
        key = click.prompt("Please enter password, blin.")
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
