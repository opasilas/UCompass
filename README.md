uCompass: Resource Management System
====================================

**uCompass** is a streamlined Python-based web application designed to bridge the gap between students, teachers, and wellbeing officers. By centralizing deadlines, educational resources, and personal task management, uCompass ensures that everyone in the academic ecosystem stays headed in the right direction.

🚀 Getting Started
------------------

### Prerequisites

*   Python 3.8 or higher
    
*   pip (Python package installer)
    

### Installation

1.  git clone https://github.com/opasilas/ucompass.git ucompass
    
2.  pip install -r requirements.txt
    
3.  python app.py The application will typically be available at http://127.0.0.1:5000


> \[!NOTE\] **No Database Setup Required:** uCompass uses a local JSON-based object store for simplicity. Data is persisted directly within the repository structure.

🔐 Access & Authentication
--------------------------

uCompass features a role-based access control system. To test the different dashboards, use the **credentials provided directly on the Login Page**.

*   **Students:** Access personalized dashboards and task tracking.
    
*   **Teachers:** Manage academic deadlines and curriculum resources.
    
*   **Wellbeing Officers:** Oversee student support resources and holistic data.
    


🛠 Features & API Endpoints
---------------------------

### User Dashboards

*   **Student Dashboard (/student\_dashboard):** View upcoming tasks and a timeline of academic health.
    
*   **Teacher Dashboard (/teacher\_dashboard):** High-level view of class progress and resource distribution.
    
*   **Wellbeing Dashboard (/wellbeing\_dashboard):** Monitor student engagement and provide support materials.
    
*   **Day View (/day):** A detailed granular view of tasks and deadlines for a specific calendar date.
    

### Resource Management

*   **/resources**: Browse available materials.
    
*   **/manage\_resources**: (Post/Get) Administer the repository of files/links.
    
*   **/pin\_resource/**: Pin important materials to the top of the feed for quick access.
    
*   **/delete\_resource/**: Remove outdated materials.
    

### Task & Deadline Control

*   **For Students:**
    
    *   /create\_task: Add personal milestones.
        
    *   /update\_task/ / /delete\_task/: Manage personal to-do lists.
        
    *   /add\_deadline/: Convert or link tasks to specific deadlines.
        
*   **For Teachers:**
    
    *   /teacher\_deadlines/create: Push new deadlines to the entire class.
        
    *   /teacher\_deadlines/edit/: Update existing academic requirements.
        
    *   /teacher\_deadlines/delete/: Revoke or remove deadlines.
        

📁 Project Structure
--------------------

*   app.py: Entry point for the Flask application.
    
*   static/: Contains CSS, JavaScript, and image assets.
    
*   templates/: HTML structures for the various dashboards.
    
*   data/ (or similar): JSON files serving as the primary object store.

*   tests/: Contains Behavioural Driven Development tests for every feature.
    

The application is also available online at https://ucompass.onrender.com (Application might be slow to load due to server cold start).

📝 License
----------

bookface ltd., University of Birmingham, 2026