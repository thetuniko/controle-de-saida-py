from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import hashlib
import urllib.request
import urllib.error
import os

SUPABASE_URL = "https://sfzleczdsorvfknjtzot.supabase.co"
SUPABASE_KEY = "sb_secret_IqPXb8svsnWiWcpIRHJNFw_JuWG2TB_"

def supabase_request(endpoint, method="GET", data=None, query_params=""):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if query_params:
        url += f"?{query_params}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    req_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode('utf-8')
            return json.loads(body) if body else []
    except Exception as e:
        print(f"Erro Supabase: {e}")
        return None

def init_db():
    users = supabase_request("users", query_params="username=eq.admin")
    if not users:
        pwd_hash = hashlib.sha256("Pr1pr1213@".encode()).hexdigest()
        supabase_request("users", method="POST", data={
            "username": "admin",
            "password": pwd_hash,
            "role": "admin"
        })
        print("Admin inicial criado no Supabase.")

init_db()

class SimpleAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/logs':
            rows = supabase_request("logs", query_params="select=*&order=timestamp.desc") or []
            logs = [{"id": r.get("id"), "timestamp": r.get("timestamp"), "type": r.get("type"), "reason": r.get("reason"), "countAfter": r.get("countAfter"), "username": r.get("username") or "sistema"} for r in rows]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(logs).encode('utf-8'))
        elif self.path == '/api/users':
            rows = supabase_request("users", query_params="select=username,role") or []
            users = [{"username": r["username"], "role": r["role"]} for r in rows]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(users).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except:
            data = {}

        if self.path == '/api/logs':
            payload = {
                "id": data['id'], "timestamp": data['timestamp'], "type": data['type'],
                "reason": data.get('reason'), "countAfter": data['countAfter'], "username": data.get('username', 'sistema')
            }
            res = supabase_request("logs", method="POST", data=payload)
            self.send_response(200 if res is not None else 500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Sucesso"}).encode('utf-8'))

        elif self.path == '/api/login':
            username = data.get('username')
            password = data.get('password')
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            users = supabase_request("users", query_params=f"username=eq.{username}&password=eq.{pwd_hash}")
            if users and len(users) > 0:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "role": users[0]["role"], "username": username}).encode('utf-8'))
            else:
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Credenciais inválidas"}).encode('utf-8'))

        elif self.path == '/api/users':
            username = data.get('username')
            password = data.get('password')
            role = data.get('role', 'editor')
            if not username or not password:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Preencha os campos"}).encode('utf-8'))
                return
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            res = supabase_request("users", method="POST", data={"username": username, "password": pwd_hash, "role": role})
            self.send_response(200 if res is not None else 400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"success": res is not None}).encode('utf-8'))

    def do_DELETE(self):
        if self.path.startswith('/api/logs/'):
            log_id = self.path.split('/')[-1]
            supabase_request(f"logs?id=eq.{log_id}", method="DELETE")
        elif self.path == '/api/logs':
            supabase_request("logs?id=not.is.null", method="DELETE")
        elif self.path.startswith('/api/users/'):
            username_to_delete = self.path.split('/')[-1]
            if username_to_delete != 'admin':
                supabase_request(f"users?username=eq.{username_to_delete}", method="DELETE")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Sucesso"}).encode('utf-8'))

def run():
    port = int(os.environ.get("PORT", 3000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleAPIHandler)
    print(f"Servidor web rodando na porta {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
