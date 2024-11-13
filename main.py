from terminal import Terminal
from graph import App
from langchain_anthropic import ChatAnthropic
from langchain_openai.chat_models.base import ChatOpenAI
from langchain.globals import set_debug
import sys

# set_debug(True)

if __name__ == "__main__":
    instructions = sys.argv[1] if len(sys.argv) > 1 else "Print the first 10 Fibonacci numbers."

    # Setup terminal and model
    terminal = Terminal()
    model = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
    # model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    app = App(model, terminal)

    # Draw the graph for fun
    app.draw_graph("graph.png")

    # Run the app
    app.run(instructions)
