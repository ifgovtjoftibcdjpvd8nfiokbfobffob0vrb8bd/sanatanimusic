import asyncio
import glob
import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Union

import requests
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from youtubesearchpython.__future__ import VideosSearch, CustomSearch

from config import YT_API_KEY, YTPROXY_URL as YTPROXY 
from AnonXMusic.utils.formatters import time_to_seconds
from AnonXMusic import LOGGER

def cookie_txt_file():
    try:
        folder_path = f"{os.getcwd()}/cookies"
        filename = f"{os.getcwd()}/cookies/logs.csv"
        txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
        if not txt_files:
            raise FileNotFoundError("No .txt files found in the specified folder.")
        cookie_txt_file = random.choice(txt_files)
        with open(filename, 'a') as file:
            file.write(f'Choosen File : {cookie_txt_file}\n')
        return f"""cookies/{str(cookie_txt_file).split("/")[-1]}"""
    except:
        return None

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def _get_video_details(self, link: str, limit: int = 20) -> Union[dict, None]:
        """Helper function to get video details with duration limit and error handling"""
        try:
            results = VideosSearch(link, limit=limit, region='IN')
            search_results = (await results.next()).get("result", [])

            for result in search_results:
                duration_str = result.get("duration", "0:00")

                # Convert duration to seconds
                try:
                    parts = duration_str.split(":")
                    duration_secs = 0
                    if len(parts) == 3:  # HH:MM:SS
                        duration_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:  # MM:SS
                        duration_secs = int(parts[0]) * 60 + int(parts[1])

                    # Skip videos longer than 1 hour
                    if duration_secs > 3600:
                        continue

                    return result

                except (ValueError, IndexError):
                    continue
            
            search = CustomSearch(query=link, searchPreferences="EgIYAw==" ,limit=1)
            for res in (await search.next()).get("result", []):
                return res

            return None

        except Exception as e:
            LOGGER(__name__).error(f"Error in _get_video_details: {str(e)}")
            return None

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]


        result = await self._get_video_details(link)
        if not result:
            raise ValueError("No suitable video found (duration > 1 hour or video unavailable)")

        title = result["title"]
        duration_min = result["duration"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]

        if str(duration_min) == "None":
            duration_sec = 0
        else:
            duration_sec = int(time_to_seconds(duration_min))

        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]
            
        result = await self._get_video_details(link)
        if not result:
            raise ValueError("No suitable video found (duration > 1 hour or video unavailable)")
        return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]

        result = await self._get_video_details(link)
        if not result:
            raise ValueError("No suitable video found (duration > 1 hour or video unavailable)")
        return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]

        result = await self._get_video_details(link)
        if not result:
            raise ValueError("No suitable video found (duration > 1 hour or video unavailable)")
        return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]

        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]

        result = await self._get_video_details(link)
        if not result:
            raise ValueError("No suitable video found (duration > 1 hour or video unavailable)")

        track_details = {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result["duration"],
            "thumb": result["thumbnails"][0]["url"].split("?")[0],
        }
        return track_details, result["id"]

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]

        try:
            results = []
            search = VideosSearch(link, limit=10)
            search_results = (await search.next()).get("result", [])

            # Filter videos longer than 1 hour
            for result in search_results:
                duration_str = result.get("duration", "0:00")
                try:
                    parts = duration_str.split(":")
                    duration_secs = 0
                    if len(parts) == 3:
                        duration_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        duration_secs = int(parts[0]) * 60 + int(parts[1])

                    if duration_secs <= 3600:
                        results.append(result)
                except (ValueError, IndexError):
                    continue

            if not results or query_type >= len(results):
                raise ValueError("No suitable videos found within duration limit")

            selected = results[query_type]
            return (
                selected["title"],
                selected["duration"],
                selected["thumbnails"][0]["url"].split("?")[0],
                selected["id"]
            )

        except Exception as e:
            LOGGER(__name__).error(f"Error in slider: {str(e)}")
            raise ValueError("Failed to fetch video details")

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            vid_id = link
            link = self.base + link
        loop = asyncio.get_running_loop()

        def create_session():
            session = requests.Session()
            session.mount('http://', HTTPAdapter())
            session.mount('https://', HTTPAdapter())
            return session

        def get_ydl_opts(output_path):
            return {
                "outtmpl": output_path,
                "quiet": True,
                "concurrent-fragments": 16,
                "http-chunk-size": 10485760, 
                "buffersize": 32768,
            }

        async def audio_dl(vid_id):
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    session = create_session()
                    res = session.get(f"{YTPROXY}/api/{vid_id}/key={YT_API_KEY}", timeout=30)
                    response = res.json()

                    if response['status'] == 'success':
                        xyz = os.path.join("downloads", f"{vid_id}.{response['ext']}")
                        if os.path.exists(xyz):
                            return xyz

                        try:
                            ydl_opts = get_ydl_opts(f"downloads/{vid_id}.{response['ext']}")
                            yt_dlp.YoutubeDL(ydl_opts).download([response['download_url']])
                            if os.path.exists(xyz):
                                return xyz
                        except Exception as e:
                            LOGGER(__name__).error(f"YouTube-DLP download error: {str(e)}")
                            if os.path.exists(xyz):
                                os.remove(xyz)
                            raise
                        
                    elif response['status'] in ['error', 'failed']:
                        LOGGER(__name__).warning(f"Proxy returned error status: {response}")
                        await asyncio.sleep(2)
                        retry_count += 1
                        continue
                    
                    else:
                        LOGGER(__name__).error(f"Unexpected proxy response: {response}")
                        return None

                except requests.exceptions.RequestException as e:
                    LOGGER(__name__).error(f"Network error: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

                except json.JSONDecodeError as e:
                    LOGGER(__name__).error(f"Invalid JSON response from proxy: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

                except Exception as e:
                    LOGGER(__name__).error(f"Unexpected error: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

            LOGGER(__name__).error(f"Max retries ({max_retries}) reached, download failed for {vid_id}")
            return None

        async def video_dl(vid_id):
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    session = create_session()
                    res = session.get(f"{YTPROXY}/api/{vid_id}/key={YT_API_KEY}", timeout=60)
                    response = res.json()

                    if response['status'] == 'success':
                        xyz = os.path.join("downloads", f"{vid_id}.mp4")
                        if os.path.exists(xyz):
                            return xyz

                        try:
                            ydl_opts = get_ydl_opts(f"downloads/{vid_id}.mp4")
                            yt_dlp.YoutubeDL(ydl_opts).download([response['video_url']])
                            if os.path.exists(xyz):
                                return xyz
                        except Exception as e:
                            LOGGER(__name__).error(f"YouTube-DLP download error: {str(e)}")
                            if os.path.exists(xyz):
                                os.remove(xyz)
                            raise
                        
                    elif response['status'] in ['error', 'failed']:
                        LOGGER(__name__).warning(f"Proxy returned error status: {response}")
                        await asyncio.sleep(2)  
                        retry_count += 1
                        continue
                    
                    else:
                        LOGGER(__name__).error(f"Unexpected proxy response: {response}")
                        return None

                except requests.exceptions.RequestException as e:
                    LOGGER(__name__).error(f"Network error: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

                except json.JSONDecodeError as e:
                    LOGGER(__name__).error(f"Invalid JSON response from proxy: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

                except Exception as e:
                    LOGGER(__name__).error(f"Unexpected error: {str(e)}")
                    await asyncio.sleep(2)
                    retry_count += 1

            LOGGER(__name__).error(f"Max retries ({max_retries}) reached, download failed for {vid_id}")
            return None

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath
        elif video:
            direct = True
            downloaded_file = await video_dl(vid_id)
        else:
            direct = True
            downloaded_file = await audio_dl(vid_id)
        return downloaded_file, direct
