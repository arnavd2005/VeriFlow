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
| Keyword | Purpose | Example |
| ----------- | ----------- |----------- |
| TO(State) | Defines the destination state. | -> TO(ALARM_STATE) |

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

Example:

Input: DSL to explain the state machine specification
```

GLOBAL_TRANSITIONS: 
     ON_EVENT(USER_ENTERS_MASTER_CODE): 
           DO(STOP_ALL_TIMERS, CLEAR_ALARM) -> TO(IDLE_LOCKED)

STATE_LIST:
    IDLE_LOCKED   [Output: Lock_Bolt=HIGH, Alarm_LED=OFF]
    ENTRY_ALLOWED [Output: Lock_Bolt=LOW,  Alarm_LED=OFF]
    DOOR_OPEN_WAITING [Output: Lock_Bolt=LOW, Timer=RUNNING]
    ALARM_STATE   [Output: Lock_Bolt=HIGH, Alarm_LED=BLINK]
    PAUSED_MODE [Output: Alarm_LED=BLINK, Alarm_Logic=DISABLED]

TRANSITIONS:
    FROM(IDLE_LOCKED):
        ON_EVENT(KEYPAD_INPUT):
            IF (Code == VALID) -> TO(ENTRY_ALLOWED)
            IF (Code == INVALID AND Attempt_Count < 3) -> STAY
            IF (Code == INVALID AND Attempt_Count >= 3) -> TO(ALARM_STATE)

    FROM(ENTRY_ALLOWED):
        ON_EVENT(SENSE_DOOR_CLOSED):
            TO(IDLE_LOCKED)

    FROM(ENTRY_ALLOWED):
        ON_EVENT(SENSE_DOOR_OPEN):
            DO(START_TIMER: 60s) -> TO(DOOR_OPEN_WAITING)

    FROM(DOOR_OPEN_WAITING):
        ON_EVENT(SENSE_DOOR_CLOSED):
            DO(STOP_TIMER) -> TO(IDLE_LOCKED)

        ON_EVENT(TIMER_EXPIRED):
            TO(ALARM_STATE)

    FROM(ALARM_STATE): 
        ON_EVENT(USER_PRESSES_PAUSE):
              DO(START_TIMER: 30m) -> TO(PAUSED_MODE) FROM(PAUSED_MODE): 

         ON_TIMEOUT(30m): 
               IF (SENSE_DOOR_OPEN == TRUE): 
                       TO(ALARM_STATE)
               ELSE:
                       TO(IDLE_LOCKED)

```

Intermediate JSON representation 
```
{
  "product_name": "Smart_Lock_v1",
  "global_transitions": [
    { "event": "MASTER_CODE", "action": "STOP_TIMERS", "next_state": "IDLE" }
  ],
  "states": {
    "IDLE_LOCKED": {
      "outputs": { "bolt": "HIGH", "led": "OFF" },
      "transitions": [
        { "event": "KEYPAD_INPUT", "condition": "code==valid", "next_state": "ENTRY_ALLOWED" }
      ]
    }
  }
}

```
Output: Generated Verilog code

# Why Comments Matter for Logic Synthesis

Here are three specific ways your # comments help me build a better circuit:

Safety & Criticality: If you comment # CRITICAL: Must trigger in <10ms, I know I cannot use a slow "debouncer" circuit on that input. I will prioritize that logic path during synthesis.

Power Management: If you comment # Intent: Save battery while waiting, I can implement "Clock Gating," which shuts down the high-speed clock in that state to save microwatts of power.

Future-Proofing: If you comment # Note: We might add a Fingerprint sensor here in v2, I will design the state machine with "spare" states so we don't have to redesign the whole chip next year.

Final Documentation Tip: The "Assumptions" Block

Add a "Header Comment" block at the very top of their DSL files. This defines the Environment Assumptions (e.g., "Assume the sensor is Normally Open" or "Assume the motor needs 500ms to spin up").
