from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from functools import wraps
from datetime import datetime
import sys
import os
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import Response, stream_with_context

# Core Backend Modules
from backend import db, auth, invoice, admin
import razorpay

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

# Configuration Load
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razor_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(" ")[1]
    return auth.verify_token(token)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            return jsonify({"detail": "Invalid or expired token"}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = get_current_user()
        if not current_user or current_user.get('role') != 'admin':
            return jsonify({"detail": "Admin access required"}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# --- Interface Routes ---

@app.route("/")
def read_index():
    return send_file("frontend/index.html")

@app.route("/<page>.html")
def get_html_page(page):
    file_path = f"frontend/{page}.html"
    if os.path.exists(file_path):
        return send_file(file_path)
    return jsonify({"detail": "Page not found"}), 404

# Serve assets manually for Flask
@app.route("/css/<path:path>")
def send_css(path):
    return send_from_directory("frontend/css", path)

@app.route("/js/<path:path>")
def send_js(path):
    return send_from_directory("frontend/js", path)

@app.route("/assets/<path:path>")
def send_assets(path):
    return send_from_directory("frontend/assets", path)

# --- API Routes ---

@app.route("/api/v1/auth/google", methods=["POST"])
def google_auth():
    data = request.json
    if not data or 'id_token' not in data:
        return jsonify({"detail": "Missing id_token"}), 400
    
    
    try:
        # 1. VERIFY GOOGLE ID TOKEN
        idinfo = id_token.verify_oauth2_token(data['id_token'], google_requests.Request(), GOOGLE_CLIENT_ID)
        
        user_info = {
            "google_id": idinfo['sub'],
            "email": idinfo['email'],
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture')
        }
    except ValueError as e:
        return jsonify({"detail": "Invalid Google Token"}), 401
    except Exception as e:
        return jsonify({"detail": "Identity Verification Failed"}), 500

    try:
        query = """
        INSERT INTO users (google_id, email, name, profile_picture)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (google_id) DO UPDATE 
        SET email = EXCLUDED.email, 
            name = EXCLUDED.name, 
            profile_picture = EXCLUDED.profile_picture,
            updated_at = CURRENT_TIMESTAMP
        RETURNING *;
        """
        params = (user_info["google_id"], user_info["email"], user_info["name"], user_info["picture"])
        user_record = db.execute_query(query, params)
        
        # 5. GENERATE JWT
        access_token = auth.create_access_token(data={"sub": user_info["email"], "role": user_record[0][6]})
        
        return jsonify({
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_record[0]
        })
    except Exception as e:
        return jsonify({"detail": "Authentication sync failed."}), 500

@app.route("/api/v1/user/profile", methods=["GET"])
@token_required
def get_profile(current_user):
    return jsonify({"status": "AUTHENTICATED", "user_data": current_user})

@app.route("/api/v1/cart", methods=["POST"])
def add_to_cart():
    item = request.json
    if not item:
        return jsonify({"detail": "Missing item data"}), 400
        
    try:
        # Check for duplicates
        check_query = "SELECT id FROM cart WHERE user_id = %s AND project_id = %s AND project_category = %s"
        existing = db.execute_query(check_query, (item['user_id'], item['project_id'], item['project_category']))
        
        if existing:
            return jsonify({"status": "exists", "message": "Project already in cart"})

        query = """
        INSERT INTO cart (user_id, project_id, project_name, project_category)
        VALUES (%s, %s, %s, %s) RETURNING id;
        """
        result = db.execute_query(query, (item['user_id'], item['project_id'], item['project_name'], item['project_category']))
        return jsonify({"status": "success", "cart_id": result[0][0]})
    except Exception as e:
        return jsonify({"detail": "Failed to add item to cart"}), 500

@app.route("/api/v1/cart/<int:user_id>", methods=["GET"])
def get_cart(user_id):
    try:
        # 1. Fetch all items in cart first
        query = "SELECT id, project_id, project_name, project_category FROM cart WHERE user_id = %s ORDER BY added_at DESC;"
        cart_rows = db.execute_query(query, (user_id,))
        if not cart_rows:
            return jsonify([])

        # 2. Group project IDs by category for bulk fetching
        categorized_ids = {}
        for row in cart_rows:
            cat = row[3]
            p_id = row[1]
            if cat not in categorized_ids:
                categorized_ids[cat] = []
            categorized_ids[cat].append(p_id)

        # 3. Fetch project details in bulk from the unified table
        project_details = {} # Map id -> {price, image}
        
        all_ids = [row[1] for row in cart_rows]
        if all_ids:
            placeholders = ', '.join(['%s'] * len(all_ids))
            p_query = f"SELECT id, offer_amount, image_link, description FROM projects WHERE id IN ({placeholders})"
            p_rows = db.execute_query(p_query, all_ids)
            for pr in p_rows:
                project_details[pr[0]] = {"price": float(pr[1]), "image": pr[2], "description": pr[3]}

        # 4. Assemble final list
        cart_items = []
        for row in cart_rows:
            details = project_details.get(row[1], {})
            cart_items.append({
                "cart_id": row[0],
                "project_id": row[1],
                "name": row[2],
                "category": row[3],
                "price": details.get("price", 0),
                "image_link": details.get("image", "assets/monogram.png"),
                "description": details.get("description", "Premium project details.")
            })
        
        return jsonify(cart_items)
    except Exception as e:
        return jsonify({"detail": "Fast fetch core failure"}), 500

@app.route("/api/v1/cart/<int:cart_id>", methods=["DELETE"])
def remove_from_cart(cart_id):
    try:
        db.execute_query("DELETE FROM cart WHERE id = %s", (cart_id,))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"detail": "Failed to remove item"}), 500

