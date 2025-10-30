import streamlit as st
import agent  
import time
import json
import random


st.set_page_config(
    page_title="GoodFoods AI Agent",
    page_icon="🤖",
    layout="centered"
)
st.title("GoodFoods AI Reservation Agent 🤖")
st.caption("I can help you find restaurants, check availability, and book a table.")


if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = [
        {
            "role": "assistant",
            "content": "Hi! I'm the GoodFoods AI reservation agent. Where are you thinking of eating, or what kind of food are you in the mood for?"
        }
    ]

for message in st.session_state.conversation_history:
    if message["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(message["content"])
    elif message["role"] == "assistant":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(message["content"])


if user_input := st.chat_input("What would you like to do?"):
    
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            
            current_history = st.session_state.conversation_history

            while True:
                response_data = agent.run_conversation_turn(current_history)
                
                if response_data["type"] == "final_answer":
                    final_answer = response_data["text"]
                    st.session_state.conversation_history.append(
                        {"role": "assistant", "content": final_answer}
                    )
                    st.markdown(final_answer)
                    
                    if "booking_id" in final_answer.lower():
                        st.balloons()
                        st.success("Booking Confirmed! You should receive a (mock) confirmation.")
                    
                    break # Exit the while loop
                
                elif response_data["type"] == "tool_result":
                    
                    tool_result_content = response_data["tool_result"]

        
                    if response_data["tool_name"] == "find_restaurants":
                        try:
                            result_list = json.loads(tool_result_content)
                            
                            if result_list and isinstance(result_list, list) and "name" in result_list[0]:
                                # 1. Extract *only* the names
                                name_list = [r["name"] for r in result_list]
                                name_list = name_list[:5]
                                tool_result_content = json.dumps(name_list)
                                
                                print(f"DEBUG (app.py): Processed list. Sending names to LLM: {tool_result_content}")
                            
                            elif not result_list:
                                tool_result_content = json.dumps([]) # Send empty list
                                
                        except Exception as e:
                            print(f"ERROR (app.py): Could not parse/process find_restaurants result: {e}")
                            tool_result_content = json.dumps([]) # Send empty list
                    
                    current_history.append({
                        "role": "system",
                        "content": f"history: {tool_result_content}"
                    })
             
                else:
                    st.error("Sorry, something went wrong. Please try again.")
                    break

