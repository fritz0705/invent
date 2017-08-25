# coding: utf-8

import argparse
import sys

import qrcode
import sqlalchemy
from sqlalchemy import or_, asc, desc, any_

import invent.label
from invent.sql import *


def print_item(item, show_qrcode=True):
    print("{item.inventory_number} – {item.title}".format(item=item))
    print("-" * 80)
    print("  Realm:        {}".format(item.realm.name))
    if item.resource_url:
        print("  Resource URL: {}".format(item.resource_url))
    if item.owner:
        print("  Owner:        {}".format(item.owner))
    print("  Created at:   {}".format(item.created_at))
    print("  Updated at:   {}".format(item.updated_at))
    print("  Is active:    {}".format(item.is_active))
    print("  Is labeled:   {}".format(item.is_labeled))
    if show_qrcode:
        print()
        qr = qrcode.QRCode()
        qr.add_data(item.inventory_number)
        qr.print_ascii(tty=True)


def generate_item_label(label_type, item, attributes,
                        output=None):
    if output is None:
        output = "{item.inventory_number}-{label_type}.{ext}"
    label_factory = invent.label.label_factories[label_type]
    if hasattr(output, "write"):
        return label_factory.generate_for_item(item, attributes=attributes,
                                               output=output)
    output_file = output.format(item=item,
                                label_type=label_type,
                                ext=label_factory.file_extension)
    with open(output_file, "wb") as fh:
        return label_factory.generate_for_item(item, attributes=attributes,
                                               output=fh)


def generate_labels(args, session, engine):
    attrs = dict(args.attr)
    label_factory = invent.label.label_factories[args.type]
    attrs = dict(args.attr)
    items = []
    if args.item:
        items.extend(session.query(Item).filter(
            Item.inventory_number == any_(args.item)).all())
    if args.item_stdin:
        inventory_numbers = [l.strip() for l in sys.stdin.readlines()]
        items.extend(session.query(Item).filter(Item.inventory_number ==
                                                any_(inventory_numbers)).all())

    if items:
        output = args.output
        if output == "-":
            output = sys.stdout.buffer
        for item in items:
            generate_item_label(args.type, item, attrs, output=output)
    elif args.output:
        with open(args.output, "wb") as fh:
            label_factory.generate(attributes=attrs, output=fh)
    else:
        label_factory.generate(attributes=attrs, output=sys.stdout.buffer)


def show_item(args, session, engine):
    items = session.query(Item).filter(
        Item.inventory_number.in_(args.inventory_numbers)).all()
    for item in items:
        print_item(item, show_qrcode=args.show_qrcode)
        print()


def create_db(args, session, engine):
    Base.metadata.create_all(engine)
    if args.alembic_ini:
        import alembic.config
        alembic_cfg = alembic.config.Config(args.alembic_ini)
        alembic.command.stamp(alembic_cfg, "head")


def add_item(args, session, engine):
    if args.realm is None:
        realm = session.query(Realm).filter(Realm.is_external == False).first()
    else:
        realm = session.query(Realm).filter(Realm.prefix == args.realm).first()
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
    if args.label_type:
        generate_item_label(args.label_type, item, dict(args.label_attribute),
                            output=args.label_output)


def update_item(args, session, engine):
    item = session.query(Item).filter(
        Item.inventory_number == args.inventory_number).first()
    if not item:
        return
    if args.title:
        item.title = args.title
    if args.resource_url:
        item.resource_url = args.resource_url
    if args.owner:
        item.owner = args.owner
    if args.active is not None:
        item.is_active = args.active
    if args.labeled is not None:
        item.is_labeled = args.labeled
    session.add(item)
    session.commit()
    if not args.quiet:
        print_item(item)


def list_realms(args, session, engine):
    realms = session.query(Realm).filter(Realm.is_external == any_([args.external,
                                                                    not args.internal])).all()
    for realm in realms:
        print(args.format.format(realm=realm))


def list_items(args, session, engine):
    query = session.query(Item)
    if args.realm is not None:
        realm = session.query(Realm).filter(Realm.prefix == args.realm).first()
        if realm is not None:
            query = query.filter(Item.realm_id == realm.id)
    if args.owner is not None:
        query = query.filter(Item.owner == str(args.owner))
    if args.active is not None:
        query = query.filter(Item.is_active == args.active)
    if args.labeled is not None:
        query = query.filter(Item.is_labeled == args.labeled)
    query = query.order_by(desc(args.sort_key))
    if args.limit > 0:
        query = query.limit(args.limit)
    query = query.offset(args.offset)
    items = query.all()
    item_format = args.format
    if item_format is None:
        if args.show_title:
            item_format = "{item.inventory_number}:  {item.title}"
        else:
            item_format = "{item.inventory_number}"
    for item in items:
        print(item_format.format(item=item))


