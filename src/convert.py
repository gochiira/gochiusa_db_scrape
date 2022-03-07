import codecs
from dataclasses import dataclass
from typing import Any, List
import yaml
import json
import random
import pykakasi


@dataclass
class Level:
    id: int
    # display id
    name: str
    # owner id
    userId: int
    # time mixin
    createdTime: int
    updatedTime: int
    title: str
    titleEn: str
    subtitle: str
    subtitleEn: str
    author: str
    authorEn: str
    description: str
    descriptionEn: str
    public: bool
    isDeleted: bool
    rating: int
    bpm: int
    notes: int
    length: int
    cover: str
    bgm: str
    data: str
    engineId: int
    genreId: int
    publicSus: bool


@dataclass
class LevelExport:
    model: str
    id: int
    fields: Level


class ModelConverter:
    KAKASHI: pykakasi.kakasi = None
    CONVERSION: Any = None

    def __init__(self):
        self.KAKASHI = pykakasi.kakasi()
        self.KAKASHI.setMode("H", "a")
        self.CONVERSION = self.KAKASHI.getConverter()

    def convertJsonToYaml(self, json_file: str, yaml_file: str) -> None:
        levels_json: List[Level] = []
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                levels_json = json.loads(f.read())
        except IOError:
            raise Exception("Could not read json file")
        new_levels = [
            LevelExport(
                model="src.database.objects.level.Level",
                id=i,
                fields=Level(
                    id=i,
                    name=self.CONVERSION.do(level["titleEn"]),
                    userId=1,
                    createdTime=level["createdTime"],
                    updatedTime=level["updatedTime"],
                    title=level["title"],
                    titleEn=level["titleEn"],
                    subtitle=level["subtitle"],
                    subtitleEn=level["subtitleEn"],
                    author=level["author"],
                    authorEn=" ".join(
                        [
                            item["hira"]
                            for item in self.KAKASHI.convert(level["authorEn"])
                        ]
                    )[:500],
                    description=level["description"],
                    descriptionEn=" ".join(
                        [
                            item["hira"]
                            for item in self.KAKASHI.convert(level["description"])
                        ]
                    )[:500],
                    public=True,
                    isDeleted=False,
                    rating=random.randint(1, 50),
                    bpm=level["bpm"],
                    notes=random.randint(100, 1000),
                    length=level["length"],
                    cover="https://placehold.jp/32/3d4070/ffffff/300x300.png?text="
                    + level["title"],
                    bgm="https://cdn.purplepalette.net/file/potato-test/LevelBgm/more_one_night.mp3",
                    data="dummy",
                    engineId=1,
                    genreId=1,
                    publicSus=False,
                ).__dict__,
            ).__dict__
            for i, level in enumerate(levels_json)
        ]
        with codecs.open(yaml_file, "w", "utf-8") as f:
            yaml.dump(new_levels, f, encoding="utf-8", allow_unicode=True)


if __name__ == "__main__":
    cl = ModelConverter()
    cl.convertJsonToYaml("result.json", "result.yaml")
    print("Converted")
    exit(0)
