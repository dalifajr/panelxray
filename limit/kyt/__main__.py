import asyncio
from aiohttp import web
from kyt import *
from importlib import import_module
from kyt.modules import ALL_MODULES
import subprocess
import json

async def api_check_admin(request):
    tg_id = request.query.get("id")
    if not tg_id:
        return web.json_response({"ok": False, "error": "Missing id"}, status=400)
    
    is_admin = is_admin_user(tg_id)
    return web.json_response({"ok": True, "is_admin": is_admin})

async def api_execute(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)
        
    command = data.get("command")
    args = data.get("args", [])
    
    if not command:
        return web.json_response({"ok": False, "error": "Missing command"}, status=400)
        
    try:
        res = subprocess.run([command] + args, capture_output=True, text=True, check=False)
        return web.json_response({
            "ok": True, 
            "stdout": res.stdout, 
            "stderr": res.stderr, 
            "code": res.returncode
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def start_web_api():
    app = web.Application()
    app.router.add_get('/api/check-admin', api_check_admin)
    app.router.add_post('/api/execute', api_execute)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 1014)
    await site.start()
    logging.info("Local Web API started on 127.0.0.1:1014")

async def main():
    for module_name in ALL_MODULES:
        try:
            import_module("kyt.modules." + module_name)
        except Exception as e:
            logging.exception("Failed loading module %s: %s", module_name, e)
            continue
            
    await start_web_api()
    await bot.run_until_disconnected()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
