import json
import logging
from typing import List, Dict, Any
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.config import settings
from app.agent.agent_prompt import SYSTEM_PROMPT
from app.agent.memory import memory_store

# Import tool functions
from app.agent.agent_tools import (
    verify_order_tool,
    get_order_items_tool,
    get_return_methods_tool,
    get_return_reasons_tool,
    upload_image_guidance_tool,
    calculate_return_tool,
    get_product_variants_tool,
    create_return_request_tool,
    get_return_status_tool,
    update_return_session_details_tool
)

logger = logging.getLogger("app.agent")

class ReturnAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.llm = None
        
        # Wrap tool functions as LangChain StructuredTools
        self.tools = [
            StructuredTool.from_function(func=verify_order_tool, coroutine=verify_order_tool),
            StructuredTool.from_function(func=get_order_items_tool, coroutine=get_order_items_tool),
            StructuredTool.from_function(func=get_return_methods_tool, coroutine=get_return_methods_tool),
            StructuredTool.from_function(func=get_return_reasons_tool, coroutine=get_return_reasons_tool),
            StructuredTool.from_function(func=upload_image_guidance_tool, coroutine=upload_image_guidance_tool),
            StructuredTool.from_function(func=calculate_return_tool, coroutine=calculate_return_tool),
            StructuredTool.from_function(func=get_product_variants_tool, coroutine=get_product_variants_tool),
            StructuredTool.from_function(func=create_return_request_tool, coroutine=create_return_request_tool),
            StructuredTool.from_function(func=get_return_status_tool, coroutine=get_return_status_tool),
            StructuredTool.from_function(func=update_return_session_details_tool, coroutine=update_return_session_details_tool),
        ]
        self.tools_map = {t.name: t for t in self.tools}

        if self.api_key and "xxxx" not in self.api_key.lower():
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.1
                ).bind_tools(self.tools)
                logger.info(f"Initialized Gemini Chat model {self.model_name} with tools.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini LLM: {e}")
        else:
            logger.warning("No valid GEMINI_API_KEY set. Agent will use simulated rule-based conversation engine.")

    async def run_chat(self, session_id: str, chat_history: List[Dict[str, str]], user_message: str) -> Dict[str, Any]:
        """Processes chat messages conversationally using Gemini with session state memory & fallback options."""
        session = memory_store.get_session(session_id)
        
        # Analyze/Update session details from user message in background if plain text matches
        text = user_message.lower().strip()
        
        # Fallback simulated engine check
        if not self.llm:
            reply = await self._run_simulated_agent(session_id, session, text, user_message)
            next_action = self._determine_next_action(session)
            options = await self._get_options_for_action(session, next_action)
            return {
                "success": True,
                "reply": reply,
                "session_id": session_id,
                "next_action": next_action,
                "options": options
            }

        # Gemini Agent execution loop
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # Append context from Session memory
        memory_ctx = f"Current Session memory context (loaded from DB/cache): {json.dumps(session)}. If user specifies details, match and execute tool updates."
        messages.append(SystemMessage(content=memory_ctx))

        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        try:
            # Multi-turn tool invocation loop
            max_iterations = 5
            iteration = 0
            
            response = await self.llm.ainvoke(messages)
            
            while response.tool_calls and iteration < max_iterations:
                iteration += 1
                messages.append(response)
                
                tool_messages = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_obj = self.tools_map.get(tool_name)
                    
                    if tool_obj:
                        logger.info(f"Agent session_id={session_id} calling tool={tool_name} args={tool_args}")
                        tool_res = await tool_obj.ainvoke(tool_args)
                        
                        # Update session memory based on tool outputs
                        self._sync_memory_from_tool(session, tool_name, tool_args, tool_res)
                        
                        tool_messages.append(ToolMessage(
                            content=tool_res,
                            name=tool_name,
                            tool_call_id=tool_call["id"]
                        ))
                    else:
                        tool_messages.append(ToolMessage(
                            content=f"Error: Tool {tool_name} not found.",
                            name=tool_name,
                            tool_call_id=tool_call["id"]
                        ))
                
                messages.extend(tool_messages)
                response = await self.llm.ainvoke(messages)
            
            reply = response.content
            if isinstance(reply, list):
                parts = []
                for part in reply:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(part["text"])
                    elif isinstance(part, str):
                        parts.append(part)
                reply = "\n".join(parts)
            elif isinstance(reply, dict) and "text" in reply:
                reply = reply["text"]

            # Parse simple text replies to extract notes/quantities if LLM bypassed tools
            self._heuristically_update_memory(session, text)
            next_action = self._determine_next_action(session)
            options = await self._get_options_for_action(session, next_action)

            return {
                "success": True,
                "reply": reply,
                "session_id": session_id,
                "next_action": next_action,
                "options": options
            }
        except Exception as e:
            logger.error(f"Gemini agent run_chat error: {e}")
            # Fallback to simulated handler on error
            reply = await self._run_simulated_agent(session_id, session, text, user_message)
            next_action = self._determine_next_action(session)
            options = await self._get_options_for_action(session, next_action)
            return {
                "success": True,
                "reply": reply,
                "session_id": session_id,
                "next_action": next_action,
                "options": options
            }

    def _sync_memory_from_tool(self, session: Dict[str, Any], tool_name: str, args: Dict[str, Any], result_str: str):
        try:
            res = json.loads(result_str)
        except Exception:
            return

        if tool_name == "verify_order_tool":
            if res.get("success"):
                session["order_number"] = args.get("order_number")
                session["email"] = args.get("email")
                session["order_id"] = res.get("order_id")
        elif tool_name == "calculate_return_tool":
            if res.get("success"):
                session["selected_product"] = args.get("product_id")
                session["quantity"] = args.get("quantity")
                session["return_method"] = args.get("return_method")
                session["return_reason"] = args.get("reason")
        elif tool_name == "update_return_session_details_tool":
            if res.get("success"):
                if res.get("product_id") is not None:
                    session["selected_product"] = res["product_id"]
                if res.get("quantity") is not None:
                    session["quantity"] = res["quantity"]
                if res.get("return_method") is not None:
                    session["return_method"] = res["return_method"]
                if res.get("return_reason") is not None:
                    session["return_reason"] = res["return_reason"]
                if res.get("notes") is not None:
                    session["notes"] = res["notes"]
                if res.get("image_file_id") is not None:
                    session["image_file_id"] = res["image_file_id"]
                if res.get("exchange_variant_id") is not None:
                    session["exchange_variant"] = res["exchange_variant_id"]
        elif tool_name == "create_return_request_tool":
            pass

    def _heuristically_update_memory(self, session: Dict[str, Any], text: str):
        # Allow linking image uploaded metadata by the frontend
        if "file_id" in text or "image_file_id" in text:
            # Check for strings like file_id is xxx
            words = text.split()
            for i, w in enumerate(words):
                if ("file_id" in w or "image" in w) and i + 1 < len(words):
                    val = words[i+1].replace(":", "").replace('"', "").replace("'", "").strip()
                    if len(val) > 10:
                        session["image_file_id"] = val

    def _determine_next_action(self, session: Dict[str, Any]) -> str:
        if not session["order_number"] or not session["email"]:
            return "collect_order_details"
        if not session["selected_product"]:
            return "select_product"
        if not session["return_method"]:
            return "select_return_method"
        if not session["return_reason"]:
            return "select_return_reason"
        if session["return_method"] == "exchange" and not session["exchange_variant"]:
            return "select_exchange_variant"
        # Check if reason is damaged/defective and needs image/notes
        reason = str(session["return_reason"] or "").lower()
        if "damaged" in reason or "defective" in reason:
            if not session["notes"]:
                return "collect_notes"
            if not session["image_file_id"]:
                return "collect_image"
        return "confirm_return"

    async def _run_simulated_agent(self, session_id: str, session: Dict[str, Any], text: str, original_text: str) -> str:
        # 1. Reset / restart check
        if "reset" in text or "restart" in text or "start over" in text or "cancel" in text:
            memory_store.clear_session(session_id)
            return "Session has been reset. To begin, please provide your **Order Number** and **Email**."

        # 2. Status retrieval shortcut
        if "status" in text or "ret-" in text:
            import re
            ret_match = re.search(r"ret-\d{6}", text)
            if ret_match:
                ret_id = ret_match.group(0).upper()
                res_str = await get_return_status_tool(ret_id)
                res = json.loads(res_str)
                if res.get("success"):
                    info = res["status"]
                    return f"Your return **{ret_id}** is currently in **{info['status']}** status. Created on {info['created_at']}."
                return "Data not available."

        # 3. Order verification collect step
        if not session["order_number"] or not session["email"]:
            # Parse order number (digits or 1001/1002 format) and email format
            import re
            order_match = re.search(r"\b\d{4}\b", text)
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
            
            if order_match and email_match:
                order_num = order_match.group(0)
                email_val = email_match.group(0)
                verify_res = json.loads(await verify_order_tool(order_num, email_val))
                
                if verify_res.get("success"):
                    session["order_number"] = order_num
                    session["email"] = email_val
                    session["order_id"] = verify_res["order_id"]
                    
                    items_str = "\n".join([f"- **{i['title']}** (ID: {i['line_item_id']}, Price: ${i['price']:.2f}, Qty: {i['quantity']})" for i in json.loads(await get_order_items_tool(verify_res["order_id"]))["items"]])
                    return f"Thank you, order verified! Welcome, {verify_res['customer_name']}.\n\nItems in your order:\n{items_str}\n\nPlease let me know which product you'd like to return (e.g. jacket or tee) and the method: **Refund**, **Store Credit**, or **Exchange**."
                else:
                    return "Order not found or email does not match."
            
            return "Please provide your Order Number and Email Address (e.g. 'Order 1001, email customer@example.com') to verify."

        # 4. Item and Method selection
        if not session["selected_product"] or not session["return_method"]:
            # Check return methods
            method = None
            if "refund" in text:
                method = "refund"
            elif "credit" in text or "store credit" in text:
                method = "credit"
            elif "exchange" in text:
                method = "exchange"

            # Check items from Shopify
            items_res = json.loads(await get_order_items_tool(session["order_id"]))
            selected_item = None
            for item in items_res.get("items", []):
                title = item["title"].lower()
                if "jacket" in text and "jacket" in title:
                    selected_item = item
                elif "tee" in text and "tee" in title:
                    selected_item = item
                elif "sneaker" in text and "sneaker" in title:
                    selected_item = item
                elif item["line_item_id"] in text:
                    selected_item = item

            # If user specified something else, let's keep querying
            if selected_item:
                session["selected_product"] = selected_item["line_item_id"]
                session["quantity"] = 1 # Default qty 1
            if method:
                session["return_method"] = method

            if not session["selected_product"]:
                return "Which item from your order would you like to return? (Please mention Classic Denim Jacket or Premium Cotton Tee)."
            if not session["return_method"]:
                return f"Got it. You want to return the product. Which return option would you prefer: **Refund**, **Store Credit**, or **Exchange**?"

        # 5. Return reason select
        if not session["return_reason"]:
            reason = None
            if "damaged" in text or "defective" in text:
                reason = "Damaged Product"
            elif "wrong" in text:
                reason = "Wrong Item"
            elif "mind" in text or "change" in text:
                reason = "Changed Mind"
            elif "fit" in text or "size" in text:
                reason = "Size Didn't Fit"
            elif "misplaced" in text:
                reason = "Order Misplaced"

            if reason:
                session["return_reason"] = reason
                # check guidance
                requires_img = json.loads(await upload_image_guidance_tool(reason))["requires_image"]
                if requires_img:
                    return f"You selected '{reason}'. This reason requires a descriptive note and a verification image. Please upload a photo and describe the issue."
            else:
                return "Please provide a reason for return (e.g., Damaged Product, Wrong Item, Size Didn't Fit, Changed Mind)."

        # 6. Reason validation notes and image uploads
        reason = session["return_reason"].lower()
        if "damaged" in reason or "defective" in reason or "wrong" in reason or "misplaced" in reason:
            # Check notes
            if not session["notes"]:
                if len(text) > 8 and "damaged" not in text and "return" not in text and "confirm" not in text:
                    session["notes"] = original_text
                else:
                    return "Notes are required for this return reason. Please provide a brief description."
            
            # Check image verification if damaged/defective
            if ("damaged" in reason or "defective" in reason) and not session["image_file_id"]:
                # Check if user passed a file_id (e.g. file_id=abc)
                import re
                file_match = re.search(r"file_id[:=\s]+([a-f0-9]{24})", text)
                if file_match:
                    session["image_file_id"] = file_match.group(1)
                else:
                    return "Image is required for damaged product returns. Please upload your verification image in the Return Portal form."

        # 7. Exchange variant select
        if session["return_method"] == "exchange" and not session["exchange_variant"]:
            # Load variants list
            items_res = json.loads(await get_order_items_tool(session["order_id"]))
            sel_item = next((i for i in items_res.get("items", []) if i["line_item_id"] == session["selected_product"]), None)
            
            if sel_item:
                prod_id = sel_item["product_id"]
                variants_res = json.loads(await get_product_variants_tool(prod_id))
                variants = variants_res.get("variants", [])
                
                # Check if variant exists in input
                matched_v = None
                for v in variants:
                    v_title = v["title"].lower()
                    if v["variant_id"] in text or v_title in text:
                        matched_v = v
                        break
                
                if matched_v:
                    session["exchange_variant"] = matched_v["variant_id"]
                else:
                    v_options = "\n".join([f"- **{v['title']}** (ID: {v['variant_id']})" for v in variants])
                    return f"Please select an exchange variant from the list below:\n{v_options}"

        # 8. Confirmation and calculate summary
        # Trigger calculate first
        calc_res = json.loads(await calculate_return_tool(
            session["order_id"],
            session["selected_product"],
            session["quantity"],
            session["return_method"],
            session["return_reason"]
        ))
        
        if not calc_res.get("success", True):
            return f"Calculation failed: {calc_res.get('message')}"

        subtotal = calc_res.get("subtotal", 0.0)
        fee = calc_res.get("handling_fee", 0.0)
        total = calc_res.get("total_refund_amount", 0.0)

        # Confirm step
        if "confirm" in text or "yes" in text or "submit" in text:
            # Create return
            create_res = json.loads(await create_return_request_tool(
                session["order_id"],
                session["email"],
                session["selected_product"],
                session["quantity"],
                session["return_method"],
                session["return_reason"],
                session["notes"],
                session["image_file_id"],
                session["exchange_variant"]
            ))
            
            if create_res.get("success"):
                # Clean up session memory on success
                memory_store.clear_session(session_id)
                return f"Success! Your return request **{create_res['return_id']}** has been created. Tracking number: **{create_res['tracking_number']}** via {create_res['carrier']}."
            else:
                return f"Return submission failed: {create_res.get('detail') or create_res.get('message') or 'Unknown validation error.'}"

        summary_msg = f"Summary: Subtotal is ${subtotal:.2f}, fee is ${fee:.2f}. Total return value: ${total:.2f}."
        if session["return_method"] == "exchange":
            summary_msg = f"Summary: Swapping item value ${subtotal:.2f}."
        return f"{summary_msg}\n\nDo you want to confirm and submit this return request? Say 'confirm' to complete."

    async def _get_options_for_action(self, session: Dict[str, Any], next_action: str) -> List[str]:
        if next_action == "select_return_method":
            return ["Refund", "Store Credit", "Exchange"]
        elif next_action == "select_product":
            if session.get("order_id"):
                from app.services.shopify_service import ShopifyService
                try:
                    items = await ShopifyService.get_order_items(session["order_id"])
                    return [item["title"] for item in items]
                except Exception:
                    pass
            return []
        elif next_action == "select_return_reason":
            from app.database.mongodb import db
            if db.return_reasons is not None:
                try:
                    cursor = db.return_reasons.find({})
                    reasons = await cursor.to_list(length=20)
                    return [r["reason"] for r in reasons]
                except Exception:
                    pass
            return ["Size Didn't Fit", "Changed Mind", "Damaged Product", "Wrong Item", "Product Defective", "Order Misplaced"]
        elif next_action == "select_exchange_variant":
            if session.get("selected_product") and session.get("order_id"):
                from app.services.shopify_service import ShopifyService
                try:
                    items = await ShopifyService.get_order_items(session["order_id"])
                    selected_item = next((i for i in items if str(i["id"]) == str(session["selected_product"])), None)
                    if not selected_item:
                        selected_item = next((i for i in items if str(i.get("product_id")) == str(session["selected_product"])), None)
                    if selected_item and selected_item.get("product_id"):
                        variants = await ShopifyService.get_product_variants(str(selected_item["product_id"]))
                        return [v["title"] for v in variants if v.get("inventory_quantity", 1) > 0]
                except Exception:
                    pass
            return []
        elif next_action == "confirm_return":
            return ["Confirm", "Cancel"]
        elif next_action == "collect_quantity":
            if session.get("selected_product") and session.get("order_id"):
                from app.services.shopify_service import ShopifyService
                try:
                    items = await ShopifyService.get_order_items(session["order_id"])
                    selected_item = next((i for i in items if str(i["id"]) == str(session["selected_product"])), None)
                    if not selected_item:
                        selected_item = next((i for i in items if str(i.get("product_id")) == str(session["selected_product"])), None)
                    if selected_item:
                        max_qty = selected_item.get("quantity", 1)
                        return [str(i) for i in range(1, max_qty + 1)]
                except Exception:
                    pass
            return ["1", "2", "3"]
        return []
