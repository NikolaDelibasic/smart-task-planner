# Changelog

## [1.4] - 2026-06-24

### Added

- Automatic in-app notification center
- Notification icon in the top-right corner
- Unread notification counter
- Notification inbox stored in browser local storage
- Toast alerts inside the application
- Sound alerts for notifications
- Automatic task warning checks while the app is open
- Notifications for overdue tasks
- Notifications for tasks due today
- Notifications for tasks due soon
- Notifications for high time risk
- Notifications for high deadline risk
- Mark all as read option
- Delete single notification option
- Clear all notifications option
- Click-to-mark-as-read behavior for individual notifications
- Optional motivational alerts
- Motivational alerts ON/OFF switch inside the notification center

### Improved

- Removed manual Enable Alerts button
- Removed manual Check Warnings button
- Removed old Smart Alerts card from the main page
- Removed old focus notification UI from the task list
- Simplified notification user experience
- Notifications now work automatically while the app is open
- Improved notification center usability
- Improved notification read/unread handling
- Cleaned notification-related CSS

### Fixed

- Repeated alerts being created when clicking the old Alerts Enabled button
- Notification panel closing when marking a single notification as read
- Duplicate and unused notification CSS
- Confusing notification control layout

## [1.3] - 2026-06-23

### Added

- Recurring task support
- Repeat type field for tasks
- Repeat interval field for tasks
- Daily recurring tasks
- Weekly recurring tasks
- Monthly recurring tasks
- Automatic creation of the next recurring task after completion
- Recurring task badges in the task list

### Improved

- Task form layout for recurring tasks
- Repeat interval behavior
- Active and all task list ordering
- UI consistency for recurring task labels

### Fixed

- Repeat interval input behavior when repeat type is disabled
- Recurring task form validation
- Theme styling for repeat interval controls

## [1.2] - 2026-05-27

### Added

- AI Engine for user-friendly task advice
- Ridge Regression model for task duration prediction
- Logistic Regression model for overtime and deadline risk prediction
- ML model status tracking in the database
- Risk model status tracking in the database
- P1-P5 priority system
- Priority helper module (`core/priority.py`)
- Priority dropdown in the task form
- Smart Assistant UI for recommended task duration
- `requirements.txt` for project dependencies

### Improved

- Replaced technical recommendation output with simple Smart Assistant messages
- Updated duration prediction to use hybrid cold-start and ML-based prediction
- Updated risk analysis to support ML prediction with rule-based fallback
- Updated task history to work as AI memory for model training
- Updated priority logic so P1 is the most important and P5 is the least important
- Updated task sorting to prioritize P1 tasks first
- Improved Smart Assistant styling to match the existing application theme

### Fixed

- Removed technical AI/ML details from the user-facing interface
- Removed `MAE: null` from recommendation messages
- Prevented duplicated completed-task records in `task_history`
- Fixed missing Python dependency setup for `scikit-learn` and `joblib`
- Fixed Smart Assistant color inconsistency on the main page

## [1.1] - 2026-03-24

### Added

- AI memory system (`task_history`)
- Multi-block daily planner
- Task splitting for large tasks
- Created_at tracking for tasks
- Serbian README (`README_rs.md`)

### Improved

- Risk model with feasibility detection
- Duration prediction using historical data
- UI responsiveness without full page reload
- Live workload updates

### Fixed

- Incorrect late risk for small tasks
- Workload warnings not updating dynamically
- UI color inconsistencies