"""
nats.py
NATS message subscribers and message handlers
"""
import json
import logging
import ssl
from asyncio import get_running_loop
from nats.aio.client import (Client as NatsClient,
                             Msg)
from pyconnect.clients.kafka import (get_kafka_producer,
                                     KafkaCallback)
from pyconnect.config import (get_settings,
                              nats_sync_subject,
                              kafka_sync_topic)
from typing import Optional


logger = logging.getLogger(__name__)
nats_client = None


async def create_nats_subscribers():
    """
    Create an instance of each NATS subscriber.  Add additional subscribers as needed.
    """
    await start_sync_event_subscriber()


async def start_sync_event_subscriber():
    """
    Subscribes to EVENTS.responses NATS messages from the local LFH
    and any defined remote LFH instances.
    """
    nats_client = await get_nats_client()
    sid = await nats_client.subscribe(nats_sync_subject, cb=lfh_sync_event_handler)
    return sid


async def lfh_sync_event_handler(msg: Msg):
    """
    Callback for EVENTS.sync messages
    """
    subject = msg.subject
    reply = msg.reply
    data = msg.data.decode()
    logger.debug(f'lfh_sync_event_handler: received a message on {subject} {reply}: {data}')

    # if the message is from our local LFH, don't store in kafka
    logger.debug(f'lfh_sync_event_handler: checking LFH uuid')
    data_obj = json.loads(data)
    if (get_settings().lfh_id == data_obj['lfh_id']):
        logger.debug('lfh_sync_event_handler: detected local LFH message, not storing in kafka')
        return

    logger.debug(f'lfh_sync_event_handler: storing remote LFH message in Kafka')
    kafka_producer = get_kafka_producer()
    kafka_cb = KafkaCallback()
    await kafka_producer.produce_with_callback(kafka_sync_topic, data,
                                               on_delivery=kafka_cb.get_kafka_result)
    logger.debug(f'lfh_sync_event_handler: stored LFH message in Kafka for replay at {kafka_cb.kafka_result}')


async def get_nats_client() -> Optional[NatsClient]:
    """
    :return: a connected NATS client instance
    """
    global nats_client

    if not nats_client:
        settings = get_settings()

        ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ssl_ctx.load_verify_locations(settings.nats_rootCA_file)
        ssl_ctx.load_cert_chain(settings.nats_cert_file, settings.nats_key_file)

        nats_client = NatsClient()
        await nats_client.connect(
            servers=settings.nats_servers,
            loop=get_running_loop(),
            tls=ssl_ctx,
            allow_reconnect=settings.nats_allow_reconnect,
            max_reconnect_attempts=settings.nats_max_reconnect_attempts)

    return nats_client