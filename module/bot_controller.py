class BotController:
    """Bot-facing adapter over the same downloader instance used by the Web API."""

    def __init__(self, core):
        self.core = core

    async def submit_download(self, link: str) -> dict:
        return await self.core.add_download(link)

    async def get_status(self) -> dict:
        return await self.core.snapshot()

    async def control_download(self, link: str, message_id: int, action: str) -> dict:
        return await self.core.control_download(link, message_id, action)
