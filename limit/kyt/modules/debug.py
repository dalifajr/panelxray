from kyt import *

@bot.on(events.NewMessage())
async def debug_all_messages(event):
    sender = await event.get_sender()
    sender_id = getattr(sender, 'id', event.sender_id)
    text = event.raw_text
    logging.info("[DEBUG-ALL] Received message from %s: %r", sender_id, text)
