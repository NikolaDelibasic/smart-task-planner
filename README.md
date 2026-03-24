# Smart Task Planner

Adaptive task planning system with predictive modeling, risk analysis, and dynamic scheduling.

---

## English

### Overview

Smart Task Planner is an adaptive web application designed to help users organize, prioritize, and optimize their daily tasks using data-driven logic.

Unlike traditional task managers, the system evolves over time by learning from user behavior and improving its predictions and planning decisions.

---

### Features

#### Task Management
- Add, delete, and complete tasks
- Define priority, deadline, and duration
- Track actual time spent
- Automatic ordering (active first, completed below)

---

#### AI Memory
- Stores completed tasks in `task_history`
- Preserves data even after deletion
- Tracks:
  - planned vs actual duration
  - deadlines
  - completion timestamps

---

#### Duration Prediction
- Uses:
  - historical data (ridge regression)
  - fallback heuristics (cold start)
- Outputs:
  - recommended duration
  - confidence level
  - MAE (mean absolute error)

---

#### Risk Analysis
- Detects:
  - overtime risk
  - late completion risk
- Based on:
  - user history
  - workload
  - deadline proximity
  - task size
- Includes feasibility checks for unrealistic tasks

---

#### Daily Planner
- Automatic scheduling system
- Supports:
  - multiple time blocks
  - custom start time
  - breaks
- Includes task splitting for large tasks

---

#### Statistics
- Based on historical data
- Metrics:
  - planning accuracy
  - productivity score
  - estimation error
- Provides behavioral insights

---

### How It Works

#### Task Prioritization
1. Priority (descending)
2. Deadline (earliest first)
3. Duration (shortest first)

---

#### Prediction Model
Ridge regression model using:
- planned duration
- priority
- deadline proximity
- weekend indicator

Fallback: rule-based estimation

---

#### Risk Model
Combines:
- historical behavior
- workload pressure
- time constraints

---

#### Scheduler
- fills available time blocks
- splits large tasks
- respects breaks

---

### Technologies

- Python (Flask)
- SQLite
- HTML / CSS (Bootstrap)
- Chart.js

---

### Installation

```bash
git clone https://github.com/NikolaDelibasic/smart-task-planner.git
cd smart-task-planner

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install flask

python -m web.app