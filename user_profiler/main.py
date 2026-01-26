from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from .agent import agent
from .events import *
import asyncio



async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")

async def main() : 
    session_service = InMemorySessionService()

    APP_NAME = agent.name
    USER_ID = "user_1"
    SESSION_ID = "session_001" # Using a fixed ID for simplicity

    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    runner = Runner(
    agent=agent, # The agent we want to run
    app_name=APP_NAME,   # Associates runs with our app
    session_service=session_service # Uses our session manager
    )

    try:

        print("--- Simulation Started ---")

        # 1. Profile Creation
        profile = ProfileCreatedEvent(
            user_id="u_100", timestamp="2026-01-21T09:00:00Z", session_id="s_1",
            age=25, gender="M", region="Tunis", status="student", device="iPhone 13"
        )
        await call_agent_async(profile.model_dump_json(), runner, USER_ID, SESSION_ID)

        # 2. Search
        search = SearchPerformedEvent(
            user_id="u_100", timestamp="2026-01-21T09:05:00Z", session_id="s_1",
            query="gaming laptop rtx 4060", filters={"brand": "Asus"}
        )
        await call_agent_async(search.model_dump_json(), runner, USER_ID, SESSION_ID)

        # 3. Add to Cart
        cart = AddToCartEvent(
            user_id="u_100", timestamp="2026-01-21T09:10:00Z", session_id="s_1",
            product_id="prod_asus_rog", quantity=1, price=3200.0, currency="TND", store_id="store_1"
        )
        await call_agent_async(cart.model_dump_json(), runner, USER_ID, SESSION_ID)

        # 4. Remove from Cart (Too expensive)
        remove = RemoveFromCartEvent(
            user_id="u_100", timestamp="2026-01-21T09:12:00Z", session_id="s_1",
            product_id="prod_asus_rog", quantity=1, price=3200.0, currency="TND", store_id="store_1"
        )
        await call_agent_async(remove.model_dump_json(), runner, USER_ID, SESSION_ID)

        # 5. Purchase (Cheaper Alternative)
        buy = PurchaseMadeEvent(
            user_id="u_100", timestamp="2026-01-21T09:20:00Z", session_id="s_1",
            order_id="o_99", product_id="prod_asus_tuf", quantity=1, price=2400.0,
            currency="TND", total_amount=2400.0, discount_applied=100.0, 
            payment_method="Visa", installment_plan=True
        )
        await call_agent_async(buy.model_dump_json(), runner, USER_ID, SESSION_ID)

    except Exception as e:
        print(f"Agent Init Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

