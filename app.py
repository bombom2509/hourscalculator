import streamlit as st
from datetime import datetime, timedelta, time

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="Work Hours Calculator",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- HELPER FUNCTIONS ---

def format_timedelta(td: timedelta) -> str:
    """Formats a timedelta object into a 'HH hours, MM minutes' string."""
    if td is None:
        return "0h 0m"
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"

def calculate_time_difference(in_time_str: str, out_time_str: str) -> timedelta:
    """
    Calculates the difference between two time strings in 'HH:MM' format.
    Handles overnight work shifts and the '24:00' edge case for out-time.
    """
    try:
        # Define a common date for calculations
        base_date = datetime(2024, 1, 1)

        # An in-time of '24:00' is invalid, so strptime will raise an error which is caught below.
        start_datetime = datetime.combine(base_date, datetime.strptime(in_time_str, "%H:%M").time())

        # Handle '24:00' for out_time by treating it as midnight of the next day
        if out_time_str == "24:00":
            end_datetime = datetime.combine(base_date, time.min) + timedelta(days=1)
        else:
            end_datetime = datetime.combine(base_date, datetime.strptime(out_time_str, "%H:%M").time())

        # If out time is earlier than in time, assume it's the next day
        if end_datetime < start_datetime:
            end_datetime += timedelta(days=1)

        return end_datetime - start_datetime
    except (ValueError, TypeError):
        # Return zero duration if inputs are invalid or empty
        return timedelta(0)

def format_time_input(time_str: str) -> str:
    """Cleans and formats the time input string to 'HH:MM' as the user types."""
    if not time_str:
        return ""
    
    # Remove any non-digit characters and limit to 4 digits.
    digits = "".join(filter(str.isdigit, time_str))[:4]
    
    if len(digits) == 3:
        # If the first two digits represent an invalid hour (>23),
        # assume the user is typing HMM (e.g., "545") and format as "0H:MM" (05:45).
        if int(digits[:2]) > 23:
            return f"0{digits[0]}:{digits[1:]}"
        # Otherwise, assume they are typing HHM (e.g., "123") and format as "HH:M" (12:3).
        else:
            return f"{digits[:2]}:{digits[2:]}"
    elif len(digits) == 4:
        # Always format 4 digits as HH:MM.
        return f"{digits[:2]}:{digits[2:]}"
    else:
        # For 1 or 2 digits, return as is.
        return digits

def format_input_callback(day: str, field: str):
    """Callback to format time input for a given day and field (in/out)."""
    key = f"{field}_{day}"  # e.g., "in_Monday"
    if key in st.session_state:
        raw_value = st.session_state[key]
        formatted_value = format_time_input(raw_value)
        st.session_state[key] = formatted_value

def end_now_callback(day: str):
    """Callback for the 'End Now' button to set the out-time to the current time."""
    st.session_state[f"out_{day}"] = datetime.now().strftime("%H:%M")

def clear_day_callback(day: str):
    """Callback to clear the in and out times for a specific day."""
    st.session_state[f"in_{day}"] = ""
    st.session_state[f"out_{day}"] = ""

def reset_all_callback():
    """Callback to clear all time inputs for the week."""
    for day in st.session_state.days:
        st.session_state[f"in_{day}"] = ""
        st.session_state[f"out_{day}"] = ""

# --- INITIALIZE SESSION STATE ---
if 'days' not in st.session_state:
    st.session_state.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in st.session_state.days:
        st.session_state[f"in_{day}"] = ""
        st.session_state[f"out_{day}"] = ""

# --- UI LAYOUT ---

st.title("Work Hours Calculator")
st.markdown("Enter your start and end times in **HH:MM** (24-hour) format for each day.")
st.markdown("---")


total_duration = timedelta(0)
now = datetime.now()

# --- DAILY INPUTS AND CALCULATIONS ---
for day in st.session_state.days:
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1.5, 1.5, 1, 1.2, 0.8])

    with col1:
        st.write(f"**{day}**")

    with col2:
        st.text_input(
            "In Time",
            key=f"in_{day}",
            placeholder="HH:MM",
            label_visibility="collapsed",
            on_change=format_input_callback,
            args=(day, "in")
        )

    with col3:
        st.text_input(
            "Out Time",
            key=f"out_{day}",
            placeholder="HH:MM",
            label_visibility="collapsed",
            on_change=format_input_callback,
            args=(day, "out")
        )

    # --- VALIDATION AND CALCULATION LOGIC ---
    in_time = st.session_state[f"in_{day}"]
    out_time = st.session_state[f"out_{day}"]
    error_in_row = False
    
    # Validate in_time only if it's fully entered
    if in_time and len(in_time) == 5:
        try:
            if in_time == "24:00": raise ValueError
            datetime.strptime(in_time, "%H:%M")
        except ValueError:
            error_in_row = True

    # Validate out_time only if it's fully entered and in_time is valid
    if out_time and not error_in_row and len(out_time) == 5:
        try:
            if out_time != "24:00":
                datetime.strptime(out_time, "%H:%M")
        except ValueError:
            error_in_row = True

    with col4:
        # Show "End Now" button only if there's a valid start time and no end time
        if not error_in_row and in_time and not out_time:
            st.button(
                "End Now", 
                key=f"end_{day}", 
                use_container_width=True,
                on_click=end_now_callback,
                args=(day,)
            )

    daily_duration = timedelta(0)
    duration_suffix = ""
    # Case 1: Both in and out times are complete and valid.
    if not error_in_row and len(in_time) == 5 and len(out_time) == 5:
        daily_duration = calculate_time_difference(in_time, out_time)
    # Case 2: In time is valid, but out time is empty. Calculate vs current time.
    elif not error_in_row and len(in_time) == 5 and not out_time:
        current_time_str = now.strftime("%H:%M")
        daily_duration = calculate_time_difference(in_time, current_time_str)
        duration_suffix = " (so far)"
        
    total_duration += daily_duration

    with col5:
        if error_in_row:
            st.error("Not a real time", icon="❗")
        else:
            # Display daily total, styled for emphasis
            display_text = format_timedelta(daily_duration)
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px;'>{display_text}{duration_suffix}</div>",
                unsafe_allow_html=True,
            )

    with col6:
        # Daily Reset Button
        st.button(
            "Clear",
            key=f"reset_{day}",
            use_container_width=True,
            on_click=clear_day_callback,
            args=(day,)  # Pass the current day to the callback
        )

st.markdown("---")

# --- TOTALS AND GLOBAL RESET ---
col_total_label, col_total_value, col_reset_all = st.columns([2, 2, 1])

with col_total_label:
    st.header("Total Hours:")

with col_total_value:
    # Display the grand total in a larger font
    total_hours_str = format_timedelta(total_duration)
    st.header(f"`{total_hours_str}`")

with col_reset_all:
    # Global Reset Button
    st.button(
        "Reset All",
        use_container_width=True,
        on_click=reset_all_callback
    )
