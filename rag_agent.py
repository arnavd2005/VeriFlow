import os
import json
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_classic.agents import AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Import the classes from our original script
from digital_design_agent import StateMachine, DSLParser, Validator

# --- 1. Define the Tools ---

@tool
def analyze_dsl_and_critique(dsl_text: str) -> str:
    """
    Analyzes a given block of Digital State Machine DSL text.
    It parses the DSL, validates the design for errors (like deadlocks or
    undefined states), and provides a critique. If the design is valid,
    it saves it to 'state_machine.json'.
    The DSL should be provided as a multi-line string.
    """
    # We reuse the components we already built
    state_machine = StateMachine()
    parser = DSLParser(dsl_text, state_machine)
    parser.parse()

    validator = Validator(state_machine)
    critiques = validator.validate()

    feature = state_machine.data.get('header', {}).get('feature', 'N/A')

    if critiques:
        critique_str = "\n".join(f"- {c}" for c in critiques)
        return (
            f"Analysis of '{feature}': I found some issues that need attention:\n"
            f"{critique_str}\n"
            "The design was NOT saved. Please address the issues and submit the corrected DSL."
        )

    state_machine.save()
    return (
        f"Analysis of '{feature}': The design is valid and has been saved to state_machine.json. "
        "No critical issues found."
    )

@tool
def read_current_design() -> str:
    """
    Reads and returns the current state machine design from the 'state_machine.json' file.
    This is useful for understanding the existing logic before adding new features.
    """
    if os.path.exists('state_machine.json'):
        with open('state_machine.json', 'r') as f:
            # Use json.load and json.dumps to pretty-print it for the LLM
            try:
                design = json.load(f)
                return json.dumps(design, indent=2)
            except json.JSONDecodeError:
                return "Error: The 'state_machine.json' file is corrupted."
    return "No design currently exists."

def main():
    """Sets up and runs the LangChain RAG agent."""
    # --- 2. Initialize the "Brain" (Gemini) ---
    # Load environment variables from .env file
    load_dotenv()

    # Make sure to set your GOOGLE_API_KEY in a .env file or as an environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found. Please set it in your environment or a .env file.")
        return

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=api_key)

    # --- 3. Construct the Agent's Personality (The Prompt) ---
    system_prompt = """You are a Senior Digital Design Engineer.
        Your goal is to help Product Managers design robust state machines using a specific DSL.

        Your primary workflow is:
        1. When the user provides a new DSL design, you MUST use the 'analyze_dsl_and_critique' tool to validate it.
        2. If the tool returns errors or critiques, you must explain the technical impact of these issues to the user (e.g., 'The undefined state means the machine will crash if it tries to enter it'). Then, suggest a specific fix in the DSL.
        3. Before suggesting changes or additions, you should use the 'read_current_design' tool to understand the existing system. This prevents you from breaking previous logic.
        4. Guide the user to provide the DSL as a complete block of text. Do not accept single-line, simplified DSL like 'FROM(A)->TO(B)'.
        """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # --- 4. Assemble the Agent ---
    tools = [analyze_dsl_and_critique, read_current_design]
    agent = create_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # --- 5. Run the Agent CLI ---
    print("--- RAG Digital Design Agent ---")
    print("I can help you design and validate a state machine. Provide your DSL as text or a file path.")

    chat_history = []

    while True:
        try:
            user_input = input("PM > ")
            if user_input.lower() in ['exit', 'quit']:
                break

            if not user_input:
                continue

            # As a convenience, if the input is a valid file, read it.
            if os.path.exists(user_input):
                print(f"Agent > Reading DSL from file: {user_input}")
                with open(user_input, 'r') as f:
                    user_input = f.read()

            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })

            print(f"Agent > {response['output']}")
            chat_history.extend(response['chat_history'])

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