@app.route("/api/v1/projects/ai", methods=["GET"])
def get_ai_projects():
    try:
        query = "SELECT id, name, description, original_amount, offer_amount, offer_percentage, tag, image_link FROM projects WHERE category = 'ai' ORDER BY id DESC;"
        rows = db.execute_query(query)
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "original_amount": float(row[3]),
                "offer_amount": float(row[4]),
                "offer_percentage": row[5],
                "tag": row[6],
                "image_link": row[7]
            })
        return jsonify(projects)
    except Exception as e:
        return jsonify({"detail": "Failed to fetch AI projects"}), 500

@app.route("/api/v1/projects/<category>", methods=["GET"])
def get_projects(category):
    
    try:
        query = "SELECT id, name, description, original_amount, offer_amount, offer_percentage, tag, image_link FROM projects WHERE category = %s ORDER BY id DESC;"
        rows = db.execute_query(query, (category,))
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "original_amount": float(row[3]),
                "offer_amount": float(row[4]),
                "offer_percentage": row[5],
                "tag": row[6],
                "image_link": row[7]
            })
        return jsonify(projects)
    except Exception as e:
        return jsonify({"detail": f"Failed to fetch {category} projects"}), 500

@app.route("/api/v1/payment/create", methods=["POST"])
def create_payment_order():
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"detail": "User ID required"}), 400

    try:
        # 1. Fetch all items in cart for dynamic pricing
        query = "SELECT project_id, project_category FROM cart WHERE user_id = %s"
        cart_rows = db.execute_query(query, (user_id,))
        if not cart_rows:
            return jsonify({"detail": "Cart is empty"}), 400

        total_amount = 0
        for row in cart_rows:
            p_id = row[0]
            p_query = "SELECT offer_amount FROM projects WHERE id = %s"
            p_rows = db.execute_query(p_query, (p_id,))
            if p_rows:
                total_amount += float(p_rows[0][0])

        if total_amount <= 0:
            return jsonify({"detail": "Invalid total amount"}), 400

        # Create Razorpay Order
        razor_payload = {
            "amount": int(total_amount * 100), # amount in paise
            "currency": "INR",
            "payment_capture": "1"
        }
        order = razor_client.order.create(data=razor_payload)
        
        return jsonify({
            "order_id": order['id'],
            "amount": total_amount,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({"detail": "Failed to create payment order"}), 500

@app.route("/api/v1/payment/verify", methods=["POST"])
def verify_payment():
    data = request.json
    if not data:
        return jsonify({"detail": "Missing payment data"}), 400

    try:
        # Verify Signature
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }
        razor_client.utility.verify_payment_signature(params_dict)

        # Payment Successful: Archive to payments table and clear cart
        user_id = data.get("user_id")
        amount = data.get("amount")

        # 1. Fetch current cart and user details
        items_query = "SELECT project_id, project_name, project_category FROM cart WHERE user_id = %s"
        cart_items = db.execute_query(items_query, (user_id,))
        
        user_query = "SELECT name, email FROM users WHERE id = %s"
        user_record = db.execute_query(user_query, (user_id,))
        user_name = user_record[0][0] if user_record else "MataVex User"
        user_email = user_record[0][1] if user_record else ""

        # 2. Bulk Insert to Payments and Library
        pdf_items = []
        for item in cart_items:
            # Fetch price for invoice
            p_query = "SELECT offer_amount FROM projects WHERE id = %s"
            p_rows = db.execute_query(p_query, (item[0],))
            item_price = float(p_rows[0][0]) if p_rows else 0
            
            pdf_items.append({
                "name": item[1],
                "category": item[2],
                "price": item_price
            })

            insert_query = """
            INSERT INTO payments (user_id, project_id, project_name, project_category, order_id, payment_id, amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'SUCCESS')
            """
            db.execute_query(insert_query, (
                user_id,
                item[0],
                item[1],
                item[2],
                data['razorpay_order_id'],
                data['razorpay_payment_id'],
                item_price # Store per-item price
            ))

            # ARCHIVE TO LIBRARY (Ownership Node)
            library_query = """
            INSERT INTO library (user_id, user_name, project_id, project_category, project_name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, project_id, project_category) DO NOTHING;
            """
            db.execute_query(library_query, (user_id, user_name, item[0], item[2], item[1]))

        # 3. Generate and Send Invoice
        try:
            invoice_dir = "invoices"
            if not os.path.exists(invoice_dir):
                os.makedirs(invoice_dir)
            
            pdf_filename = f"invoice_{data['razorpay_payment_id']}.pdf"
            pdf_path = os.path.join(invoice_dir, pdf_filename)
            
            order_details = {
                "user_name": user_name,
                "user_email": user_email,
                "payment_id": data['razorpay_payment_id'],
                "date": datetime.now().strftime("%d %b %Y"),
                "amount": amount
            }
            
            invoice.generate_invoice_pdf(order_details, pdf_items, pdf_path)
            
            if user_email:
                invoice.send_invoice_email(user_email, pdf_path, data['razorpay_payment_id'])
        except Exception as inv_err:

        # 4. Clear Cart
        db.execute_query("DELETE FROM cart WHERE user_id = %s", (user_id,))
        
        return jsonify({"status": "SUCCESS", "message": "Secure Payment Archived, Library Updated and Invoice Sent"})
    except razorpay.errors.SignatureVerificationError:
        return jsonify({"status": "FAIL", "message": "Identity Verification Failed"}), 400
    except Exception as e:
        return jsonify({"status": "ERROR", "message": "Internal Sync Error"}), 500

@app.route("/api/v1/payments/<int:user_id>", methods=["GET"])
def get_purchased_projects(user_id):
    try:
        # 1. Fetch successful project ownership from library table
        # We join with payments and projects to get meta
        query = """
        SELECT l.project_id, l.project_name, l.project_category, l.user_id, p.payment_id, l.purchased_at 
        FROM library l
        JOIN payments p ON l.user_id = p.user_id 
            AND l.project_id = p.project_id 
        WHERE l.user_id = %s AND p.status = 'SUCCESS'
        ORDER BY l.purchased_at DESC;
        """
        rows = db.execute_query(query, (user_id,))
        if not rows:
            return jsonify([])

        # 2. Fetch project details from the unified table
        project_meta = {}
        all_ids = [row[0] for row in rows]
        if all_ids:
            placeholders = ', '.join(['%s'] * len(all_ids))
            p_query = f"SELECT id, image_link FROM projects WHERE id IN ({placeholders})"
            p_rows = db.execute_query(p_query, all_ids)
            for pr in p_rows:
                project_meta[pr[0]] = pr[1]

        # 3. Assemble
        purchased = []
        for row in rows:
            purchased.append({
                "project_id": row[0],
                "name": row[1],
                "category": row[2],
                "user_id": row[3],
                "payment_id": row[4],
                "date": row[5].strftime("%d %b %Y"),
                "image_link": project_meta.get(row[0], "assets/monogram.png")
            })
        
        return jsonify(purchased)
    except Exception as e:
        return jsonify({"detail": "Failed to fetch purchased projects"}), 500

@app.route("/api/v1/projects/download/<int:project_id>", methods=["GET"])
def download_project(project_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"detail": "Credentials required"}), 401
    
    
    try:
        # 1. Verify ownership in library
        check_query = "SELECT id FROM library WHERE user_id = %s AND project_id = %s"
        owned = db.execute_query(check_query, (user_id, project_id))
        
        if not owned:
            return jsonify({"detail": "Access Denied: Product Ownership not verified."}), 403
            
        # 2. Fetch secure link
        link_query = "SELECT download_link FROM project_links WHERE project_id = %s"
        link_res = db.execute_query(link_query, (project_id,))
        
        if not link_res:
             return jsonify({"detail": "Download archive not found for this project."}), 404
             
        download_url = link_res[0][0]
        
        # 3. Proxy the download to hide the repo URL
        # We stream the content from GitHub directly to the user
        req = requests.get(download_url, stream=True)
        
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                yield chunk
        
        # Get original filename if possible or fallback
        filename = f"matavex_project_{project_id}.zip"
        
        return Response(stream_with_context(generate()), 
                        headers={
                            "Content-Type": req.headers.get("Content-Type", "application/zip"),
                            "Content-Disposition": f"attachment; filename={filename}"
                        })

    except Exception as e:
        return jsonify({"detail": "Internal Download Node Failure"}), 500

