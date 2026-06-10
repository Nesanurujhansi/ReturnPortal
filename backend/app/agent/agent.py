import json
import logging
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.config import settings
from app.agent.tools import (
    verify_order_tool, get_order_items_tool, calculate_return_tool,
    create_return_request_tool, upload_image_tool, get_return_status_tool
)

logger = logging.getLogger("app.agent")

SYSTEM_PROMPT = """You are the official e-commerce Return Assistant. Your job is to guide customers conversationally through returning their orders.

Return Policy Rules:
1. You must first ask for and verify the order number and email. Use verify_order_tool.
2. If order details are found, display the items to the customer and ask which item(s) they want to return and the quantity.
3. Ask for the return method: 'Refund', 'Store Credit', or 'Exchange'.
4. Ask for the return reason. IMPORTANT: If they choose 'Defective / Damaged', tell them that they MUST write down descriptive notes/comments AND upload a validation photo. If they choose exchange, they must specify the size or color they want instead.
5. Prior to creating the return, call calculate_return_tool to calculate values and fees. Inform the customer of the total summary (Refund method has a $5.99 handling fee; Store Credit/Exchange are FREE).
6. Ask for confirmation before submitting.
7. Call create_return_request_tool to submit the return and give them the Return ID and shipping tracking number.

CRITICAL RULES:
- Never hallucinate data. If information is not available, respond with: "Data not available."
- Do not perform any direct database or Shopify writes except using the provided tools.
- Guide the conversation naturally. Keep responses concise and structured.
"""

class ReturnAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.llm = None
        self.tools = [
            verify_order_tool, get_order_items_tool, calculate_return_tool,
            create_return_request_tool, upload_image_tool, get_return_status_tool
        ]
        self.tools_map = {t.name: t for t in self.tools}

        if self.api_key:
            try:
                # Initialize Gemini Model
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=self.api_key,
                    temperature=0.2
                ).bind_tools(self.tools)
                logger.info("Successfully loaded Gemini Chat model with tools.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini LLM: {e}")
        else:
            logger.warning("No GEMINI_API_KEY set. Agent will use simulated rule-based conversation engine.")

    async def run_chat(self, chat_history: List[Dict[str, str]], user_message: str) -> str:
        """Processes chat messages conversationally using Gemini with fallback options."""
        if not self.llm:
            return await self._run_simulated_agent(chat_history, user_message)

        # Build langchain message list
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        try:
            # 1. Run LLM
            response = self.llm.invoke(messages)
            
            # 2. Handle Tool Calls if any
            if response.tool_calls:
                # Create copies of tools for executing
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_obj = self.tools_map.get(tool_name)
                    
                    if tool_obj:
                        logger.info(f"Agent invoking tool: {tool_name} with {tool_args}")
                        tool_result = tool_obj.invoke(tool_args)
                        
                        # Feed the tool results back into the LLM
                        messages.append(response)
                        messages.append(AIMessage(
                            content=f"Tool {tool_name} returned: {tool_result}",
                            name=tool_name
                        ))
                
                # Re-invoke LLM with tool results
                final_response = self.llm.invoke(messages)
                return final_response.content
            
            return response.content
        except Exception as e:
            logger.error(f"Gemini agent execution error: {e}")
            return f"Excuse me, I encountered a communication error with my brains. Let's try that again. (Error: {str(e)})"

    async def _run_simulated_agent(self, chat_history: List[Dict[str, str]], user_message: str) -> str:
        """Fallback conversational rules engine if Gemini API key is missing."""
        text = user_message.lower().strip()
        
        # Simple pattern matching to guide return flows
        if "hello" in text or "hi" in text or "start" in text:
            return "Hello! I am your Return Assistant. To begin your return, please provide your **Order Number** and **Email** (e.g. 'Order #1001, customer@example.com')."
        
        if "1001" in text or "customer@example.com" in text:
            return ("Thank you! I've verified Order #1001. Here are the items in your order:\n"
                    "1. **Classic Denim Jacket** ($89.00, Quantity: 1)\n"
                    "2. **Premium Cotton Tee** ($29.00, Quantity: 2)\n\n"
                    "Which item(s) would you like to return, and would you like a **Refund** (has a $5.99 fee), **Store Credit** (FREE), or **Exchange** (FREE)?")
        
        if "jacket" in text or "denim" in text:
            return ("Got it. You wish to return the Classic Denim Jacket. "
                    "Please let me know the **reason** for your return. "
                    "(Note: If returning because it is **Damaged**, you must submit comments/notes and upload an image).")

        if "damaged" in text or "defective" in text:
            return ("Since the jacket is damaged, please describe the damage in detail, and upload an image inside the main portal. "
                    "Once done, say 'submit return' to process your request.")

        if "submit" in text or "confirm" in text or "yes" in text:
            import random
            ret_id = f"RET-{random.randint(100000, 999999)}"
            return (f"Perfect! I have processed your return request. Your return identifier is **{ret_id}**.\n\n"
                    "**Shipping Instructions:**\n"
                    "1. A prepaid USPS label has been emailed to you.\n"
                    "2. Securely box the denim jacket and attach the label.\n"
                    "3. Drop off at any local post office station.")

        return "I understand. Please let me know how I can help you with your return request. To start over, say 'hello'."
