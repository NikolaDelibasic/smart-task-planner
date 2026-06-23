# Smart Task Planner

Adaptive task planning web application with AI-assisted duration prediction, risk analysis, recurring tasks, daily planning, statistics, and automatic in-app notifications.

---

## Overview

Smart Task Planner is a Flask-based web application designed to help users organize, prioritize, and plan their tasks more efficiently.

Unlike a basic task manager, this system uses historical task data to improve future estimates. Completed tasks are stored in a task history dataset, allowing the application to compare planned duration with actual duration and adapt its recommendations over time.

The project combines rule-based planning, machine learning, risk analysis, daily scheduling, recurring tasks, statistics, workload analysis, and an automatic in-app notification center.

---

## Main Features

### Task Management

- Add new tasks
- Delete tasks
- Complete tasks
- Track planned duration
- Track actual duration
- Set task deadlines
- Set task priority
- View all, active, and completed tasks

---

### Priority System

The application uses a 1-5 priority scale with user-friendly labels:

| Value | Label |
|---|---|
| 1 | Critical |
| 2 | High |
| 3 | Normal |
| 4 | Low |
| 5 | Optional |

Tasks are displayed with clear priority badges instead of technical labels such as P1, P2, or P3.

---

### Smart Assistant

When adding a task, the Smart Assistant analyzes the entered task data and provides:

- Recommended task duration
- Confidence level
- Time risk
- Deadline risk
- User-friendly suggestion

The user can apply the recommended duration with the **Use Recommended** button.

---

### AI / Machine Learning

The application includes a real machine learning component.

The system stores completed tasks in `task_history` and uses them as a training dataset.

The duration prediction model uses Ridge Regression with the following features:

- Planned duration
- Priority
- Days until deadline
- Weekend deadline indicator

The target value is:

- Actual duration

The system uses a hybrid approach:

- Cold-start fallback logic when there is not enough historical data
- Ridge Regression model when enough training data is available
- Retraining after completed tasks
- AI bootstrap seed data for initial learning support

This allows the application to learn from planning mistakes and improve future duration recommendations.

---

### Risk Analysis

The system evaluates task risk based on:

- Planned duration
- Recommended duration
- Deadline proximity
- Priority
- Workload pressure
- Historical task behavior

Risk analysis includes:

- Time risk
- Deadline risk
- Overdue detection
- Due today detection
- Due soon detection
- High-risk task detection

---

### Recurring Tasks

Tasks can be configured to repeat automatically.

Supported repeat types:

- No repeat
- Daily
- Weekly
- Monthly

The user can also define a repeat interval, for example:

- Every 1 day
- Every 2 weeks
- Every 3 months

When a recurring task is completed, the system automatically creates the next pending task with a new deadline.

---

### Daily Planner

The Daily Planner helps users organize active tasks into time blocks.

Supported features:

- Multiple time blocks
- Up to 10 blocks
- Automatic task scheduling
- Priority-based ordering
- Deadline-aware ordering
- Task splitting across available time blocks
- Unscheduled task detection when there is not enough time

The planner uses task priority, deadlines, and duration to create a realistic daily schedule.

---

### Statistics

The statistics page provides insights based on completed user tasks.

It includes:

- Completed task count
- Planning accuracy
- Planned vs actual duration comparison
- Estimation error
- Completion data by priority
- Productivity-related metrics

AI bootstrap seed data is excluded from user statistics so that generated training examples do not distort real user performance.

---

### Workload Analysis

The application analyzes current workload based on:

- Active tasks
- Total planned minutes
- Urgent tasks
- High-risk tasks
- Workload utilization

The workload system helps the user recognize when the current task load may become too large or risky.

---

### Automatic In-App Notifications

The application includes an automatic in-app notification system.

Notifications are shown inside the web application while it is open.

The notification system includes:

- Notification center icon
- Unread notification counter
- In-app toast alerts
- Sound alerts
- Saved notification history in local storage
- Mark all as read
- Delete individual notifications
- Clear all notifications
- Click notification to mark it as read

Automatic notifications are generated for:

- Overdue tasks
- Tasks due today
- Tasks due soon
- High time risk
- High deadline risk

The system avoids repeatedly showing the same warning by storing shown warnings for the current day.

---

### Motivational Alerts

The notification center includes an option to enable or disable motivational alerts.

When enabled, the application can occasionally show motivational messages while the app is open.

These alerts are optional and can be controlled by the user.

---

## How It Works

### Task Ordering

Tasks are generally ordered by:

1. Status
2. Priority
3. Deadline
4. Duration

Active and important tasks are prioritized before lower-priority or completed tasks.

---

### Duration Prediction

The prediction system works in two modes:

1. Cold-start mode  
   Used when there is not enough historical task data.

2. Machine learning mode  
   Uses Ridge Regression trained on completed task history.

The model learns from differences between planned and actual duration.

---

### Risk Model

The risk system combines:

- Deadline proximity
- Duration estimate
- Priority
- Workload pressure
- Historical task behavior

It produces user-facing risk labels and suggestions.

---

### Recurring Task Logic

When a recurring task is completed:

1. The completed task is stored in history.
2. The current task is marked as completed.
3. A new task is automatically created.
4. The new task receives the next deadline based on repeat type and interval.

---

### Notification Logic

The application checks for task warnings automatically while the page is open.

To avoid spam:

- The same task warning is shown at most once per day.
- Notifications are stored in the notification center.
- Read/unread state is stored locally in the browser.

---

## Technologies

- Python
- Flask
- SQLite
- scikit-learn
- joblib
- HTML
- CSS
- Bootstrap 5
- JavaScript
- Chart.js

---

## Installation

```bash
git clone https://github.com/NikolaDelibasic/smart-task-planner.git
cd smart-task-planner

python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt

python -m web.app