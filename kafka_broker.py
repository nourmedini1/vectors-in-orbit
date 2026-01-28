# kafka_broker.py
import asyncio
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Topic Definitions
TOPIC_USER_EVENTS = "user-events"       # High volume: clicks, cart, purchase
TOPIC_CATALOG_EVENTS = "catalog-events" # Low volume: product admin

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

class KafkaBroker:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.consumer_task = None
        self.outcome_tracker = None

    async def start(self):
        # Start producer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        
        # Start consumer for outcome tracking
        try:
            from search_engine.search_logging import OutcomeTracker
            self.outcome_tracker = OutcomeTracker()
            
            self.consumer = AIOKafkaConsumer(
                TOPIC_USER_EVENTS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                group_id="outcome-tracker-group",
                auto_offset_reset='latest'
            )
            await self.consumer.start()
            
            # Start background task to consume events
            self.consumer_task = asyncio.create_task(self._consume_events())
            print("[Broker] ✅ Kafka consumer started for outcome tracking")
            
        except Exception as e:
            print(f"[Broker] ⚠️ Failed to start outcome tracker consumer: {e}")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
        
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.consumer:
            await self.consumer.stop()

    async def send_event(self, event_type: str, data: dict):
        if not self.producer:
            raise Exception("Producer not started")
        
        # Routing Logic
        if event_type in ["ProductAddedEvent", "ProductUpdatedEvent"]:
            topic = TOPIC_CATALOG_EVENTS
        else:
            topic = TOPIC_USER_EVENTS

        message = {
            "event_type": event_type,
            "payload": data
        }
        
        print(f"[Broker] Sending {event_type} to topic '{topic}'")
        await self.producer.send_and_wait(topic, message)
    
    async def _consume_events(self):
        """
        Background task to consume events and update search logs with outcomes.
        """
        try:
            async for message in self.consumer:
                try:
                    event = message.value
                    event_type = event.get("event_type")
                    payload = event.get("payload", {})
                    
                    # Process event through OutcomeTracker
                    if self.outcome_tracker:
                        self.outcome_tracker.process_event(event_type, payload)
                    
                except Exception as e:
                    print(f"[Broker] ⚠️ Error processing event: {e}")
                    
        except asyncio.CancelledError:
            print("[Broker] Consumer task cancelled")
        except Exception as e:
            print(f"[Broker] Consumer error: {e}")

broker = KafkaBroker()