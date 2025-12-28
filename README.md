# Customer Insights Dashboard – Tech Test

This project is a lightweight full-stack analytics dashboard built with FastAPI (backend) and Angular (frontend). It loads customer data from a CSV file, computes insights, and presents them visually for non-technical users.

---

##  Goal

Produce a working full-stack solution that:

1. Ingests a CSV file.  
2. Validates and normalizes the data into a clear schema.  
3. Exposes the data and derived analytics via a well-designed API.  
4. Displays data and insights in a frontend that a non-technical stakeholder can understand.  

## Context and expectation

- The "Customer Insights” dashboard is designed for internal stakeholders.  
- The dashboard must read a provided CSV dataset, validate it, analyze it, and present useful insights in the frontend UI.  

##  Tech Stack

### Backend
- Python 3.10+
- FastAPI
- Pydantic
- Pytest

### Frontend
- Angular
- ng2-charts / Chart.js
- Node.js 18+

---

## 📁 Project Structure

tech_test/
├── backend/
│ ├── app/
│ │ └── main.py
│ ├── tests/
│ └── requirements.txt
├── frontend/
│ ├── src/
│ └── angular.json
├── sample_data.csv
└── README.md