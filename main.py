import asyncio
import logging
from async_icq.bot import AsyncBot
from handlers import handle_message


TOKEN = '001.2762277535.2286663239:1011313001'

logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

bot = AsyncBot(token=TOKEN)


async def send_message(chat_id, text):
    try:
        await bot.send_text(chat_id, text)
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


async def check_events():
    while True:
        try:
            events = await bot.get_events()
            print(events)
            if events:
                print(f"Received {len(events)} events")
                for event in events:
                    try:
                        if isinstance(event, dict) and 'type' in event:
                            event_data = event
                        else:
                            print("Unknown event type, skipping.")
                            continue

                        print(f"Event data: {event_data}")

                        if event_data.get('type') == 'message':
                            print("Handling message event...")
                            await handle_message(event_data)
                    except Exception as e:
                        print(f"Error handling event: {e}")
        except Exception as e:
            print(f"Error getting events: {e}")

        await asyncio.sleep(5)


async def main():
    print("Checking for events...")
    while True:
        events = await bot.get_events()
        for event in events:
            if isinstance(event, dict) and 'type' in event:
                event_data = event
                await handle_message(event_data)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    asyncio.run(main())

