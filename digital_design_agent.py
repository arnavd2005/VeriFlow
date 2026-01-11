import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# --- Data Structures ---

# Using TypedDicts would be even better, but for a single file, this is clear enough.
State = Dict[str, Any]
StateMachineData = Dict[str, Any]

# --- 1. StateMachine Class (The "Source of Truth") ---

class StateMachine:
    """
    Holds the structured state machine data and handles JSON serialization.
    """
    def __init__(self, file_path: str = 'state_machine.json'):
        self.file_path = Path(file_path)
        self.data: StateMachineData = self._get_initial_structure()
        self.load()

    def _get_initial_structure(self) -> StateMachineData:
        return {
            "header": {},
            "assumptions": [],
            "global_transitions": [],
            "states": {},
        }

    def load(self):
        """Loads state machine from the JSON file if it exists."""
        if self.file_path.exists():
            try:
                self.data = json.loads(self.file_path.read_text())
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.file_path}, starting fresh.")
                self.data = self._get_initial_structure()
        else:
            self.data = self._get_initial_structure()

    def save(self):
        """Saves the current state machine to the JSON file."""
        self.file_path.write_text(json.dumps(self.data, indent=2))
        print(f"Agent > State machine saved to {self.file_path}")

    def get_all_defined_states(self) -> Set[str]:
        """Returns a set of all state names defined in STATE_LIST."""
        return set(self.data.get('states', {}).keys())

    def get_all_target_states(self) -> Set[str]:
        """Returns a set of all states that are targets of a transition."""
        targets = set()
        
        # Global transitions
        for trans in self.data.get('global_transitions', []):
            if 'target' in trans:
                targets.add(trans['target'])

        # State-specific transitions
        for state_data in self.data.get('states', {}).values():
            for trans in state_data.get('transitions', []):
                if 'target' in trans:
                    targets.add(trans['target'])
        return targets

# --- 2. DSL Parser Class ---

class DSLParser:
    """Parses the complex, multi-section DSL into a StateMachine object."""
    def __init__(self, dsl_text: str, state_machine: StateMachine):
        self.lines = dsl_text.strip().split('\n')
        self.sm = state_machine
        self.current_section = None
        self.current_from_state = None

    def parse(self):
        """Main parsing loop."""
        for line in self.lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('#'):
                self._parse_header(line)
                continue

            if self._is_section_header(line):
                self._set_section(line)
                continue
            
            self._parse_line_in_section(line)

    def _parse_header(self, line: str):
        match = re.match(r'#\s*FEATURE:\s*(.*)', line, re.IGNORECASE)
        if match:
            self.sm.data['header']['feature'] = match.group(1).strip()
        match = re.match(r'#\s*INTENT:\s*(.*)', line, re.IGNORECASE)
        if match:
            self.sm.data['header']['intent'] = match.group(1).strip()
        match = re.match(r'#\s*ASSUME:\s*(.*)', line, re.IGNORECASE) # Custom for assumptions
        if match:
            self.sm.data['assumptions'].append(match.group(1).strip())


    def _is_section_header(self, line: str) -> bool:
        return line.upper().startswith(('GLOBAL_TRANSITIONS:', 'STATE_LIST:', 'TRANSITIONS:'))

    def _set_section(self, line: str):
        self.current_section = line.upper().split(':')[0]
        self.current_from_state = None # Reset when section changes

    def _parse_line_in_section(self, line: str):
        if self.current_section == 'GLOBAL_TRANSITIONS':
            self._parse_global_transition(line)
        elif self.current_section == 'STATE_LIST':
            self._parse_state_list_item(line)
        elif self.current_section == 'TRANSITIONS':
            self._parse_transitions_item(line)

    def _parse_global_transition(self, line: str):
        # ON_EVENT(USER_ENTERS_MASTER_CODE): DO(STOP_ALL_TIMERS, CLEAR_ALARM) -> TO(IDLE_LOCKED)
        pattern = r"ON_EVENT\((?P<event>\w+)\):\s*(DO\((?P<actions>.*?)\))?\s*->\s*TO\((?P<target>\w+)\)"
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            data = match.groupdict()
            actions = [a.strip() for a in data.get('actions', '').split(',') if a.strip()]
            self.sm.data['global_transitions'].append({
                "event": data['event'].upper(),
                "actions": actions,
                "target": data['target'].upper(),
                "comment": self._extract_comment(line)
            })

    def _parse_state_list_item(self, line: str):
        # IDLE_LOCKED  [Output: Bolt=HIGH] # Standard secured state
        pattern = r"(?P<state>\w+)\s*(\[Output:\s*(?P<outputs>.*?)\])?"
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            data = match.groupdict()
            state_name = data['state'].upper()
            outputs_dict = {}
            if data['outputs']:
                for part in data['outputs'].split(','):
                    key_val = part.split('=')
                    if len(key_val) == 2:
                        outputs_dict[key_val[0].strip()] = key_val[1].strip()
            
            if state_name not in self.sm.data['states']:
                self.sm.data['states'][state_name] = {}
            
            self.sm.data['states'][state_name].update({
                "outputs": outputs_dict,
                "comment": self._extract_comment(line),
                "transitions": []
            })

    def _parse_transitions_item(self, line: str):
        # FROM(IDLE_LOCKED):
        from_match = re.match(r"FROM\((?P<state>\w+)\):", line, re.IGNORECASE)
        if from_match:
            self.current_from_state = from_match.group('state').upper()
            return

        if not self.current_from_state:
            return # Skip lines until a FROM is declared

        # ON_EVENT(KEYPAD_INPUT): IF (Code == INVALID AND Attempts >= 3) -> TO(ALARM_STATE)
        pattern = r"ON_EVENT\((?P<event>\w+)\):\s*(IF\s*\((?P<condition>.*?)\))?\s*->\s*TO\((?P<target>\w+)\)"
        trans_match = re.search(pattern, line, re.IGNORECASE)
        if trans_match:
            data = trans_match.groupdict()
            transition = {
                "event": data['event'].upper(),
                "condition": data.get('condition', 'True').strip(),
                "target": data['target'].upper(),
                "comment": self._extract_comment(line)
            }
            if self.current_from_state in self.sm.data['states']:
                self.sm.data['states'][self.current_from_state]['transitions'].append(transition)

    def _extract_comment(self, line: str) -> Optional[str]:
        if '#' in line:
            return line.split('#', 1)[1].strip()
        return None

