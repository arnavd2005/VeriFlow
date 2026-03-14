import os
import sys
import json
import argparse
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Import the classes from our original script
from digital_design_agent import StateMachine, DSLParser, Validator


def parse_and_validate(dsl_file_path: str):
    """Parse and validate the DSL file. Returns (state_machine, critiques)."""
    try:
        with open(dsl_file_path, 'r') as f:
            dsl_text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{dsl_file_path}' not found.")
        sys.exit(1)

    state_machine = StateMachine()
    parser = DSLParser(dsl_text, state_machine)
    parser.parse()

    validator = Validator(state_machine)
    critiques = validator.validate()

    return state_machine, critiques


def generate_verilog(state_machine: StateMachine, llm) -> str:
    """Send the parsed state machine JSON to the LLM and return Verilog code."""
    design_json = json.dumps(state_machine.data, indent=2)

    system_prompt = (
        "You are a Senior Digital Design Engineer specializing in RTL design.\n"
        "Given a state machine specification in JSON format (parsed from a Moore Machine DSL),\n"
        "generate clean, synthesizable Verilog code. Follow these rules:\n"
        "- Use always @(posedge clk or posedge rst) for sequential logic\n"
        "- Use always @(*) for combinational output logic (Moore machine)\n"
        "- Include proper synchronous reset logic\n"
        "- Define states as localparams\n"
        "- Output all signals defined in the state outputs\n"
        "- Add brief comments referencing the original DSL intent where useful\n"
        "- Output ONLY the Verilog code block, no extra explanation."
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate synthesizable Verilog for this state machine:\n\n{design_json}")
    ])

    return response.content


def main():
    load_dotenv()

    arg_parser = argparse.ArgumentParser(
        description='VeriFlow: Parse a DSL file, validate it, and generate Verilog via LLM.'
    )
    arg_parser.add_argument('dsl_file', help='Path to the .dsl file')
    args = arg_parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found. Set it in your environment or a .env file.")
        sys.exit(1)

    # --- Step 1: Parse and validate ---
    print(f"\n[1/3] Parsing DSL file: {args.dsl_file}")
    state_machine, critiques = parse_and_validate(args.dsl_file)

    feature = state_machine.data.get('header', {}).get('feature', 'Unknown')
    print(f"      Feature: {feature}")

    # --- Step 2: Report errors and stop if invalid ---
    if critiques:
        print("\n[!] Validation FAILED. Please fix the following errors before proceeding:\n")
        for i, critique in enumerate(critiques, 1):
            print(f"  {i}. {critique}")
        print("\nCorrect the DSL file and re-run.")
        sys.exit(1)

    print("\n[2/3] Validation PASSED. Saving state machine to state_machine.json...")
    state_machine.save()

    # --- Step 3: Generate Verilog ---
    print("\n[3/3] Sending to LLM for Verilog generation...\n")
    llm = ChatAnthropic(model="claude-sonnet-4-6", anthropic_api_key=api_key)
    verilog_code = generate_verilog(state_machine, llm)

    print("--- Generated Verilog ---\n")
    print(verilog_code)

    output_file = args.dsl_file.rsplit('.', 1)[0] + '.v'
    with open(output_file, 'w') as f:
        f.write(verilog_code)
    print(f"\n--- Verilog saved to: {output_file} ---")


if __name__ == "__main__":
    main()
