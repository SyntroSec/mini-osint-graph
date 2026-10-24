"""mini_graph/model.py — qrafın düyünü və transformun çıxışı.

Entity-nin tipi, əsas dəyəri və əlavə property-ləri olur.
Burada eyni üç sahə adi Python obyektidir. XML yoxdur.

Eyni tip və eyni dəyər eyni düyündür. Qrafda eyni
entity təkrar düşəndə bir düyündə birləşir.
"""


class Entity:
    """Bir məlumat parçası: tip + dəyər + property-lər."""

    def __init__(self, type_name, value, properties=None, weight=100, display=""):
        self.type_name = type_name
        self.value = value
        self.properties = dict(properties or {})
        self.weight = weight
        # DisplayInformation sahəsinin mətn qarşılığı.
        self.display = display

    @property
    def id(self):
        """Qrafdakı unikal açar. Tip və dəyər birlikdə düyünü müəyyən edir."""
        return f"{self.type_name}|{self.value}"


class LinkedEntity:
    """Transformun bir nəticəsi və onu giriş entity-sinə bağlayan yazı.

    Bu yazı protokoldakı link#maltego.link.label property-sinin qarşılığıdır.
    Burada link ayrıca sahədir, çünki qrafı özümüz yığırıq.
    """

    def __init__(self, entity, link_label):
        self.entity = entity
        self.link_label = link_label


class Message:
    """UIMessage-in qarşılığı: Inform və ya PartialError."""

    def __init__(self, text, kind="Inform"):
        self.text = text
        self.kind = kind
