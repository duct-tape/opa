#!/bin/env python
import base64
import json
import subprocess
import click

from opa.util import get_list, get_item, print_item, execute


ITEM_TEMPLATES = dict(
    login={
        'fields': [
            {'designation': 'username', 'name': 'username', 'type': 'T', 'value': ''},
            {'designation': 'password', 'name': 'password', 'type': 'P', 'value': ''}
        ],
        'notesPlain': '',
        'passwordHistory': [],
        'sections': []
    }
)


@click.group()
def opa():
    pass


@opa.command()
def list():
    for item in get_list(option="items"):
        print(item["overview"]["title"])


@opa.command()
@click.argument("name")
def search(name):
    for item in get_list(option="items"):
        title = item["overview"]["title"]
        if name.lower() in title.lower():
            print(title)


@opa.command()
@click.argument("name")
@click.option("-c", "--copy",
              is_flag=True,
              help="Silently copy password value into clipboard.")
def get(name, copy):
    data = get_item(name)
    if data is None:
        exit(1)

    print_item(data, copy)


@opa.command()
def vaults():
    for item in get_list(option="vaults"):
        print(item['name'])


@opa.command()
@click.argument("name")
@click.option("-c", "--copy",
              is_flag=True,
              help="Silently copy password value into clipboard.")
@click.option("-r", "--recipe",
              type=str,
              help=(
                  "Recipe for generated password: comma separated list of "
                  "'letters','digits', 'symbols' and 0-64 for password length."
              ),
              default="letters,digits,symbols,32")
def gen(name, copy, recipe):
    template = ITEM_TEMPLATES['login']

    position, username_template = [
        (c, x) for c, x in enumerate(template['fields']) if x['name'] == 'username'
    ][0]
    username_template['value'] = name
    template['fields'][position] = username_template

    data_to_encode = json.dumps(template, separators=(',', ':'))

    p = subprocess.Popen(["op", "encode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    encoded_output, errors = p.communicate(data_to_encode.encode('utf-8'))
    if errors is None:
        encoded_data = encoded_output.decode('utf-8').strip()
    else:
        print(f"Failed to encode data: {errors}")
        exit(1)

    # Create item
    data = base64.b64encode(json.dumps(template).encode('utf-8')).decode('utf-8')
    command = f'op create item login {encoded_data} --title="{name}" --generate-password={recipe}'
    result = json.loads(execute(command=command))

    print_item(data=get_item(result['uuid']), copy=copy)


if __name__ == '__main__':
    opa()
