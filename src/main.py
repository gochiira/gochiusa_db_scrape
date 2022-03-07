from dataclasses import dataclass
import datetime
from typing import Dict, List, Optional
import requests
import lxml.html
import json
import re
import random
from time import sleep

"""
ごちうさDB
https://gochiusa.info
から曲データを吸い出すだけの回
"""


@dataclass
class Song:
    title: str
    url: str


class BaseScrape:
    def is_supported_page(self, url):
        if not url.startswith(self.ENDPOINT):
            raise Exception("Unsupported page")

    def get_page(self, url: str, params: Dict[str, str]):
        """リクエストしてページをパース"""
        sleep(random.randint(1, 3))
        response = requests.get(url, params)
        if response.status_code != 200:
            raise Exception(response.status_code)
        return lxml.html.fromstring(response.text)

    def parse_japan_time_in_seconds(self, time_string: str):
        """X分Y秒を X*60 + Y秒にパースする"""
        match = self.TIME_PATTERN.search(time_string)
        if match is None:
            return 0
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return minutes * 60 + seconds

    def parse_date_to_unix_time(self, date_string: str):
        """2022/02/19 を UnixTimeにパースする"""
        dt = datetime.datetime.strptime(date_string, "%Y/%m/%d")
        return int(dt.timestamp())


class EvestaLyricScrape(BaseScrape):
    ENDPOINT = "https://lyric.evesta.jp/"

    def __init__(self):
        super().__init__()

    def search(self, song_title: str) -> Optional[str]:
        """指定した曲名で検索する"""
        url = "https://lyric.evesta.jp/search.php/"
        params = {"kind": "title", "keyword": song_title, "how": 2, "do": "検索"}
        page = self.get_page(url, params)
        links = page.xpath("//a[@class='title']/@href")
        return self.ENDPOINT + links[0] if len(links) > 0 else None

    def get_lyrics(self, url: str) -> str:
        """指定されたページの歌詞を取得する"""
        page = self.get_page(url, {})
        return "\n".join(
            [
                t.strip().replace("\u3000", " ")
                for t in page.xpath("//div[@id='lyricbody']/text()")
            ]
        )


class GochiusaDatabaseScrape(BaseScrape):
    ENDPOINT = "https://gochiusa.info/"
    TIME_PATTERN = re.compile(r"(\d{1,2})分(\d{1,2})秒")
    lyric_client: Optional[EvestaLyricScrape] = None

    def __init__(self, lyrics_client: Optional[EvestaLyricScrape] = None):
        super().__init__()
        if lyrics_client:
            self.lyric_client = lyrics_client

    def get_song_info(self, url: str) -> Dict[str, str]:
        """指定したページの曲情報を読み出す"""
        self.is_supported_page(url)
        page = self.get_page(url, {})
        # タイトル
        title = page.xpath("//h1[@class='border-bottom pb-1 mb-0']")[0].text.strip()
        print(title)
        # たいとる(ひらがな)
        titleEn = page.xpath("//span[@class='small']")[0].text.strip()
        # キャラクター名
        artists = page.xpath('//h5[@class="card-title mb-2"]')
        # 声優名
        artistsReal = page.xpath('//h6[@class="card-subtitle mb-1 text-muted"]')
        # サブタイトル
        subtitle = " ".join([a.text for a in artists])
        subtitleEn = " ".join([a.text for a in artistsReal])
        # 作者(作詞/作曲/編曲)
        authors = page.xpath("//div[@class='d-inline-block']/a")
        author = authorEn = " ".join([a.text for a in authors])
        # 曲の長さ + BPM
        length_and_bpm = [
            e.text.strip() for e in page.xpath('//dd[@class="col-4 col-lg-2"]')
        ]
        length = self.parse_japan_time_in_seconds(length_and_bpm[0])
        bpm = int(length_and_bpm[1]) if length_and_bpm[1].isdecimal() else 100
        # イベントでの披露情報
        event_times = [
            e.strip().split("(")[0]
            for e in page.xpath(
                "//span[@class='d-none d-md-inline font-weight-bold']/text()"
            )
        ]
        event_times = [e for e in event_times if e != ""]
        created_time = updated_time = self.parse_date_to_unix_time("2022/02/19")
        if len(event_times) > 2:
            # 作成時刻
            created_time = self.parse_date_to_unix_time(event_times[-1])
            # 更新時刻
            updated_time = self.parse_date_to_unix_time(event_times[0])
        # 曲の説明
        # TODO: 載せれそうなものが存在しないので歌詞を別途とってくる
        description = ""
        if self.lyric_client:
            url = self.lyric_client.search(title)
            if url:
                description = self.lyric_client.get_lyrics(url)
        return {
            "title": title,
            "titleEn": titleEn,
            "subtitle": subtitle,
            "subtitleEn": subtitleEn,
            "author": author,
            "authorEn": authorEn,
            "length": length,
            "bpm": bpm,
            "createdTime": created_time,
            "updatedTime": updated_time,
            "description": description[:510],
        }

    def get_songs_from_artist_page(self, url: str) -> List[Song]:
        """
        指定したページに記載されている曲名リストを取得する
        例: https://gochiusa.info/artist/2
        """
        self.is_supported_page(url)
        page = self.get_page(url, {})
        song_elements = page.xpath(
            "//a[@class='list-group-item list-group-item-action']"
        )
        titles = [e.text.strip() for e in song_elements]
        links = [self.ENDPOINT + e.attrib["href"] for e in song_elements]
        return [Song(title, link) for title, link in zip(titles, links)]


if __name__ == "__main__":
    lyric_client = EvestaLyricScrape()
    cl = GochiusaDatabaseScrape(lyric_client)
    songs = cl.get_songs_from_artist_page("https://gochiusa.info/artist/2")
    output = [cl.get_song_info(song.url) for song in songs]
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
