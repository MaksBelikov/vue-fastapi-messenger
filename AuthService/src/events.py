import aio_pika
import json

from config import settings

async def send_user_created_event(user_id: int, username: str | None):
    connection = await aio_pika.connect_robust(host=settings.RABBIT_HOST, login=settings.RABBIT_USER, password=settings.RABBIT_PASS)

    async with connection:
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
        name="user_events",
        type=aio_pika.ExchangeType.FANOUT,
        durable=True)

        event = {
            "type": "UserRegistered",
            "data": {
                "user_id": user_id,
                "username": username,
            }
        }   

        message = aio_pika.Message(
        body=json.dumps(event).encode('utf-8'),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        
        await exchange.publish(
        message,
        routing_key="")

        await channel.close()