from dataclasses import dataclass, asdict


@dataclass
class PatternItem:
    pattern: str
    replace: str = ""
    ignore_case: bool = True,
    name: str | None = None

    def to_json(self):
        return asdict(self)

    @classmethod
    def from_json(cls, d):
        return cls(d.get("pattern", ""), d.get("replace", ""), d.get("ignore_case", True), d.get("name", None))