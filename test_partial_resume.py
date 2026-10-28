"""Offline cancellation and retry against distinct OCR output directories."""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

from config import Config
from media_download_manager import MediaDownloadManager


class FakeClient:
    def __init__(self, slow_from=2):
        self.calls = []
        self.slow_from = slow_from
        self.session = SimpleNamespace(dc_id=5)

    def is_connected(self):
        return True

    async def iter_download(self, message, *, offset, chunk_size, **kwargs):
        index = offset // chunk_size
        self.calls.append(index)
        if index >= self.slow_from:
            await asyncio.sleep(10)
        yield bytes([index]) * chunk_size


async def main():
    size = 4 * 524288
    manager = MediaDownloadManager(fast_workers=2)
    message = SimpleNamespace(id=3, media=SimpleNamespace(document=SimpleNamespace(
        id=4, dc_id=1, size=size)), file=SimpleNamespace(name="test.mp4"))
    original_cache = Config.OCR_VIDEO_FILE_CACHE_DIR
    with tempfile.TemporaryDirectory() as root:
        Config.OCR_VIDEO_FILE_CACHE_DIR = str(Path(root) / "video_cache")
        try:
            with tempfile.TemporaryDirectory() as output_a:
                first = FakeClient()
                task = asyncio.create_task(manager._multipart_download(first, message, output_a, size, chat_id=11))
                await asyncio.sleep(0.3)
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                print("Lan 1 chunks:", first.calls)
            with tempfile.TemporaryDirectory() as output_b:
                second = FakeClient(slow_from=999)
                result = await manager._multipart_download(second, message, output_b, size, chat_id=11)
                print("Lan 2 chunks:", second.calls)
                assert sorted(second.calls) == [2, 3], second.calls
                assert Path(result).read_bytes() == b"".join(bytes([i]) * 524288 for i in range(4))
                print("Resume va noi dung file: OK")
        finally:
            Config.OCR_VIDEO_FILE_CACHE_DIR = original_cache


if __name__ == "__main__":
    asyncio.run(main())
