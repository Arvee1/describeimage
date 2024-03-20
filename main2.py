__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import replicate
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.agents import create_openai_functions_agent
from langchain.agents import AgentExecutor
from langchain_community.tools.tavily_search import TavilySearchResults
import os
from langchain.memory import ConversationBufferMemory
# from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_core.tools import Tool

# search = GoogleSearchAPIWrapper()

# search_tool = Tool(
    # name="google_search",
    # description="Search Google for recent results.",
    # func=search.run,
# )

@st.cache_resource
def create_vector():
    loader = TextLoader("model-whs-bill-23_november_2023.txt", encoding="utf8")
    docs = loader.load()
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    text_splitter = RecursiveCharacterTextSplitter(
        # Set chunk size, just to show.
        chunk_size=500,
        chunk_overlap=20,
        length_function=len,
        is_separator_regex=False,
    )
    documents = text_splitter.split_documents(docs)
    vector = Chroma.from_documents(documents, embeddings)
    return vector

vector = create_vector()
retriever = vector.as_retriever()

retriever_tool = create_retriever_tool(
    retriever,
    "ofsc_search",
    "Search for information about the OFSC. For any questions about the OFSC, you must use this tool!",
)

print("Vector Created.")

# tools = [retriever_tool, search_tool]
tools = [retriever_tool]

# Get the prompt to use - you can modify this!
prompt = hub.pull("hwchase17/openai-functions-agent")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=st.secrets["api_key"])
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Sidebar to clear chat history
def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]


def generate_llava_response(prompt_input):
    string_dialogue = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as 'Assistant'."
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            if dict_message.get("type") == "image":
                string_dialogue += "User: [Image]\\n\\n"
            else:
                string_dialogue += "User: " + dict_message["content"] + "\\n\\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\\n\\n"
    output = replicate.run(llm,
                           input={"image": uploaded_file, "prompt": prompt})
    return output


# st.set_page_config(page_title="🦙💬 Llava 2 Chatbot")
with (st.sidebar):
    st.title('🦙💬 Wazzup!!! Upload Image to assess if it is safe work site.')
    # selected_model = st.sidebar.selectbox('Choose a llava model', ['llava-13b'], key='selected_model')
    # if selected_model == 'llava-13b':
    llm = 'yorickvp/llava-13b:2facb4a474a0462c15041b78b1ad70952ea46b5ec6ad29583c0b29dbd4249591'

    temperature = 0.01
    top_p = 0.9
    max_length = value=512
    # temperature = st.sidebar.slider('temperature', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
    # top_p = st.sidebar.slider('top_p', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    # max_length = st.sidebar.slider('max_length', min_value=64, max_value=4096, value=512, step=8)

    # st.markdown('📖 Learn how to build a llava chatbot [blog](#link-to-blog)!')
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

# Ensure session state for messages if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["content"])
        else:
            st.write(message["content"])

# Text input for chat
prompt = st.text_input("Type a message:")

# Button to send the message/image
if st.button('Send'):
    if uploaded_file:
        # If an image is uploaded, store it in session_state
        st.session_state.messages.append({"role": "user", "content": uploaded_file, "type": "image"})

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    llava2_answer = generate_llava_response(st.session_state.messages)
    st.write(llava2_answer)
    result_string = ""
    for text in llava2_answer:
        result_string += text

    result_string = ("Check the Model Work Health and Safety Bill for non conformance based on this "
                     "text and identify the Part, Division and "
                     "Subdivision relating to "
                     "non conformance: ") + result_string

    chat_history = memory.buffer_as_messages
    response = agent_executor.invoke({
        "input": result_string,
        "chat_history": chat_history,
    })
    # response = str(response)
    st.write(response["output"])
