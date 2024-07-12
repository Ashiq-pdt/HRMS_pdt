<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="https://i.imgur.com/6wj0hh6.jpg" alt="Project logo"></a>
</p>

<h3 align="center">HRMAPP</h3>

<div align="center">

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![GitHub Issues](https://img.shields.io/github/issues/kylelobo/The-Documentation-Compendium.svg)](https://github.com/kylelobo/The-Documentation-Compendium/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/kylelobo/The-Documentation-Compendium.svg)](https://github.com/kylelobo/The-Documentation-Compendium/pulls)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

</div>

---

<p align="center"> Few lines describing your project.
    <br> 
</p>

## 📝 Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Deployment](#deployment)
- [Usage](#usage)
- [Built Using](#built_using)
- [TODO](../TODO.md)
- [Contributing](../CONTRIBUTING.md)
- [Authors](#authors)
- [Acknowledgments](#acknowledgement)
- [File structure](#project_tree)
- [Pages](#pages)

## 🧐 About <a name = "project_tree"></a>

erp-system/
├── project/
│   ├── __init__.py
│   ├── auth.py
│   ├── decorators.py
│   ├── helper.py
│   ├── models.py
│   ├── main.py
│   ├── token
│   ├── utils/
|   ├── employee/
│   │    ├── __init__.py
│   │    ├── models.py
│   │    ├── views.py
│   │    ├── templates/
|   ├── company/
│   │    ├── __init__.py
│   │    ├── models.py
│   │    ├── views.py
│   │    ├── templates/
│   │    ├── static/
│   ├── static/
│   │    ├── assets/
│   │    ├── img/
│   │    ├── sample/
│   │    ├── uploads/
│   ├── templates/
│   │    ├── admin/
│   │    ├── company/
│   │    ├── email/
│   │    ├── employee/
│   │    ├── errors/
│   │    ├── js/
│   │    ├── layout/
│   │    ├── security/
│
├── requirements.txt
└── README.md

## 🏁 Getting Started <a name = "getting_started"></a>

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See [deployment](#deployment) for notes on how to deploy the project on a live system.

### Prerequisites

```
Check requirements.txt present in the root folder. 
```

### Installing

```
 & 'c:\Users\POS\Desktop\hrmapp\hrmapp\venv\Scripts\python.exe' 'c:\Users\POS\.vscode\extensions\ms-python.debugpy-2024.6.0-wi\.vscode\extensions\ms-python.debugpy-2024.6.0-win32-x64\bundled\libs\debugpy\adapter/../..\debugpy\launcher' '50752' '--' '-m' 'flask' 'run' '--no-debugger'
```

<!-- And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo. -->

# Pages and their overview

<a name="pages"></a>

# HR Dashboard

## Dashboard

Analytics of company and its members along with events.

## Employees

- Employee List
- Add Employees

## Expiry Documents
Provides an overview of documents set to expire, facilitating proactive management and renewal processes.

# Attendance & Leave

## Attandance Report

Attandance report by days and employee(shows absent employee too)

## Leave Applications

Show list of leave applications in detail
Employee leave

## Pending Leave List

Employee wise leaves summary of all employees

## Leave calendar

Calendar view of all employee leaves in the organization

# Payroll & Adjustment

## Payroll Detail

Payroll view of employee monthwise or sub company wise

## WPS

SIF accounts of company or sub company monthwise

## Payroll Adjustments

List view of salary adjustments

## Reimbursement

Manages reimbursement processes, tracking and processing employee claims for expenses incurred during business activities.

## Leave Adjustments

Show list of adjustments

# Payroll Adjustment

## Time-Off Adjustment

Facilitates adjustments based on employee leave or time-off, ensuring accurate compensation calculations.

## End of Service

Handles end-of-service calculations, providing insights into benefits and settlements for employees leaving the organization.

## Loan Encashment

## Schedule & Uploads

# Scheduler & Uploads

Create various shift realeaded data.

## Shift Scheduler

Create various shift-related data

## Mass Upload

# Memo & Events

## 🎈 Usage <a name="usage"></a>

Add notes about how to use the system.

## 🚀 Deployment <a name = "deployment"></a>

Add additional notes about how to deploy this on a live system.

## ⛏️ Built Using <a name = "built_using"></a>

- [MongoDB](https://www.mongodb.com/) - Database
- [flask](https://expressjs.com/) - Server Framework
- [HTML/CSS](https://vuejs.org/) - Ui Templates
- [Celery](https://nodejs.org/en/) - Task Que

## ✍️ Authors <a name = "authors"></a>

- [@kylelobo](https://github.com/kylelobo) - Idea & Initial work

See also the list of [contributors](https://github.com/kylelobo/The-Documentation-Compendium/contributors) who participated in this project.

## 🎉 Acknowledgements <a name = "acknowledgement"></a>

- Hat tip to anyone whose code was used
- Inspiration
- References
