# SQL Assessment Platform

[![CI Database Test](https://github.com/gulnargasimzada/sql-quiz-app/actions/workflows/ci.yml/badge.svg)](https://github.com/gulnargasimzada/sql-quiz-app/actions/workflows/ci.yml)

An interactive, cloud-native SQL evaluation environment where students can solve and execute relational queries against a live, hosted PostgreSQL database.

- **Live Quiz Application URL:** https://sql-quiz-app-4gx6cjcl84jrrrsyans9ie.streamlit.app/
- **Hosted Database:** PostgreSQL (Supabase) via Session Pooler (`sslmode=require`)
- **Authentication Engine:** Supabase Auth
- **Continuous Integration:** GitHub Actions with Encrypted Secrets

---

## 1. System Architecture & Components

The application fulfills all four core technical requirements:

1. **Hosted PostgreSQL Database (Supabase):**
   - Configured with a relational schema for a movie rental platform (`customers`, `movies`, `rentals`).
   - Uses the **Session Pooler** over port `5432` with enforced `sslmode=require`.
2. **Access Control & Authentication (Supabase Auth):**
   - **Signed-Out State:** Visitors can inspect question prompts, but database query execution is strictly locked.
   - **Signed-In State:** Authenticated users can execute SQL against live tables and view resulting records.
3. **CI Pipeline via GitHub Secrets:**
   - Automated through `.github/workflows/ci.yml`.
   - Executes `test_db.py` to verify live database connectivity using encrypted repository secrets without committing passwords.
4. **20-Point SQL Assessment:**
   - 5 multi-tier relational SQL questions (4 points each).
   - Validated against live result sets (matching row count, schema shape, ordering, and data values).

---

## 2. 20-Point SQL Quiz Specification

| Question | Topic / Concept Tested | Points | Target Concept & Approach | Required Output Columns |
| :---: | :--- | :---: | :--- | :--- |
| **Q1** | Above-Average Rated Movies by Genre | 4 pts | Correlated subquery in `WHERE` comparing ratings to genre average | `title`, `genre`, `rating` |
| **Q2** | Customers with No Sci-Fi Rentals | 4 pts | Subquery exclusion using `NOT IN` against target genre rentals | `full_name`, `country`, `subscription_type` |
| **Q3** | Premium Revenue & Rental Count by Country | 4 pts | Multi-table `JOIN` with conditional aggregation and `HAVING` threshold | `country`, `premium_rentals_count`, `total_revenue` |
| **Q4** | Customers Exceeding Mean Active Spending | 4 pts | Derived table (`FROM`-clause subquery) compared against overall spend | `full_name`, `total_spent` |
| **Q5** | Top-Ranked Movie per Genre | 4 pts | Window function (`DENSE_RANK() OVER`) partitioned by genre | `genre`, `title`, `rental_rate` |

---

## 3. Step-by-Step User Guide (How to Use the Live Streamlit App)

To take the assessment or grade a student's submission on the live platform:

### Step 1: Open the Application
Navigate to the live application URL provided at the top of this document.

### Step 2: Sign Up and Sign In (Authentication Guardrail)
1. In the left sidebar (**Student Portal**), select **Sign Up**.
2. Enter an email and password, then click **Register**.
3. Switch to **Sign In**, enter your credentials, and click **Log In**.
4. Once authenticated, your email is confirmed in the sidebar (`👤 Logged In: ...`), unlocking query execution.

### Step 3: Choose an Assessment Question
1. Locate the **"Select Question:"** dropdown menu in the main panel.
2. Select any of the 5 questions (Q1 through Q5). The question description, point value (4 pts), and requirements will update dynamically.

### Step 4: Inspect Question Hints & Schema
1. Click the **"💡 View Question Guidance & Expected Columns"** expander.
2. Review the target output column names and structural approach for the question.

### Step 5: Write and Execute Your SQL Query
1. Write your SQL statement inside the **"Your Query Execution"** text box.
2. Click the **🚀 Run Query** button.
3. The platform executes your query against the live Supabase PostgreSQL database:
   - **Live Results Table:** Displays all retrieved rows.
   - **Automated Validation:** If your result matches the benchmark dataset (shape, values, ordering), a success message and balloon animation appear (`+4 Points`).
   - If there is a mismatch, helpful feedback prompts you to adjust your conditions.

---

## 4. Continuous Integration & Security Verification

Database network connectivity and schema integrity are verified through GitHub Actions:
- **Workflow File:** `.github/workflows/ci.yml`
- **Secret Management:** Connection credentials are read strictly from `${{ secrets.DATABASE_URL }}`.
- **Automated Test:** The workflow executes `pytest -v test_db.py`, connecting to the Supabase instance, running a live validation query (`SELECT COUNT(*) FROM movies;`), and confirming that test records are present.