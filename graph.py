from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, ToolCall
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic
from langchain_openai.chat_models.base import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from terminal import Terminal
from pydantic import BaseModel, Field
import ast
from pprint import pprint

# The terminal agent's output schema
class response_schema(BaseModel):
    reasoning: str = Field(description="- One or two sentences about what you have done so far to complete the task.\n- Briefly state what you plan to do next to complete the task.")
    zsh_command: str | None = Field(description="The next input to send to the terminal. Set this to None if there are no further commands to run.")
    stop: bool = Field(description="Whether to stop the terminal session. If there are more commands left to execute, set this to False. If you have completed the task, set this to True.")

    def __str__(self):
        return f"Reasoning: {self.reasoning}\n\nCommand: {self.zsh_command}"

# Define the function for the terminal agent node
def terminal_agent(state: MessagesState, model: BaseChatModel) -> MessagesState:
    print("\n=== Terminal agent ===\n")
    system_message = """You are a terminal agent that can execute commands on a MacOS operating system. To start with, you will be given a task that can be completed by executing a series of commands in a terminal. Your job is to complete the task to the best of your ability.

There is no restriction to the type of commands you can execute or the number of commands you can execute. After executing a command, you will be able to see the output and decide what to do next.

If you need additional information to complete the task, ask the user for help using the "ask_user" tool.
"""
    template = ChatPromptTemplate([
        SystemMessage(system_message),
        MessagesPlaceholder(variable_name="messages")
    ])
    chain = template | model.with_structured_output(response_schema)
    response = chain.invoke({"messages": state["messages"]})
    print(response)
    return {"messages": [AIMessage(content=str(response.model_dump()))]}

@tool
def ask_user(message: str) -> str:
    """Use this tool to ask the user for help or to provide more information."""
    # When the agent uses this tool, it will actually be routed to the respond_to_agent node.
    # So this function will never be used directly -- it just sets the type of the tool called by the agent.
    return ""

# The function for the conditional edge out of the terminal agent node
def execute_respond_or_stop(state: MessagesState) -> Literal[END, "execute_command", "respond_to_agent"]:
    last_message_content = ast.literal_eval(state["messages"][-1].content)
    
    if len(state["messages"][-1].tool_calls) > 0:
        # The only tool the agent can call is the ask_user tool.
        print(f"\nTerminal agent asked the user for help:\n\n{state['messages'][-1].tool_calls[0].args['message']}\n")
        return "respond_to_agent"
    elif last_message_content['zsh_command'] != None:
        response = input("\n=== Respond with r to respond to the terminal agent, s to stop, or anything else to execute the command. ===\n")
        match response:
            case "r":
                return "respond_to_agent"
            case "s":
                return END
            case _:
                return "execute_command"
    elif last_message_content['stop']:
        print("\nTask completed!\n")
        return END
    else:
        return "respond_to_agent"


# The function for the respond to agent node
def respond_to_agent(state: MessagesState) -> MessagesState:
    response = input("\n=== User (type your response) ===\n")
    return {"messages": [HumanMessage(content=response)]}

# The function for the execute command node
def execute_command(state: MessagesState, terminal: Terminal) -> MessagesState:
    print("=== Terminal ===\n")
    last_message = state["messages"][-1]
    last_message_content = ast.literal_eval(last_message.content)
    tool_call_id = f"call_{len(state['messages'])}"
    last_message.tool_calls.append(ToolCall(name="terminal_input", args={"command": last_message_content['zsh_command']}, id=tool_call_id))
    output = terminal.execute(last_message_content['zsh_command'])
    return {"messages": [ToolMessage(content=output, tool_call_id=tool_call_id)]}

def init_graph(model: BaseChatModel, terminal: Terminal):
    workflow = StateGraph(MessagesState)

    # Add the tools to the model
    model = model.bind_tools([ask_user])

    # Add the nodes to the graph
    workflow.add_node("terminal_agent", lambda state: terminal_agent(state, model))
    workflow.add_node("execute_command", lambda state: execute_command(state, terminal))
    workflow.add_node("respond_to_agent", respond_to_agent)

    # Add edges to the graph
    workflow.add_edge(START, "terminal_agent")
    workflow.add_conditional_edges("terminal_agent", execute_respond_or_stop)
    workflow.add_edge("execute_command", "terminal_agent")
    workflow.add_edge("respond_to_agent", "terminal_agent")

    # Compile the graph
    graph = workflow.compile(checkpointer=MemorySaver())
    return graph

class App:
    def __init__(self, model: BaseChatModel, terminal: Terminal):
        model.verbose = True
        self.graph = init_graph(model, terminal)

    def run(self, instructions: str):
        print(f"\n=== User ===\n{instructions}\n")
        return self.graph.invoke({"messages": [HumanMessage(content=instructions)]},
                                 {"configurable": {"thread_id": "1"}, "recursion_limit": 10000 })
    
    def draw_graph(self, path: str):
        img = self.graph.get_graph().draw_mermaid_png()
        with open(path, "wb") as f:
            f.write(img)
