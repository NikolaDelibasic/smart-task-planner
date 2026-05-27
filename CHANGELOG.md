# Changelog

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