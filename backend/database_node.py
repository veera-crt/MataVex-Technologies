import os
import psycopg2
from psycopg2 import pool, OperationalError
import time


DATABASE_URL = os.getenv("DATABASE_URL")

# Production Robust Pool
execution_pool = None

def init_pool():
    global execution_pool
    try:
        execution_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20, # Dynamic range
            DATABASE_URL
        )
    except Exception as e:
        pass

init_pool()

def get_connection():
    global execution_pool
    try:
        if execution_pool is None:
            init_pool()
        conn = execution_pool.getconn()
        # Ping the connection to ensure it's alive (Fixes SSL closed unexpectedly)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (OperationalError, Exception):
            execution_pool.putconn(conn, close=True) # Put back and close
            conn = execution_pool.getconn()
        return conn
    except Exception as e:
        return None

def release_connection(conn):
    if execution_pool and conn:
        execution_pool.putconn(conn)

def execute_query(query, params=None):
    conn = get_connection()
    if not conn:
        raise Exception("Database node unreachable.")
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            result = None
            if cursor.description:
                result = cursor.fetchall()
            
            # Always commit to persist changes (required for INSERT ... RETURNING)
            conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)
