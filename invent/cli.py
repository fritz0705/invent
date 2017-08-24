# coding: utf-8

import argparse
import sys

import qrcode
import sqlalchemy
from sqlalchemy import or_, asc, desc

import invent.label
from invent.sql import *

def print_item(item):
    print("{item.inventory_number} – {item.title}".format(item=item))
    print("-" * 80)
    print("  Realm:        {}".format(item.realm.name))
    if item.resource_url:
        print("  Resource URL: {}".format(item.resource_url))
    if item.owner:
        print("  Owner:        {}".format(item.owner))
    print("  Created at:   {}".format(item.created_at))
    print("  Updated at:   {}".format(item.updated_at))
    print()
    qr = qrcode.QRCode()
    qr.add_data(item.inventory_number)
    qr.print_ascii(tty=True)

def generate_label(args, session, engine):
    label_factory = invent.label.label_factories[args.type]
    attrs = dict(args.attr)
    item = None
    if args.item:
        item = session.query(Item).filter(Item.inventory_number == args.item).first()

    if item and args.output:
        with open(args.output, "wb") as fh:
            label_factory.generate_for_item(item, attributes=attrs,
                    output=fh)
    elif item:
        res = label_factory.generate_for_item(item, attributes=attrs,
                output=sys.stdout.buffer)
    elif args.output:
        with open(args.output, "wb") as fh:
            label_factory.generate(attributes=attrs, output=fh)
    else:
        label_factory.generate(attributes=attrs, output=sys.stdout.buffer)

def show_item(args, session, engine):
    item = session.query(Item).filter(Item.inventory_number == args.inventory_number).first()
    if item:
        print_item(item)

def create_db(args, session, engine):
    Base.metadata.create_all(engine)

def add_item(args, session, engine):
    if args.realm is None:
        realm = session.query(Realm).filter(Realm.is_external == False).first()
    else:
        realm = session.query(Realm).filter(or_(Realm.id == args.realm,
            Realm.prefix == args.realm)).first()
    if not realm:
        return
    item = Item()
    if args.inventory_number:
        item.inventory_number = args.inventory_number
    if args.owner:
        item.owner = args.owner
    item.realm_id = realm.id
    item.resource_url = args.resource_url
    item.title = args.title
    session.add(item)
    session.commit()
    if not item.inventory_number:
        item.generate_inventory_number()
        session.add(item)
        session.commit()
    print_item(item)

def list_items(args, session, engine):
    query = session.query(Item)
    if args.realm is not None:
        realm = session.query(Realm).filter(or_(Realm.id == args.realm,
            Realm.prefix == args.realm)).first()
        if realm is not None:
            query = query.filter(Item.realm_id == realm.id)
    query = query.order_by(desc(args.sort_key))
    query = query.limit(args.limit)
    query = query.offset(args.offset)
    items = query.all()
    for item in items:
        print("{item.inventory_number}:  {item.title}".format(item=item))

def main(argv=sys.argv[1:]):
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--database", "-D", default="sqlite://")
    subparsers = argparser.add_subparsers(dest="subcommand")

    add_item_subparser = subparsers.add_parser("add-item")
    add_item_subparser.add_argument("--inventory-number", "-I")
    add_item_subparser.add_argument("--realm", "-R")
    add_item_subparser.add_argument("--resource-url", "-U")
    add_item_subparser.add_argument("--owner", "-o")
    add_item_subparser.add_argument("title")

    add_realm_subparser = subparsers.add_parser("add-realm")
    add_realm_subparser.add_argument("--url-base", "-U")
    add_realm_subparser.add_argument("prefix")
    add_realm_subparser.add_argument("name")

    create_db_subparser = subparsers.add_parser("create-db")

    update_item_subparser = subparsers.add_parser("update-item")
    update_item_subparser.add_argument("--title", "-t")
    update_item_subparser.add_argument("--resource-url", "-U")
    update_item_subparser.add_argument("--owner", "-o")
    update_item_subparser.add_argument("inventory_number")

    delete_item_subparser = subparsers.add_parser("delete-item")
    delete_item_subparser.add_argument("inventory_number")

    list_items_subparser = subparsers.add_parser("list-items")
    list_items_subparser.add_argument("--realm", "-R")
    list_items_subparser.add_argument("--limit", "-l", type=int, default=20)
    list_items_subparser.add_argument("--offset", "-o", type=int, default=0)
    list_items_subparser.add_argument("--sort-key", "-S", default="updated_at")

    show_item_subparser = subparsers.add_parser("show-item")
    show_item_subparser.add_argument("inventory_number")

    generate_label_subparser = subparsers.add_parser("generate-label")
    generate_label_subparser.add_argument("--output", "-o")
    generate_label_subparser.add_argument("--attr", "-a", nargs=2, action="append",
            default=[])
    generate_label_subparser.add_argument("--item", "-i")
    generate_label_subparser.add_argument("type")

    args = argparser.parse_args(argv)

    engine = sqlalchemy.create_engine(args.database)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    subcommand = None

    if args.subcommand == "add-item":
        subcommand = add_item
    elif args.subcommand == "add-realm":
        pass
    elif args.subcommand == "delete-item":
        pass
    elif args.subcommand == "list-items":
        subcommand = list_items
    elif args.subcommand == "show-item":
        subcommand = show_item
    elif args.subcommand == "update-item":
        pass
    elif args.subcommand == "create-db":
        subcommand = create_db
    elif args.subcommand == "generate-label":
        subcommand = generate_label

    if subcommand is None:
        argparser.print_help()
    else:
        session = Session()
        try:
            subcommand(args, session=session, engine=engine)
        finally:
            session.close()

if __name__ == "__main__":
    main()

