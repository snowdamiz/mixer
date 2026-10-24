import json
import sys
from html.parser import HTMLParser


class Inspection(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


inspection = Inspection()
inspection.feed(sys.stdin.read())
print(json.dumps({"tags": inspection.tags, "attributes": inspection.attributes}))
