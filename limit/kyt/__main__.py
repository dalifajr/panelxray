from kyt import *
from importlib import import_module
from kyt.modules import ALL_MODULES

for module_name in ALL_MODULES:
        try:
                imported_module = import_module("kyt.modules." + module_name)
        except Exception as e:
                logging.exception("Failed loading module %s: %s", module_name, e)
                continue

bot.run_until_disconnected()

