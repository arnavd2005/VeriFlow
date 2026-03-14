# FEATURE: Smart Door Lock v1
# INTENT: A keypad-controlled door lock with alarm and pause functionality
# ASSUME: Lock bolt is Normally Closed (HIGH = locked)
# ASSUME: Door sensor is Normally Open (detects OPEN/CLOSED)
# ASSUME: Keypad debounce is handled in hardware

GLOBAL_TRANSITIONS:
    ON_EVENT(USER_ENTERS_MASTER_CODE): DO(STOP_ALL_TIMERS, CLEAR_ALARM) -> TO(IDLE_LOCKED)

STATE_LIST:
    IDLE_LOCKED       [Output: Lock_Bolt=HIGH, Alarm_LED=OFF]
    ENTRY_ALLOWED     [Output: Lock_Bolt=LOW, Alarm_LED=OFF]
    DOOR_OPEN_WAITING [Output: Lock_Bolt=LOW, Alarm_LED=OFF]
    ALARM_STATE       [Output: Lock_Bolt=HIGH, Alarm_LED=BLINK]
    PAUSED_MODE       [Output: Lock_Bolt=HIGH, Alarm_LED=BLINK]

TRANSITIONS:
    FROM(IDLE_LOCKED):
        ON_EVENT(KEYPAD_INPUT): IF (Code == VALID) -> TO(ENTRY_ALLOWED)
        ON_EVENT(KEYPAD_INPUT): IF (Code == INVALID AND Attempt_Count < 3) -> TO(IDLE_LOCKED)
        ON_EVENT(KEYPAD_INPUT): IF (Code == INVALID AND Attempt_Count >= 3) -> TO(ALARM_STATE)

    FROM(ENTRY_ALLOWED):
        ON_EVENT(SENSE_DOOR_OPEN): DO(START_TIMER: 60s) -> TO(DOOR_OPEN_WAITING)
        ON_EVENT(SENSE_DOOR_CLOSED): IF (True) -> TO(IDLE_LOCKED)

    FROM(DOOR_OPEN_WAITING):
        ON_EVENT(SENSE_DOOR_CLOSED): IF (True) -> TO(IDLE_LOCKED)
        ON_EVENT(TIMER_EXPIRED): IF (True) -> TO(ALARM_STATE)

    FROM(ALARM_STATE):
        ON_EVENT(USER_PRESSES_PAUSE): IF (True) -> TO(PAUSED_MODE)

    FROM(PAUSED_MODE):
        ON_EVENT(TIMER_EXPIRED): IF (SENSE_DOOR_OPEN == TRUE) -> TO(ALARM_STATE)
        ON_EVENT(TIMER_EXPIRED): IF (SENSE_DOOR_OPEN == FALSE) -> TO(IDLE_LOCKED)
