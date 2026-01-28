import asyncio, json, os, sys, uuid
from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

load_dotenv(override=True)
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path: sys.path.insert(0, repo_root)

from user_profiler.agent import agent
from user_profiler.events import *
from user_profiler.tools import ensure_collections

KAFKA_TOPIC = "user-events"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

ensure_collections()

EVENT_MAP = {
    "ProfileCreatedEvent": ProfileCreatedEvent,
    "SearchPerformedEvent": SearchPerformedEvent,
    "AddToCartEvent": AddToCartEvent,
    "RemoveFromCartEvent": RemoveFromCartEvent,
    "PurchaseMadeEvent": PurchaseMadeEvent,
    "WishlistAddedEvent": WishlistAddedEvent,
    "ReviewSubmittedEvent": ReviewSubmittedEvent,
    "FilterAppliedEvent": FilterAppliedEvent,
    "ProfileUpdatedEvent": ProfileUpdatedEvent,
    "ReturnRefundEvent": ReturnRefundEvent
}

async def process_event(event_data: dict, runner: Runner, session_service):
    event_type = event_data.get("event_type")
    payload = event_data.get("payload", {})
    
    # We use a unique session ID for EVERY event to prevent context bloating.
    # The agent is stateless (reasoning engine); state is persisted in Qdrant.
    session_id = str(uuid.uuid4())
    user_id = "profiler_agent" 

    if event_type in EVENT_MAP:
        try:
            event_obj = EVENT_MAP[event_type](**payload)
            print(f"\n[Kafka] Received {event_type} (Session: {session_id})")
            
            # Ensure Session
            await session_service.create_session(app_name=agent.name, user_id=user_id, session_id=session_id)

            # Run Agent with Retry Logic for Rate Limits
            query_text = event_obj.model_dump_json()
            content = types.Content(role='user', parts=[types.Part(text=query_text)])
            
            max_retries = 3
            current_retry = 0
            
            while current_retry <= max_retries:
                try:
                    async for response in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                        if response.is_final_response():
                            if response.content and response.content.parts:
                                print(f"<<< Agent Output: {response.content.parts[0].text}")
                            elif response.actions and response.actions.escalate:
                                print(f"<<< Agent Error: {response.error_message}")
                            break
                    break # Success
                except Exception as e:
                    if "429" in str(e) or "Rate limit" in str(e) or "rate_limited" in str(e):
                        wait_time = 15 * (current_retry + 1)
                        print(f"⚠️ Rate Limit Hit ({e}). Retrying in {wait_time}s... (Attempt {current_retry + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        current_retry += 1
                        if current_retry > max_retries:
                            print(f"❌ Dropping event {event_type} after max retries.")
                    else:
                        raise e

        except Exception as e:
            print(f"Error processing {event_type}: {e}")
    else:
        print(f"Unknown event type: {event_type}")

async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    # Initialize Agent Infrastructure
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=agent.name,
        session_service=session_service
    )

    await consumer.start()
    print("--- Agent Listening on Kafka Topic ---")
    try:
        async for msg in consumer:
            await process_event(msg.value, runner, session_service)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())