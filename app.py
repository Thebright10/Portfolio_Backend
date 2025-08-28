from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import datetime
import os

app = Flask(__name__)
CORS(app)

LOG_FILE = os.path.join(os.path.dirname(__file__), "visitors.jsonl")

def get_location(ip):
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,lat,lon,query,timezone",
            timeout=5
        )
        data = resp.json()
        if data.get("status") == "success":
            return {
                "ip_lookup": data.get("query"),
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "isp": data.get("isp"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone")
            }
        else:
            return {"error": data.get("message", "lookup_failed")}
    except Exception as e:
        return {"error": str(e)}

def save_log(doc):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Failed to write log:", e)

@app.route("/log-visitor", methods=["POST"])
def log_visitor():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(',')[0].strip()  # In case of multiple IPs
    ua = request.headers.get("User-Agent", "")
    payload = request.get_json(silent=True) or {}

    section = payload.get("section")
    action = payload.get("action")
    success = bool(payload.get("success", False))
    extra = payload.get("extra", {})

    if ip == "127.0.0.1" or ip.startswith("192.168.") or ip.startswith("10."):
        location = {"country": "Local", "region": "", "city": "", "isp": ""}
    else:
        location = get_location(ip)

    doc = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "ip": ip,
        "user_agent": ua,
        "section": section,
        "action": action,
        "success": success,
        "location": location,
        "extra": extra
    }

    print("Visitor logged:", doc)
    save_log(doc)

    return jsonify({"status": "ok", "logged": True})


@app.route("/view-logs-dashboard", methods=["GET"])
def view_logs_dashboard():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except:
                    continue

    html = """
    <html>
    <head>
        <title>Visitor Logs Dashboard</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f4f4f4; }
            table { border-collapse: collapse; width: 100%; background: #fff; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background: #333; color: #fff; }
            tr:nth-child(even) { background: #f9f9f9; }
        </style>
    </head>
    <body>
        <h2>Visitor Logs Dashboard</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>IP</th>
                <th>City</th>
                <th>Region</th>
                <th>Country</th>
                <th>ISP</th>
                <th>Section</th>
                <th>Action</th>
                <th>Success</th>
                <th>Device</th>
                <th>Platform</th>
                <th>Language</th>
            </tr>
    """

    for log in logs[::-1]:
        html += f"""
        <tr>
            <td>{log.get('timestamp','')}</td>
            <td>{log.get('ip','')}</td>
            <td>{log.get('location',{}).get('city','')}</td>
            <td>{log.get('location',{}).get('region','')}</td>
            <td>{log.get('location',{}).get('country','')}</td>
            <td>{log.get('location',{}).get('isp','')}</td>
            <td>{log.get('section','')}</td>
            <td>{log.get('action','')}</td>
            <td>{log.get('success')}</td>
            <td>{log.get('extra', {}).get('device','')}</td>
            <td>{log.get('extra', {}).get('platform','')}</td>
            <td>{log.get('extra', {}).get('language','')}</td>
        </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