# --- Admin Routes ---

@app.route("/api/v1/admin/login", methods=["POST"])
def admin_login():
    return admin.admin_login()

@app.route("/api/v1/admin/tables", methods=["GET"])
@admin_required
def list_tables(current_user):
    return admin.get_all_tables()

@app.route("/api/v1/admin/table/<table_name>", methods=["GET"])
@admin_required
def get_table_data(current_user, table_name):
    return admin.get_table_data(table_name)

@app.route("/api/v1/admin/table/<table_name>", methods=["PUT"])
@admin_required
def update_table_row(current_user, table_name):
    return admin.update_row(table_name)

@app.route("/api/v1/admin/table/<table_name>/<int:row_id>", methods=["DELETE"])
@admin_required
def delete_table_row(current_user, table_name, row_id):
    return admin.delete_row(table_name, row_id)

@app.route("/api/v1/admin/table/<table_name>", methods=["POST"])
@admin_required
def insert_table_row(current_user, table_name):
    return admin.insert_row(table_name)

@app.route("/api/v1/health")
def health_check():
    try:
        result = db.execute_query("SELECT now();")
        return jsonify({"status": "UP", "db": "CONNECTED", "timestamp": str(result[0][0])})
    except Exception as e:
        return jsonify({"detail": "Internal Core Sync Failure"}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
