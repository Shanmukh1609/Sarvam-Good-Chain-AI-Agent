import json
import requests
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import re
from cerebras.cloud.sdk import Cerebras
import tools


load_dotenv()
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
if not CEREBRAS_API_KEY: print("FATAL ERROR: CEREBRAS_API_KEY not found in .env file.")

try:
    client = Cerebras(api_key=CEREBRAS_API_KEY)
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Cerebras client: {e}")
    client = None

MODEL_NAME = "llama-3.1-8b" 

SYSTEM_PROMPT = """
You are a highly efficient, friendly, and helpful reservation agent for the GoodFoods restaurant chain.

--- AVAILABLE TOOLS ---

1. find_restaurants(locationArea: str, cuisine: str):
   - Use this to find restaurants. Arguments are optional strings.
   - returns a JSON list of restaurant names (strings).

2. check_availability(partySize: int, time: str, restaurantId: int, restaurantName: str):
   - Use this to check if a specific restaurant has a table.
   - You must provide EITHER `restaurantId` (which MUST be an integer number) OR `restaurantName` (which MUST be a string).

3. book_table(partySize: int, time: str, userName: str, userContact: str, restaurantId: int, restaurantName: str):
   - Use this to finalize a booking.
   - You must provide EITHER `restaurantId` (integer) OR `restaurantName` (string).
   - All other arguments are required strings/integers.

4. get_menu(restaurantId: int, restaurantName: str):
   - Use this if a user asks for the menu of a specific restaurant.
   - You must provide EITHER `restaurantId` (integer) OR `restaurantName` (string).
   - The menu is returned as a JSON list, sorted by price.
   - The menu will be returned as a JSON list, sorted by price (low to high).

5. find_item_in_menus(item_name: str, budget: float):
   - Use this to find a specific item* (like "Biryani") and its price.
   - The `budget` argument is optional.
   - Example: "Where can I find 'Biryani' for under Rs.200?"

--- INSTRUCTIONS FOR RESPONSE ---
# ... (JSON format rules are the same) ...
Your *ENTIRE* response MUST be a single, valid JSON object, and nothing else.
You MUST respond in one of the following two JSON formats:
1. To call a tool:
   {
     "tool_call": {
       "name": "tool_name",
       "arguments": { "arg1": "value1", "arg2": "value2" }
     }
   }
2. To send a final answer to the user:
   {
     "final_answer": "This is your spoken response to the user."
   }

3. Whenever your `final_answer` includes a list, format it using Markdown bullet points (`\\n* `).

---  NEW PRICE ACCURACY & CURRENCY RULE  ---
When presenting menu items and prices from the `get_menu` result:
1. You MUST use the exact item names and prices provided in the result. Do NOT hallucinate, guess, or change prices or items.
2. You MUST format all prices using the Indian Rupee symbol (₹) before the number. Example: ₹6.50, ₹18.00.

--- CONVERSATION RULES ---
- Greet the user first and ask how you can help.

- ITEM RULE : If the user asks for a specific *menu item* (like "spaghetti", "biryani", "burger"), you MUST use the `find_item_in_menus` tool. This is the correct tool for all specific dish requests.

- BUDGET RULE :If the user asks for "cheap" or "budget" options *in addition* to an item (like "cheap spaghetti"), add the 'budget' argument to your `find_item_in_menus` call (e.g., `budget=20`).
x
- BUDGET-ONLY RULE : If the user *only* asks for "cheap restaurants" without specifying an item, you MUST explain that you cannot search by price alone. Offer to find restaurants by cuisine or location first.

- AVAILABILITY- RULE : If the user asks for availability at a restaurant,you must call check_availability function.
 After providing the availability at a restaurant, Ask the if they want to book a table.  

- When `find_restaurants` returns a list of names, present 3-4 options.
- When the `get_menu` tool returns a `result`, you MUST present it as a clean, itemized list with prices.
- When the user refers to one of those restaurants by *name*, you will use that `restaurantName` in your subsequent tool calls.

-  UPDATED BOOKING RULE 
  If the user asks to book a table, you MUST check if you have `partySize`, `time`, `userName`, and `userContact`.
  If any of these are missing, you MUST ask for all of them.
  Example 1: "Sure, I can help with that! For how many people, at what time, and what is your name and contact information?"
  Example 2 (if you have name): "Okay, I have your name as Sai. For how many people, what time, and what's your contact info?"
  Call `book_table` when you have all four pieces of information.

-  CONFIRMATION RULE 
  When the `book_table` tool returns a `result` with a "status": "confirmed", your *only* job is to congratulate the user and present the booking details in a friendly, conversational way.
  Do NOT just repeat the JSON. Do NOT say "result".
  Example:
  {
    "final_answer": "Great! Your table is confirmed at GoodFoods - Uptown for 4 people at 8 PM. We'll see you then!"
  }
"""