def main(argv=sys.argv[1:]):
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--database", "-D", default="sqlite://")
    subparsers = argparser.add_subparsers(dest="subcommand")

    add_item_subparser = subparsers.add_parser("add-item", aliases=["add"])
    add_item_subparser.add_argument("--inventory-number", "-I")
    add_item_subparser.add_argument("--realm", "-R")
    add_item_subparser.add_argument("--resource-url", "-U")
    add_item_subparser.add_argument("--owner", "-o")
    add_item_subparser.add_argument("--label-type", "-l")
    add_item_subparser.add_argument("--label-attribute", "-a", nargs=2,
                                    action="append")
    add_item_subparser.add_argument("--label-output", "-L")
    add_item_subparser.add_argument("title")

    add_realm_subparser = subparsers.add_parser("add-realm")
    add_realm_subparser.add_argument("--url-base", "-U")
    add_realm_subparser.add_argument("prefix")
    add_realm_subparser.add_argument("name")

    create_db_subparser = subparsers.add_parser("create-db")
    create_db_subparser.add_argument("--alembic-ini", "-a")

    update_item_subparser = subparsers.add_parser("update-item", aliases=["update", "modify"])
    update_item_subparser.add_argument("--title", "-t")
    update_item_subparser.add_argument("--resource-url", "-U")
    update_item_subparser.add_argument("--owner", "-o")
    update_item_subparser.add_argument("--active", action="store_true",
            default=None)
    update_item_subparser.add_argument("--inactive", dest="active",
            action="store_false")
    update_item_subparser.add_argument("--labeled", "--labelled",
            default=None, action="store_true")
    update_item_subparser.add_argument("--unlabeled", "--unlabelled",
            "--not-labelled", "--not-labeled", dest="labeled",
            action="store_false")
    update_item_subparser.add_argument("--quiet", "-q", action="store_true")
    update_item_subparser.add_argument("inventory_number")

    delete_item_subparser = subparsers.add_parser("delete-item")
    delete_item_subparser.add_argument("inventory_number")

    list_items_subparser = subparsers.add_parser(
        "list-items", aliases=["list"])
    list_items_subparser.add_argument("--realm", "-R")
    list_items_subparser.add_argument("--limit", "-L", type=int, default=20)
    list_items_subparser.add_argument("--offset", "-O", type=int, default=0)
    list_items_subparser.add_argument("--sort-key", "-S", default="updated_at")
    list_items_subparser.add_argument("--owner", "-o")
    list_items_subparser.add_argument("--active", action="store_true",
            default=None)
    list_items_subparser.add_argument("--inactive", dest="active",
            action="store_false")
    list_items_subparser.add_argument("--labeled", "--labelled",
            action="store_true", default=None)
    list_items_subparser.add_argument("--unlabeled", "--unlabelled",
            "--not-labelled", "--not-labeled", dest="labeled",
            action="store_false")
    list_items_subparser.add_argument("--show-title", default=True,
                                      action="store_true")
    list_items_subparser.add_argument("--hide-title", dest="show_title",
                                      action="store_false")
    list_items_subparser.add_argument("--format", default=None)
    list_items_subparser.add_argument("--csv", dest="format", action="store_const",
            const="{item.id!r};{item.inventory_number!r};{item.title!r};"
            "{item.owner!r};{item.resource_url!r};{item.is_active!r};"
            "{item.is_labeled!r};{item.realm.prefix!r};{item.realm.name!r};"
            "{item.created_at};{item.updated_at}")

    show_item_subparser = subparsers.add_parser("show-item", aliases=["show",
                                                                      "get",
                                                                      "show-items"])
    show_item_subparser.add_argument("--show-qrcode", default=True,
            action="store_true")
    show_item_subparser.add_argument("--hide-qrcode", "-Q", action="store_false",
            dest="show_qrcode")
    show_item_subparser.add_argument("inventory_numbers", nargs="+")

    generate_label_subparser = subparsers.add_parser("generate-label")
    generate_label_subparser.add_argument("--output", "-o")
    generate_label_subparser.add_argument("--attr", "-a", nargs=2, action="append",
                                          default=[])
    generate_label_subparser.add_argument("--item", "-i", action="append")
    generate_label_subparser.add_argument("--item-stdin", action="store_true")
    generate_label_subparser.add_argument("type")

    list_realms_subparser = subparsers.add_parser("list-realms")
    list_realms_subparser.add_argument("--internal", action="store_true",
                                       default=True)
    list_realms_subparser.add_argument("--no-internal", "-i", dest="internal",
                                       action="store_false")
    list_realms_subparser.add_argument("--external", action="store_true",
                                       default=True)
    list_realms_subparser.add_argument("--no-external", "-e", dest="external",
                                       action="store_false")
    list_realms_subparser.add_argument("--format", default="[{realm.prefix}]"
                                       " {realm.name}")

    args = argparser.parse_args(argv)

    engine = sqlalchemy.create_engine(args.database)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    subcommand = None

    if args.subcommand in {"add", "add-item"}:
        subcommand = add_item
    elif args.subcommand == "add-realm":
        subcommand = add_realm
    elif args.subcommand == "delete-item":
        pass
    elif args.subcommand in {"list", "list-items"}:
        subcommand = list_items
    elif args.subcommand == "list-realms":
        subcommand = list_realms
    elif args.subcommand in {"show", "get", "show-item", "show-items"}:
        subcommand = show_item
    elif args.subcommand in {"update-item", "update", "modify"}:
        subcommand = update_item
    elif args.subcommand == "create-db":
        subcommand = create_db
    elif args.subcommand == "generate-label":
        subcommand = generate_labels

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
