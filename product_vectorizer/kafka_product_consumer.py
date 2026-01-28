# kafka_product_consumer.py
import asyncio, json, os, sys
from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

load_dotenv(override=True)
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path: sys.path.insert(0, repo_root)

from product_vectorizer.agent import agent
from product_vectorizer.events import *
from product_vectorizer.tools import ensure_product_collections

ensure_product_collections()
TOPICS = ["user-events", "catalog-events"]
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
CONSUMER_GROUP = "product_vectorizer_group"

EVENT_MAP = {
    "ProductAddedEvent": ProductAddedEvent, "ProductUpdatedEvent": ProductUpdatedEvent,
    "PurchaseMadeEvent": PurchaseMadeEvent, "AddToCartEvent": AddToCartEvent,
    "RemoveFromCartEvent": RemoveFromCartEvent, "ReturnRefundEvent": ReturnRefundEvent,
    "ReviewSubmittedEvent": ReviewSubmittedEvent
}

import uuid

async def process_event(event_data: dict, runner: Runner, session_service):
    event_type = event_data.get("event_type")
    payload = event_data.get("payload")
    
    if event_type in EVENT_MAP:
        try:
            event_obj = EVENT_MAP[event_type](**payload)
            # Use specific session per event to avoid context bloat eating up TPM quota
            # We don't need history between distinct product updates
            session_id = f"worker_{uuid.uuid4()}" 
            user_id = "system_agent" 
            print(f"\n[ProductConsumer] Processing {event_type}...")

            if not await session_service.get_session(app_name=agent.name, user_id=user_id, session_id=session_id):
                await session_service.create_session(app_name=agent.name, user_id=user_id, session_id=session_id)

            query_text = f"Event Received: {event_type}\nData: {event_obj.model_dump_json()}"
            content = types.Content(role='user', parts=[types.Part(text=query_text)])

            max_retries = 3
            current_retry = 0
            
            while current_retry <= max_retries:
                try:
                    async for response in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                        if response.is_final_response() and response.content and response.content.parts:
                            print(f"   >>> Agent Action: {response.content.parts[0].text}...")
                            break
                    # If successful, break the retry loop
                    break 
                except Exception as e:
                    if "429" in str(e) or "Rate limit" in str(e) or "rate_limited" in str(e):
                        wait_time = 15 * (current_retry + 1)
                        print(f"⚠️ Rate Limit Hit ({e}). Retrying in {wait_time}s... (Attempt {current_retry + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        current_retry += 1
                        if current_retry > max_retries:
                            print(f"❌ Dropping event {event_type} after max retries.")
                    else:
                        raise e # Re-raise other errors
 

        except Exception as e: print(f"[Error] Failed to process {event_type}: {e}")


async def consume():
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP, # Ensures independent consumption
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest'
    )
    
    # Initialize Agent
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)

    await consumer.start()
    print(f"--- Product Vectorizer Listening on {TOPICS} ---")
    
    try:
        async for msg in consumer:
            await process_event(msg.value, runner, session_service)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())