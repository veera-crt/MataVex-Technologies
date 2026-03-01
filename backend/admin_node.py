import os
from flask import request, jsonify
from passlib.hash import pbkdf2_sha256
from backend import db, auth
import psycopg2

def admin_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"detail": "Username and password required"}), 400

    try:
        query = "SELECT id, password_hash FROM admin_users WHERE username = %s"
        result = db.execute_query(query, (username,))

        if not result:
            return jsonify({"detail": "Invalid credentials"}), 401

        admin_id, password_hash = result[0]

        if pbkdf2_sha256.verify(password, password_hash):
            token = auth.create_access_token(data={"sub": username, "role": "admin"})
            return jsonify({
                "success": True,
                "access_token": token,
                "user": {"id": admin_id, "username": username, "role": "admin"}
            })
        else:
            return jsonify({"detail": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"detail": "Login failed"}), 500

def get_all_tables():
    try:
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        """
        rows = db.execute_query(query)
        tables = [row[0] for row in rows]
        return jsonify(tables)
    except Exception as e:
        return jsonify({"detail": f"Failed to fetch tables: {e}"}), 500

def get_table_data(table_name):
    try:
        # 1. Get Schema
        schema_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s 
        AND table_schema = 'public'
        ORDER BY ordinal_position
        """
        columns = db.execute_query(schema_query, (table_name,))
        
        col_names = [col[0] for col in columns]
        
        # 2. Get Data
        data_query = f"SELECT * FROM {table_name} LIMIT 100"
        rows = db.execute_query(data_query)
        
        # Convert rows (tuples) to list of dicts
        formatted_data = []
        for row in rows:
            formatted_data.append(dict(zip(col_names, row)))
            
        return jsonify({
            "columns": col_names,
            "data": formatted_data
        })
    except Exception as e:
        return jsonify({"detail": f"Failed to fetch table data: {e}"}), 500

def update_row(table_name):
    data = request.json
    row_id = data.get("id") # Assuming 'id' is the primary key
    updates = data.get("updates") # dict of col: val
    
    if not row_id or not updates:
        return jsonify({"detail": "ID and updates required"}), 400
        
    try:
        set_clause = ", ".join([f"{col} = %s" for col in updates.keys()])
        values = list(updates.values())
        values.append(row_id)
        
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
        db.execute_query(query, tuple(values))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"detail": f"Update failed: {e}"}), 500

def delete_row(table_name, row_id):
    try:
        query = f"DELETE FROM {table_name} WHERE id = %s"
        db.execute_query(query, (row_id,))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"detail": f"Delete failed: {e}"}), 500

def insert_row(table_name):
    data = request.json
    record = data.get("record") # dict of col: val
    
    if not record:
        return jsonify({"detail": "Record data required"}), 400
        
    try:
        cols = ", ".join(record.keys())
        placeholders = ", ".join(["%s"] * len(record))
        values = list(record.values())
        
        query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) RETURNING id"
        result = db.execute_query(query, tuple(values))
        return jsonify({"success": True, "id": result[0][0]})
    except Exception as e:
        return jsonify({"detail": f"Insertion failed: {e}"}), 500
