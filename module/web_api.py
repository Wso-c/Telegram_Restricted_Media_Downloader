class WebAPI:
    """REST resource adapter; authentication and HTTP transport stay in module.web."""

    def __init__(self, core):
        self.core = core

    def get(self, path: str, query: dict = None) -> dict:
        if path == '/api/admin/config':
            return self.core.get_config_yaml()
        if path == '/api/admin/sessions':
            return self.core.session_inventory()
        if path == '/api/admin/system':
            return self.core.system_status()
        if path == '/api/admin/forward/status':
            job_id = (query or {}).get('job_id', [''])[0]
            return self.core.get_forward_job(job_id)
        if path == '/api/admin/queue':
            return {'status': True, 'links': self.core.queue_order()}
        return {'status': False, 'e_code': '未知的管理資源。'}

    async def post(self, path: str, payload: dict) -> dict:
        if path == '/api/admin/config':
            return self.core.save_config_yaml(payload.get('config_yaml'))
        if path == '/api/admin/download/reorder':
            return await self.core.reorder_download_queue(payload.get('links'))
        if path == '/api/admin/forward':
            try:
                start_id = int(payload.get('start_id'))
                end_id = int(payload.get('end_id'))
            except (TypeError, ValueError):
                return {'status': False, 'e_code': '起始及結束訊息 ID 必須是整數。'}
            return await self.core.start_forward_job(
                origin_link=str(payload.get('origin_link') or '').strip(),
                target_link=str(payload.get('target_link') or '').strip(),
                start_id=start_id,
                end_id=end_id
            )
        return {'status': False, 'e_code': '未知的管理操作。'}