def call_cerebras_llm(conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    if not client: return {"final_answer": "ERROR: Cerebras client is not initialized."}
    messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    try:
        print("DEBUG: Calling Cerebras API via SDK...")
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_to_send,
            temperature=0.4, 
            max_tokens=2048
        )

        llm_response_content = completion.choices[0].message.content
        print(f"DEBUG: LLM Raw Response:\n{llm_response_content}")

       
        cleaned_content = llm_response_content.strip()
        original_cleaned_content = cleaned_content

    
        prefixes_to_remove = ["TOOL_CALL:", "TOOL_RESULT:"]
        for prefix in prefixes_to_remove:
            cleaned_content = re.sub(f"^{re.escape(prefix)}", "", cleaned_content, flags=re.IGNORECASE).strip()
        print(f"DEBUG: Content after prefix removal:\n{cleaned_content}")

     
        json_string = None
        attempt_parse = False
        try:
            start_index_obj = cleaned_content.find('{')
            start_index_arr = cleaned_content.find('[')
            start_index = min(start_index_obj, start_index_arr) if start_index_obj != -1 and start_index_arr != -1 else max(start_index_obj, start_index_arr)

            end_index_obj = cleaned_content.rfind('}')
            end_index_arr = cleaned_content.rfind(']')
            end_index = max(end_index_obj, end_index_arr)

            if start_index != -1 and end_index != -1:
                json_string = cleaned_content[start_index : end_index + 1].strip()
                attempt_parse = True
                print(f"DEBUG: Found braces. Extracted potential JSON: {json_string}")
            elif start_index != -1 and end_index == -1:
                brace_type = cleaned_content[start_index]
                closing_brace = '}' if brace_type == '{' else ']'
                json_string = cleaned_content[start_index:] + closing_brace
                json_string = json_string.strip()
                attempt_parse = True
                print(f"DEBUG: Attempting brace correction (end): {json_string}")
            
            if attempt_parse and json_string:

                return json.loads(json_string)
            else:
                
                print("DEBUG: No JSON braces found or extraction failed. Wrapping as final answer.")
                return {"final_answer": original_cleaned_content}

        except json.JSONDecodeError as e:
  
            print(f"DEBUG: Invalid JSON after potential correction ('{json_string}'). Error: {e}. Wrapping original cleaned text.")
            return {"final_answer": original_cleaned_content}
      

    except Exception as e:
        print(f"ERROR: Cerebras SDK call failed: {e}")
        return {"final_answer": f"Sorry, I'm having trouble connecting to my brain. Error: {e}"}

def run_conversation_turn(
    conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    
    llm_response = call_cerebras_llm(conversation_history)

    if isinstance(llm_response, dict) and "tool_call" in llm_response:
        tool_call = llm_response["tool_call"]

    elif isinstance(llm_response, dict) and "name" in llm_response and "arguments" in llm_response:
        print("DEBUG (agent.py): LLM returned a direct tool call. Fixing it.")
        tool_call = {
            "name": llm_response.get("name"),
            "arguments": llm_response.get("arguments", {})
        }
    elif isinstance(llm_response, dict) and "final_answer" in llm_response:
        return {"type": "final_answer", "text": llm_response["final_answer"]}
    
   
    elif isinstance(llm_response, list):
        print("DEBUG (agent.py): LLM returned a raw list. Formatting it for UI.")
        
        try:
            if not llm_response:
                return {"type": "final_answer", "text": "I couldn't find any items for that."}

            if isinstance(llm_response[0], dict):
                # It's a menu
                formatted_list = "Here is the menu you requested:\n"
                for item in llm_response:
                    formatted_list += f"\n* {item.get('item', 'Unknown Item')}: ${item.get('price', 'N/A')}"
                formatted_list += "\n\nWhat would you like to order?"
            
            elif isinstance(llm_response[0], str):
                formatted_list = "I found these restaurants:\n"
                for name in llm_response:
                    formatted_list += f"\n* {name}"
            
            else:
                formatted_list = str(llm_response)

            return {"type": "final_answer", "text": formatted_list}
        
        except Exception as e:
            print(f"ERROR (agent.py): Failed to format raw list: {e}")
            return {"type": "final_answer", "text": "I'm sorry, I had an error formatting the results. Please try again."}
   
    else:
        print(f"ERROR: Unknown valid JSON format or None returned: {llm_response}")
        return {
            "type": "final_answer",
            "text": "Sorry, I'm not sure what to do with that information. Can you try again?"
        }


    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
    print(f"DEBUG (agent.py): LLM requested tool '{tool_name}' with args {tool_args}")


    if hasattr(tools, tool_name):
        tool_function = getattr(tools, tool_name)
        try:
            tool_result = tool_function(**tool_args)
            tool_result_str = json.dumps(tool_result)
            print(f"DEBUG (agent.py): Tool '{tool_name}' returned a result.")
            
            return {
                "type": "tool_result",
                "tool_name": tool_name,
                "tool_result": tool_result_str
            }
        except TypeError as e:
            print(f"ERROR: Tool call failed. Mismatched arguments: {e}")
            return {
                "type": "tool_result",
                "tool_name": tool_name,
                "tool_result": json.dumps({"error": f"I'm missing some information for that request. {e}"})
            }
        except Exception as e:
            print(f"ERROR: Failed to execute tool '{tool_name}': {e}")
            return {
                "type": "tool_result",
                "tool_name": tool_name,
                "tool_result": json.dumps({"error": "An unexpected error occurred."})
            }
    else:
        print(f"ERROR: LLM tried to call unknown tool: {tool_name}")
        return {
            "type": "tool_record",
            "tool_name": tool_name,
            "tool_result": json.dumps({"error": f"I don't know how to do '{tool_name}'."})
        }