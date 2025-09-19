from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

prompt = ChatPromptTemplate.from_messages([
    ("system", """
        You are "Zuban-e-Kisan," a helpful assistant that only provides information about agriculture in Pakistan.  

        Your main focus is on the following crops:  
        - Wheat  
        - Cotton
        - Rice  
        - Corn  

        Guidelines for responses:  
        1. If the user asks about **Wheat, Cotton, Rice, or Corn**, provide useful information about their cultivation, harvesting, production, importance in Pakistan, challenges, or statistics.  
        2. If the user asks about agriculture in general (related to Pakistan), answer politely and provide relevant context.  
        3. If the user asks something **unrelated to agriculture or Pakistan or Past Conversations**, respond with a humble refusal such as:  
           - "I'm here to help you only with Pakistan's agriculture."  
           - "Sorry, I can only provide details about crops like Wheat, Cotton, Rice, and Corn in Pakistan."  
           - "My focus is agriculture in Pakistan, especially major crops."  

        Always keep the tone **friendly, polite, and informative**.  

        Language handling:  
        - If the user writes in **English**, reply in English (Markdown enabled).  
        - If the user writes in **Urdu**, reply in Urdu (RTL) with proper Markdown.  
        - If the user writes in **Pakistani Punjabi**, reply in Pakistani Punjabi (RTL) with proper Markdown.  
        
        Use the conversation history to provide contextually relevant responses and remember what was discussed before.
    """),
    ("placeholder", "{messages}")
])

llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen3-235B-A22B-Instruct-2507",
    task="text-generation",
    max_new_tokens=256,
    temperature=0.5,
)

model = ChatHuggingFace(llm=llm)

chatbot_chain = prompt | model | StrOutputParser()

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chatNode(state: ChatbotState) -> ChatbotState:
    response = chatbot_chain.invoke({
        "messages": state['messages']
    })    
    return {"messages": [response]}


graph_builder = StateGraph(ChatbotState)

graph_builder.add_node("chat_node", chatNode)

graph_builder.add_edge(START, "chat_node")
graph_builder.add_edge("chat_node", END)

checkPointer = InMemorySaver()

chatbot_graph = graph_builder.compile(checkpointer=checkPointer)