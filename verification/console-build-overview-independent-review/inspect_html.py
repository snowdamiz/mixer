import json
import sys
from html.parser import HTMLParser


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.attributes = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data):
        self.text.append(data)


parser = Inspect()
parser.feed(sys.stdin.read())
print(json.dumps({"tags": parser.tags, "attributes": parser.attributes, "text": parser.text}))
