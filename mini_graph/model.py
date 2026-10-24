"""mini_graph/model.py — a graph node and a transform output.

An entity has a type, a main value, and extra properties.
Here those three fields are ordinary Python objects. There is no XML.

The same type and the same value are the same node. When the same
entity appears again on the graph, it merges into one node.
"""

# Entity types added beside the existing maltego.* names.
# Those maltego.* strings stay in dns_transform.py and are not renamed.
IPV6_ADDRESS = "ipv6-address"
NAME_SERVER = "name-server"
TXT_RECORD = "txt-record"
SPF_RESULT = "spf-result"
DMARC_RESULT = "dmarc-result"


class Entity:
    """One piece of information: type + value + properties."""

    def __init__(self, type_name, value, properties=None, weight=100, display=""):
        self.type_name = type_name
        self.value = value
        self.properties = dict(properties or {})
        self.weight = weight
        # Text counterpart of the DisplayInformation field.
        self.display = display

    @property
    def id(self):
        """Unique key on the graph. Type and value together identify the node."""
        return f"{self.type_name}|{self.value}"


class LinkedEntity:
    """One transform result and the label that links it to the input entity.

    This label is the counterpart of the protocol property link#maltego.link.label.
    Here the link is its own field, because this package builds the graph itself.
    """

    def __init__(self, entity, link_label):
        self.entity = entity
        self.link_label = link_label


class Message:
    """Counterpart of UIMessage: Inform or PartialError."""

    def __init__(self, text, kind="Inform"):
        self.text = text
        self.kind = kind
