import os
import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# 1. Environment & Database Configuration
# ==========================================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(page_title="CineStream Live SQL Quiz", layout="wide", page_icon="🎬")

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = get_supabase_client()

def execute_sql_query(query: str):
    """Executes a query against the hosted PostgreSQL database safely."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)

# ==========================================
# 2. Quiz Questions (Minimalist Conceptual Hints)
# ==========================================
QUIZ_QUESTIONS = [
    {
        "id": 1,
        "title": "Question 1: Above-Average Rated Movies by Genre",
        "points": 4,
        "prompt": (
            "Find the titles, genres, and ratings of all movies whose rating is strictly higher "
            "than the average rating of their specific genre. Order results by rating descending."
        ),
        "expected_columns": ["title", "genre", "rating"],
        "concept_hint": "Filter movies by comparing each movie's rating against an inner correlated subquery calculating the genre's average.",
        "benchmark_sql": """
            SELECT m1.title, m1.genre, m1.rating
            FROM movies m1
            WHERE m1.rating > (
                SELECT AVG(m2.rating)
                FROM movies m2
                WHERE m2.genre = m1.genre
            )
            ORDER BY m1.rating DESC;
        """
    },
    {
        "id": 2,
        "title": "Question 2: Customers with No Sci-Fi Rentals",
        "points": 4,
        "prompt": (
            "Identify all registered customers who have never rented any movie in the 'Sci-Fi' genre. "
            "Display customer full name, country, and subscription type, sorted alphabetically by full name."
        ),
        "expected_columns": ["full_name", "country", "subscription_type"],
        "concept_hint": "Exclude customers using a NOT IN condition paired with a subquery that retrieves renters of the target genre.",
        "benchmark_sql": """
            SELECT full_name, country, subscription_type
            FROM customers
            WHERE customer_id NOT IN (
                SELECT r.customer_id
                FROM rentals r
                JOIN movies m ON r.movie_id = m.movie_id
                WHERE m.genre = 'Sci-Fi'
            )
            ORDER BY full_name ASC;
        """
    },
    {
        "id": 3,
        "title": "Question 3: Premium Revenue & Rental Count by Country",
        "points": 4,
        "prompt": (
            "For each country, calculate the total number of rentals and total revenue generated strictly "
            "by customers with a 'Premium' subscription. Filter out countries with zero revenue and sort by total_revenue descending."
        ),
        "expected_columns": ["country", "premium_rentals_count", "total_revenue"],
        "concept_hint": "Aggregate transactions by country using GROUP BY and apply a HAVING filter on total revenue.",
        "benchmark_sql": """
            SELECT 
                c.country,
                COUNT(r.rental_id) AS premium_rentals_count,
                SUM(r.amount_paid) AS total_revenue
            FROM customers c
            JOIN rentals r ON c.customer_id = r.customer_id
            WHERE c.subscription_type = 'Premium'
            GROUP BY c.country
            HAVING SUM(r.amount_paid) > 0
            ORDER BY total_revenue DESC;
        """
    },
    {
        "id": 4,
        "title": "Question 4: Customers Exceeding Mean Active Spending",
        "points": 4,
        "prompt": (
            "Find all customers whose total spending exceeds the average total spending across all active "
            "customers who have made rentals. Display full name and total spent, sorted by total_spent descending."
        ),
        "expected_columns": ["full_name", "total_spent"],
        "concept_hint": "Compute individual customer totals within a derived table (FROM-clause subquery), then compare against the overall average spending.",
        "benchmark_sql": """
            SELECT c.full_name, sub.total_spent
            FROM (
                SELECT customer_id, SUM(amount_paid) AS total_spent
                FROM rentals
                GROUP BY customer_id
            ) sub
            JOIN customers c ON c.customer_id = sub.customer_id
            WHERE sub.total_spent > (
                SELECT AVG(total_spent)
                FROM (
                    SELECT SUM(amount_paid) AS total_spent
                    FROM rentals
                    GROUP BY customer_id
                ) avg_table
            )
            ORDER BY sub.total_spent DESC;
        """
    },
    {
        "id": 5,
        "title": "Question 5: Top-Ranked Movie per Genre",
        "points": 4,
        "prompt": (
            "Rank movies within each genre based on their rental rate in descending order (using DENSE_RANK()). "
            "Return only the top-ranked (rank 1) movie(s) for each genre. Order by genre ascending, then title ascending."
        ),
        "expected_columns": ["genre", "title", "rental_rate"],
        "concept_hint": "Use a window function (DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...)) inside a subquery, then filter for rank = 1.",
        "benchmark_sql": """
            SELECT genre, title, rental_rate
            FROM (
                SELECT 
                    genre, 
                    title, 
                    rental_rate,
                    DENSE_RANK() OVER (PARTITION BY genre ORDER BY rental_rate DESC) as rank
                FROM movies
            ) ranked_movies
            WHERE rank = 1
            ORDER BY genre ASC, title ASC;
        """
    }
]

# ==========================================
# 3. User Session State & Auth Sidebar
# ==========================================
if "user" not in st.session_state:
    st.session_state["user"] = None

st.sidebar.title("🔐 Student Portal")

if st.session_state["user"] is None:
    auth_mode = st.sidebar.radio("Authentication", ["Sign In", "Sign Up"])
    email = st.sidebar.text_input("Student Email")
    password = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Sign Up":
        if st.sidebar.button("Register"):
            if email and password:
                try:
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.sidebar.success("Account registered. You may now sign in.")
                except Exception as e:
                    st.sidebar.error(f"Sign up error: {e}")
            else:
                st.sidebar.warning("Please enter email and password.")

    elif auth_mode == "Sign In":
        if st.sidebar.button("Log In"):
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state["user"] = res.user.email
                    st.sidebar.success(f"Signed in as {res.user.email}")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Authentication failed: {e}")
            else:
                st.sidebar.warning("Credentials required.")
else:
    st.sidebar.success(f"👤 Logged In: **{st.session_state['user']}**")
    if st.sidebar.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state["user"] = None
        st.rerun()

# ==========================================
# 4. Main Interface & SQL Execution Runner
# ==========================================
st.title("🎬 CineStream SQL Assessment (20 Points Total)")
st.caption("Live hosted PostgreSQL environment powered by Supabase.")

# Strict Enforcement: Signed-out visitors cannot execute queries
if st.session_state["user"] is None:
    st.warning("⚠️ **Access Locked:** You must **Sign In** from the sidebar to execute queries and submit answers.")

# Dropdown selection for questions
labels = [f"Q{q['id']}: {q['title']} ({q['points']} pts)" for q in QUIZ_QUESTIONS]
selected_idx = st.selectbox("Select Question:", range(len(QUIZ_QUESTIONS)), format_func=lambda i: labels[i])
active_q = QUIZ_QUESTIONS[selected_idx]

st.subheader(f"{active_q['title']} — {active_q['points']} Points")
st.write(active_q["prompt"])

# The Clean Hint Expander: Only schema and concept guidance (NO SQL CODE LEAKS)
with st.expander("💡 View Question Guidance & Expected Columns"):
    st.markdown(f"**Required Output Columns:** `{', '.join(active_q['expected_columns'])}`")
    st.markdown(f"**Approach / Concept:** {active_q['concept_hint']}")

st.markdown("---")
st.subheader("Your Query Execution")

user_sql = st.text_area(
    "Enter SQL query:",
    value="SELECT * FROM movies LIMIT 5;",
    height=140
)

if st.button("🚀 Run Query", type="primary"):
    if st.session_state["user"] is None:
        st.error("⛔ Permission Denied: Only authenticated users can run queries against the database.")
    else:
        with st.spinner("Connecting and executing query..."):
            user_df, err = execute_sql_query(user_sql)
            
            if err:
                st.error(f"❌ SQL Execution Error:\n{err}")
            else:
                st.success(f"Execution successful! Fetched {len(user_df)} rows.")
                st.dataframe(user_df, use_container_width=True)
                
                # Automated comparison against hidden benchmark
                benchmark_df, _ = execute_sql_query(active_q["benchmark_sql"])
                if benchmark_df is not None:
                    try:
                        u_res = user_df.reset_index(drop=True)
                        b_res = benchmark_df.reset_index(drop=True)
                        
                        if u_res.shape == b_res.shape and u_res.values.tolist() == b_res.values.tolist():
                            st.balloons()
                            st.success(f"🎉 Result set verified! All criteria met. (+{active_q['points']} Points)")
                        else:
                            st.info("ℹ️ Query succeeded, but the returned rows/columns do not match the expected result set. Re-check conditions, columns, and ordering.")
                    except Exception:
                        st.info("Query executed. Please verify column aliases and sort order.")