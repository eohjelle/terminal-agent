from terminal import Terminal
from graph import App
from langchain_anthropic import ChatAnthropic
from langchain_openai.chat_models.base import ChatOpenAI
from langchain.globals import set_debug

# set_debug(True)

# Setup
terminal = Terminal()
# model = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
app = App(model, terminal)

# Draw the graph for fun
app.draw_graph("graph.png")

# Run the app
instructions = "Create a file called 'fibonacci.py' that contains a function called 'fibonacci' that takes an integer n and returns the nth Fibonacci number. User this to compute the "
# instructions = "Inside a folder 'snake', implement the classic game of snake."
# instructions = "Add the first 100 numbers."
# instructions = "Print the first 10 Fibonacci numbers."
app.run(instructions)
