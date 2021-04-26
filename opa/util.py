import json
import os
import re
import subprocess

import click
import keyring
import pyperclip

SESSION_PREFIX = os.environ.get("OPA_PREFIX", "my")
ITEM_TEMPLATES = dict(
    login={
        "fields": [
            {"designation": "username", "name": "username", "type": "T", "value": ""},
            {"designation": "password", "name": "password", "type": "P", "value": ""},
        ],
        "notesPlain": "",
        "passwordHistory": [],
        "sections": [],
    }
)


def get_list(option):
    """List items."""
    result = execute(command=f"op list {option}")

    data = json.loads(result)
    for item in data:
        yield item


def get_item(name):
    """Get single item information by name or uuid."""
    result = execute(command=f'op get item "{name}"')

    if result is None:
        click.echo("Failed to fetch password, please check log above for details.")
        return None

    try:
        data = json.loads(result)
    except ValueError:
        click.echo(repr(result))
        return

    return get_values(data)


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
            f'echo "{key}" | op signin {SESSION_PREFIX}', shell=True
        )
    except subprocess.CalledProcessError as e:
        click.echo("Failed to log in.")
        click.echo(f"  {e}")
        raise Exception(1) from e

    session_key = re.findall(
        r'export OP_SESSION_{}="(?P<key>.*)"'.format(SESSION_PREFIX),
        output.decode("utf-8"),
    )[0]
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
            command, shell=True, env=env, stderr=subprocess.STDOUT, **kwargs
        )
    except subprocess.CalledProcessError as e:
        output = e.output.decode("utf-8").strip()
        if (
            "You are not currently signed in" in output
            or "session expired, sign in to create a new session" in output
        ):
            session_key = login()
            env = dict(os.environ, OP_SESSION_my=session_key)
            result = subprocess.check_output(command, shell=True, env=env)
        else:
            print(output)

    return result


def get_fields(data):
    """Fetch fields from details or sections"""
    for field in data["details"].get("fields", []):
        yield field

    sections = data["details"].get("sections", [])
    for section in sections:
        for field in section.get("fields", []):
            yield field


def get_values(data):
    values = dict(title=data["overview"]["title"])

    for field in get_fields(data):
        value = field.get("v", field.get("value"))
        name = field.get("t", field.get("name"))
        values[name] = value

    return values


def get_session_key():
    return keyring.get_password("opa", "session")


def print_item(data, copy=None):
    if copy:
        if data.get("password") is not None:
            pyperclip.copy(data["password"])
            click.echo(
                f"Copied {data['title']} password for {_get_username(data)} into clipboard."
            )
        elif data.get("sudo_password") is not None:
            pyperclip.copy(data["sudo_password"])
            click.echo(
                f"Copied {data['title']} password for {_get_username(data)} into clipboard."
            )
        else:
            click.echo("MEH! {}".format(repr(data)))
    else:
        for key, value in data.items():
            click.echo(f"{key}: {value}")


def prepare_create_payload(**params):
    template = ITEM_TEMPLATES["login"]

    for key, value in params.items():
        position, param_template = [
            (c, x) for c, x in enumerate(template["fields"]) if x["name"] == key
        ][0]
        param_template["value"] = value
        template["fields"][position] = param_template

    data_to_encode = json.dumps(template, separators=(",", ":"))

    p = subprocess.Popen(
        ["op", "encode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    encoded_output, errors = p.communicate(data_to_encode.encode("utf-8"))
    if errors is not None:
        click.echo(f"Failed to encode data: {errors}")
        exit(1)

    return encoded_output.decode("utf-8").strip()


def ask_for_password():
    password = click.prompt("Please enter password", hide_input=True)
    confirmation = click.prompt("Please confirm password", hide_input=True)
    if password != confirmation:
        click.echo(
            "Passwords do not match, please try again.", err=True, color="\033[31m"
        )
        return ask_for_password()
    return password


def _get_username(data):
    """Return Username for given entry."""
    if "username" in data:
        return data["username"]
    elif "title" in data:
        return data["title"]
    else:
        return data["user[login]"]
