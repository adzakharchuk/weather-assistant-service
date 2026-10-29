## Architecture & Design Patterns

---

A modular Python service for weather forecasting, historical persistence, and activity recommendations applying GoF Design Patterns (Adapter, Facade, Decorator, Strategy).

# Weather Assistant & Advisory Engine

A clean, modular Python application designed to retrieve, analyze, and persist weather forecast data with an intelligent recommendation engine. The project demonstrates the practical application of core Object-Oriented Design Patterns (GoF) to build maintainable, decoupled software architecture.

---

The core goal of the project is demonstrating clean separation of concerns and maintainable architecture using GoF design patterns:

* **Facade (`WeatherFacade`):** Acts as a unified entry point, orchestrating geocoding, forecast fetching, data normalization, caching, and persistence without exposing internal complexity.
* **Adapter (`WeatherAdapter`):** Normalizes heterogeneous JSON payload responses from the external Open-Meteo API into a clean internal domain model.
* **Decorator (`ForecastCacheDecorator`):** Adds transparent in-memory TTL (Time-To-Live) caching to reduce redundant network requests while preserving the core provider interface.
* **Strategy (`RecommendationStrategy`):** Decouples advisory logic into interchangeable behavioral strategies:
  * *Walking Advisor:* Evaluates walk safety based on temperature and precipitation chances.
  * *Clothing Advisor:* Suggests outfit layers matching weather severity.
  * *Rain Preparation:* Assesses precipitation risk to determine umbrella requirements.

---

## Tech Stack

* **Language:** Python 3.10+
* **External APIs:** Open-Meteo Geocoding & Weather Forecast API.
* **Database:** SQLite (persisted historical query records with parameterized queries)
* **Libraries:** `requests`


---

## Features

- **Geocoding & Forecast Integration:** Auto-resolves city coordinates and fetches hourly forecasts (temperature, precipitation probability).
- **Smart TTL Caching:** Prevents excessive HTTP calls by serving fresh cached results within a 10-minute expiry window.
- **History Storage:** Logs past queries, timestamps, coordinates, and metrics to SQLite with full SQL injection prevention.
- **Fault-Tolerant:** Comprehensive handling for HTTP timeouts, network dropouts, invalid locations, and schema drift.

---

## Getting Started

### Prerequisites

* Python 3.10 or higher
* Git

### Installation (Local Environment)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adzakharchuk/weather-assistant-service.git
   cd weather-assistant-service
   ```
2. **Install dependencies:**
   ```bash
   pip install requests
   ```
3. **Run the application:**
   ```bash
    python weather_assistant.py
   ```
## Running Experiments & Verification

To execute automated tests covering design patterns, TTL caching, database persistence, and fault tolerance:

```bash
python tests/run_experiments.py