# --- 3. Validator Class (The "Critique") ---

class Validator:
    """Analyzes the state machine for errors and potential issues."""
    def __init__(self, state_machine: StateMachine):
        self.sm = state_machine
        self.critiques: List[str] = []

    def validate(self) -> List[str]:
        """Runs all validation checks."""
        self.critiques = []
        self._check_undefined_states()
        self._find_deadlocks()
        self._check_comment_hints()
        return self.critiques

    def _check_undefined_states(self):
        """Checks if all states in transitions are defined in STATE_LIST."""
        defined_states = self.sm.get_all_defined_states()
        target_states = self.sm.get_all_target_states()
        
        undefined = target_states - defined_states
        if undefined:
            self.critiques.append(
                f"Undefined State Error: The following states are used in transitions but not defined in STATE_LIST: {', '.join(undefined)}. Please define them."
            )

    def _find_deadlocks(self):
        """Finds reachable states that have no outgoing transitions."""
        defined_states = self.sm.get_all_defined_states()
        
        for state_name in defined_states:
            state_data = self.sm.data['states'][state_name]
            has_outgoing = bool(state_data.get('transitions'))
            
            if not has_outgoing:
                # Is it a global target?
                is_global_target = any(
                    t['target'] == state_name for t in self.sm.data.get('global_transitions', [])
                )
                # Is it a regular target?
                is_regular_target = any(
                    t['target'] == state_name 
                    for s in self.sm.data['states'].values() 
                    for t in s.get('transitions', [])
                )

                if is_global_target or is_regular_target:
                    self.critiques.append(
                        f"Potential Deadlock: State '{state_name}' is reachable but has no outgoing transitions. Is this an intended final state?"
                    )

    def _check_comment_hints(self):
        """Checks for special comments and provides feedback."""
        for state, data in self.sm.data['states'].items():
            comment = data.get('comment', '')
            if 'v2' in comment or 'future' in comment:
                self.critiques.append(
                    f"Future-Proofing Notice: The comment for state '{state}' ('{comment}') mentions future plans. I will keep this in mind for extensibility."
                )
            for trans in data.get('transitions', []):
                comment = trans.get('comment', '')
                if 'critical' in comment.lower():
                    self.critiques.append(
                        f"Criticality Notice: Transition from '{state}' on event '{trans['event']}' is marked as critical. I will prioritize this path."
                    )

# --- 4. Main Agent Class ---

class DigitalDesignAgent:
    """Orchestrates parsing, validation, and user interaction."""
    def __init__(self):
        self.sm = StateMachine()

    def get_identity(self) -> str:
        return "You are a Senior Digital Design Engineer. Your job is to analyze and critique a 'PM State Machine DSL' for correctness and clarity before implementation."

    def process_dsl_file(self, file_path: str) -> str:
        """Main processing logic for a given DSL file."""
        try:
            dsl_text = Path(file_path).read_text()
        except FileNotFoundError:
            return f"Error: The file '{file_path}' was not found."
        
        # 1. Parse
        parser = DSLParser(dsl_text, self.sm)
        parser.parse()
        
        # 2. Validate
        validator = Validator(self.sm)
        critiques = validator.validate()
        
        # 3. Formulate Response
        response = "I have analyzed the DSL file. Here is my assessment:\n"
        
        feature = self.sm.data.get('header', {}).get('feature', 'N/A')
        response += f"\n- **Feature:** {feature}"
        
        if not critiques:
            response += "\n- **Critique:** The design looks solid. No immediate errors or deadlocks found."
            response += "\n\nI am satisfied with this specification. I have converted it to JSON and saved it."
            self.sm.save()
        else:
            response += "\n- **Critique:** I found the following points that need your attention:\n"
            for i, critique in enumerate(critiques, 1):
                response += f"    {i}. {critique}\n"
            response += "\nPlease review these points. Once addressed, I can proceed with generating the final hardware description."
            # Don't save if there are critiques, wait for user to fix.
            
        return response

# --- 5. CLI Execution ---

def main():
    """Runs the command-line interface for the agent."""
    agent = DigitalDesignAgent()
    print("--- Senior Digital Design Engineer ---")
    print(agent.get_identity())
    print("\nPlease provide the path to the DSL file for analysis.")
    
    while True:
        try:
            file_path = input("DSL File Path > ")
            if file_path.lower() in ['exit', 'quit']:
                print("Agent > Session ended.")
                break
            
            if not file_path:
                continue

            agent_response = agent.process_dsl_file(file_path)
            print(f"\nAgent > {agent_response}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nAgent > Session ended.")
            break

if __name__ == "__main__":
    main()