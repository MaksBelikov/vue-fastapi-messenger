import asyncio
from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import AbstractIncomingMessage
import json

from sqlalchemy import select

from models import UserOrm
from database import Session
from config import settings

async def add_user_to_db(id: int, username: str):
    async with Session() as db:
        existing = await db.scalar(
            select(UserOrm).filter(UserOrm.id==id)
        )
        if existing:
            return
        
        profile = UserOrm(
            id=id,
            username=username)
        db.add(profile)
        await db.commit()

async def handle_user_registered(message: AbstractIncomingMessage):
    async with message.process():
        try:
            event = json.loads(message.body.decode())
            if event["type"] == "UserRegistered":
                user_data = event["data"]
                await add_user_to_db(user_data['user_id'], user_data['username'])
                
        except Exception as e:
            print(f"Error processing message: {e}")
    

async def start_rabbitmq_consumer():
    connection = await connect_robust(host=settings.RABBIT_HOST, login=settings.RABBIT_USER, password=settings.RABBIT_PASS)
    
    async with connection:
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
        name="user_events",
        type=ExchangeType.FANOUT,
        durable=True)

        queue = await channel.declare_queue(
        name=f"MessagesService_user_events",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_user_events"
        })

        await queue.bind(exchange)
        await queue.consume(handle_user_registered) 
        await asyncio.Future()
