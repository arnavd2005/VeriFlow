# VeriFlow
AI-driven synthesis agent that leverages a custom DSL to transform behavioral product requirements into synthesizable Verilog

# Specification Guide: The State Machine DSL (v1.0)
## Overview
This DSL (Domain Specific Language) is designed to bridge the gap between product requirements and digital logic design. It uses a declarative structure to define how a system behaves without needing to understand the underlying circuitry.

## Core Structure
Every specification must contain these three mandatory sections in order:

# GLOBAL_TRANSITIONS (The "Interrupts")

Define events that take priority over everything else. Use this for "Emergency Stops," "Master Resets," or "Master Codes."

Syntax: ON_EVENT(Input_Name): DO(Action) -> TO(New_State)

# STATE_LIST (The "Modes")

Define every distinct state the product can be in and what the hardware outputs should be during that time.

Syntax: STATE_NAME [Output_1=Level, Output_2=Level]

Rules: Use HIGH/LOW for digital pins or ON/OFF/BLINK for user-facing components.

# TRANSITIONS (The "Logic")

Define how the system moves from one state to another based on triggers.

Syntax: ```text FROM(STATE_NAME): ON_EVENT(Trigger_Name): IF (Condition) -> TO(NEW_STATE) ELSE -> TO(OTHER_STATE)


# Keywords & Reserved Terms
Keyword	Purpose	Example
TO(State)	Defines the destination state.	-> TO(ALARM_STATE)
STAY	Explicitly tells the system to remain in the current state.	IF (Error) -> STAY
DO(Action)	Commands a one-time action during a transition.	DO(START_TIMER: 10s)
ON_TIMEOUT(t)	A trigger that fires when a timer expires.	ON_TIMEOUT(5m) -> TO(IDLE)
ON_EVENT(x)	A trigger caused by an external input.	ON_EVENT(BUTTON_PRESS)
4. Design Best Practices (The "PM Rules")
Rule 1: The "Flat" Principle

For Version 1, avoid nesting states. If a door can be OPEN or CLOSED, and LOCKED or UNLOCKED, define the specific combined state: CLOSED_LOCKED.

Rule 2: Determinism (No Dead Ends)

Every event must have a result. If an event happens and you don't define a transition, the hardware will assume STAY. Always ask: "What happens if the user does X while in state Y?"

Rule 3: Output Stability (Moore Machine)

Outputs should be tied to the State, not the Transition.

Bad: "When I press the button, the light turns on."

Good: "In the ACTIVE state, the LIGHT output is HIGH." This prevents "glitches" in the physical hardware where a light might flicker during a transition.

Rule 4: Timer Ownership

A timer should be started in the transition leading into a state, and the ON_TIMEOUT should be defined inside that state.

5. Example Checklist for PMs
Before handing this to a Design Engineer, ensure:

[ ] Does every state have at least one way to exit?

[ ] Are the names of Inputs (Sensors/Buttons) consistent throughout?

[ ] Is there a "Power On" state (usually IDLE)?

[ ] Are global overrides (like a Reset) clearly defined in GLOBAL_TRANSITIONS?

# Why Comments Matter for Logic Synthesis

Here are three specific ways your # comments help me build a better circuit:

Safety & Criticality: If you comment # CRITICAL: Must trigger in <10ms, I know I cannot use a slow "debouncer" circuit on that input. I will prioritize that logic path during synthesis.

Power Management: If you comment # Intent: Save battery while waiting, I can implement "Clock Gating," which shuts down the high-speed clock in that state to save microwatts of power.

Future-Proofing: If you comment # Note: We might add a Fingerprint sensor here in v2, I will design the state machine with "spare" states so we don't have to redesign the whole chip next year.

Final Documentation Tip: The "Assumptions" Block

Add a "Header Comment" block at the very top of their DSL files. This defines the Environment Assumptions (e.g., "Assume the sensor is Normally Open" or "Assume the motor needs 500ms to spin up").
