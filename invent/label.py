# coding: utf-8

import subprocess
import urllib.parse

import jinja2
import lxml.etree
import qrcode
import qrcode.image.svg

label_loader = jinja2.PackageLoader("invent", "labels")
label_env = jinja2.Environment(
    loader=label_loader)

def svg2pdf(input=None, output=None, dpi=(72, 72), wait=True,
            rsvg_convert="rsvg-convert"):
    argv = [rsvg_convert, "-f", "pdf"]
    if dpi:
        dpix, dpiy = dpi
        argv.extend(["-d", str(dpix), "-p", str(dpiy)])
    kwargs = {}
    if isinstance(output, str):
        argv.extend(["-o", output])
        kwargs["stdout"] = subprocess.DEVNULL
    elif output is None:
        kwargs["stdout"] = subprocess.PIPE
    else:
        kwargs["stdout"] = output
    if isinstance(input, str):
        argv.append(input)
        kwargs["stdin"] = subprocess.DEVNULL
    elif isinstance(input, bytes):
        kwargs["input"] = input
    else:
        kwargs["stdin"] = input
    return subprocess.run(argv, **kwargs, check=True)

class LabelType(object):
    def generate_for_item(self, item, attributes={}, output=None):
        attributes = dict(attributes)
        attributes["title"] = item.title
        if item.owner:
            attributes["owner"] = item.owner
        if item.inventory_number:
            attributes["inventory_number"] = item.inventory_number
        if item.realm_name:
            attributes["realm_name"] = item.realm_name
        if item.realm_prefix:
            attributes["realm_prefix"] = item.realm_prefix
        attributes["updated_at"] = item.updated_at
        return self.generate(attributes, output=output)

    def generate(self, attributes, output=None):
        attributes = dict(attributes)
        for attr, type in self.attributes:
            if attr in attributes:
                attributes[attr] = type(attributes[attr])
        return self._generate(attributes, output=output)

    def __call__(self, **attributes):
        self.generate(attributes)

    def _generate(self, attributes, output=None):
        raise NotImplementedError()

class LabelSimple62x29(LabelType):
    type = "simple-62x29"
    media_type = "application/pdf"
    attributes = [("generate_qrcode", bool),
        ("title", str),
        ("owner", str),
        ("inventory_number", str),
        ("realm_name", str)]
    dimensions = (62, 29, "mm")

    def _generate(self, attributes, output=None):
        generate_qrcode = attributes.get("generate_qrcode", False)
        tpl = label_env.get_template("simple-62x29.svg")
        qr = None
        if generate_qrcode and "inventory_number" in attributes:
            qr = qrcode.make(attributes["inventory_number"],
                    image_factory=qrcode.image.svg.SvgFragmentImage)
            qr = lxml.etree.tounicode(qr.get_image())
        res = svg2pdf(tpl.render(qr=qr, **attributes).encode(), output=output)
        if output is None:
            return res.stdout
        return res

class LabelSimple100x62(LabelType):
    type = "simple-100x62"
    dimensions = (100, 62, "mm")
    media_type = "application/pdf"
    attributes = [("generate_qrcode", bool),
        ("url_base", str),
        ("title", str),
        ("owner", str),
        ("maintainer", str),
        ("policy", str),
        ("inventory_number", str),
        ("realm_name", str),
        ("realm_prefix", str)]

    def _generate(self, attributes, output=None):
        generate_qrcode = attributes.get("generate_qrcode", True)
        url_base = attributes.get("url_base")
        tpl = label_env.get_template("simple-100x62.svg")
        qr = None
        if generate_qrcode and "inventory_number" in attributes:
            qr_data = attributes["inventory_number"]
            if url_base is not None:
                qr_data = urllib.parse.urljoin(url_base, qr_data)
            qr = qrcode.make(qr_data,
                    image_factory=qrcode.image.svg.SvgFragmentImage)
            qr = lxml.etree.tounicode(qr.get_image())
        res = svg2pdf(tpl.render(qr=qr, **attributes).encode(), output=output)
        if output is None:
            return res.stdout
        return res

label_simple_62x29 = LabelSimple62x29()
label_simple_100x62 = LabelSimple100x62()

label_factories = {l.type: l for l in [label_simple_62x29, label_simple_100x62]}

