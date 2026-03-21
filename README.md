# Smart Task Planner

Smart Task Planner is an intelligent task management web application that helps users organize, prioritize, and optimize their daily workload using algorithmic scheduling and predictive analysis.

The system goes beyond basic task tracking by introducing AI-inspired recommendations, risk analysis, and automatic scheduling.

---

## 🚀 Key Features

### 🧠 Smart Duration Recommendation
- Predicts realistic task duration based on priority and deadline
- Continuously improves as more tasks are completed
- Displays confidence and model accuracy (MAE)

### ⚠️ Risk Analysis System
- Detects:
  - Overtime risk
  - Deadline risk
- Provides explanations for each prediction

### 📅 Automatic Daily Planner
- Generates optimal schedule for the day
- Respects:
  - task priority
  - deadlines
  - duration
- Supports:
  - custom start time
  - available work time
  - break duration
  - optional AI-based scheduling

### 📊 Productivity & Statistics
- Completion rate
- Planning accuracy
- Productivity score (0–100)
- Overtime vs undertime tracking
- Task distribution by priority

### 📈 Visual Analytics
- Planned vs Actual time chart
- Task completion trends

### 🚨 Workload Analysis
- Detects overload situations
- Shows smart warnings like:
  - “Too many tasks for today”
  - “High risk of missing deadlines”

---

## ⚙️ How It Works

The system combines rule-based scheduling with data-driven predictions:

### Task Prioritization
Tasks are sorted by:
1. Priority (descending)
2. Deadline (ascending)
3. Duration (ascending)

### Duration Prediction
A lightweight predictive model estimates realistic task duration based on historical performance.

### Risk Detection
Risk is calculated using:
- time remaining until deadline
- task duration
- priority level

### Scheduling Algorithm
The planner:
- fills available time blocks
- inserts breaks
- skips tasks that exceed daily capacity

---

## 🛠 Tech Stack

- **Backend:** Python (Flask)
- **Database:** SQLite
- **Frontend:** HTML, CSS, Bootstrap
- **Charts:** Chart.js
- **Architecture:** Modular (core / web separation)

---

## ▶️ Installation

```bash
git clone <your-repo>
cd smart-task-planner

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install flask

python -m web.app