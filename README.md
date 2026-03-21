# Smart Task Planner

Smart Task Planner is a web application for organizing and managing daily tasks with a focus on prioritization, time estimation, and productivity tracking.

The main goal of the project is to help users better understand how they spend their time and improve planning through simple predictive logic and automated scheduling.

---

## Overview

This application allows users to create, track, and complete tasks while the system assists with:

- suggesting realistic task durations
- identifying potential risks (late completion or overtime)
- generating a daily plan based on available time

It is designed as a practical productivity tool, but also as an example of how basic algorithms and data analysis can be applied to real-world problems.

---

## Features

### Task Management
- Add, delete, and complete tasks
- Define priority, deadline, and expected duration
- Track actual time spent on each task

### Smart Recommendations
- Suggests adjusted task duration based on input data
- Provides a confidence indicator and error estimate

### Risk Analysis
- Detects possible issues such as:
  - running out of time
  - missing deadlines
- Gives simple explanations for each warning

### Daily Planner
- Automatically creates a schedule for the day
- Takes into account:
  - priority
  - deadlines
  - available working time
- Allows customization:
  - start time
  - total available minutes
  - break duration

### Statistics
- Total and completed tasks
- Planned vs actual time
- Productivity score
- Overtime and undertime tracking

---

## How It Works

Tasks are sorted using a simple prioritization strategy:

1. Higher priority first  
2. Earlier deadline first  
3. Shorter tasks first  

The system uses past task data to slightly adjust future duration estimates.  
Risk analysis is based on comparing task duration with time remaining until the deadline.

The daily planner fills the available time window and skips tasks that do not fit.

---

## Technologies Used

- Python (Flask)
- SQLite
- HTML / CSS (Bootstrap)
- Chart.js (for basic visualizations)

---

## Installation

```bash
git clone https://github.com/NikolaDelibasic/smart-task-planner.git
cd smart-task-planner

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install flask

python -m web.app
