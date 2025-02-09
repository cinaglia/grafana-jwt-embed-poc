from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import httpx
from typing import Optional
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
from jose import jwt
import time
import json
import math
from time import time
import os

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GRAFANA_CONFIG = {
    "base_url": os.getenv("GRAFANA_BASE_URL", ""),
    "token": os.getenv("GRAFANA_TOKEN", ""),
    "datasource_id": os.getenv("GRAFANA_DATASOURCE_ID", ""),
    "dashboard_id": os.getenv("GRAFANA_DASHBOARD_ID", ""),
    "private_key": {
        "p": "9kskMIvWlXmCqjLl11RlFUe-aAthUfL-JFlyIXlWV5QAE5egPjTJCHPJeMS-AmuTFte3uQc0KUYKZIRZtwjeLTvwoWU68ng0ntyQs8I8YaAqO6o8yIQxC-sPiP5ZSJasX2kbci6LnU6eePGhrBNp8QxLKDFkc7gGEzHG4cPx67E",
        "kty": "RSA",
        "q": "tqqOA6YaeyeKEb_MXSOTwvBpq1kVwY3QSClgupCOdKq3MZibhBWoE0nV5lr98aa2Xs6B8-Eoe38hHSf51dBX0QnjUdgvtTSoIpNC-jAqFKQnT2BlnQ3MTroyianyYqW5cj4l2EfuRzqUgxoPdEArAkyaovMv3ZJ1QQiW2RDjQKs",
        "d": "rVs7iqzZvAvzd51cI45G8RBxBqiVIS_vDQlGXQjnRGeqps6cXt90VNKMPKWj01TamkFi01aQ_RFVC1bu4eySKeIDzJ55eOkexV5usJwAgHiEzadYb8edikml6_UglMbTEb9OcCw8_DFzAKURpWKiQwEexkfbtoWWLxR9KzSP_3wB_knOJjkswkvaSB_YAJ-lY-ZF2DIrCi_3fKacqIwe_NiYDoTbXirRo-C88h0OYJ0QGdOf4DUiZSUrC1W_KVCfP65gzhRHa9Bl3HN3ZNIE5DRjsygMKOZHjtLoidjEcNp0ygDBsepk1zRwrEoocL8MIPMNTPQei6Vosjam-CkHAQ",
        "e": "AQAB",
        "kid": "embed-key-1",
        "qi": "1rPM84rATB0GODw4prZDmhlWLT1wiRTqZdFmIXXVsLaimm1HLMTcFH6a-sJWS21ffTlgO-pArHeXS2COu5Zs00TGIXkTwiccRFSSOJTmiAt1oCHPNaDM3RAEbwSSU0fB2M6q9npnEEzPqqrFgrMBVvpWwP76FOgWX5fl6cP8VKs",
        "dp": "YvQ_vw2AEqA2YmF-vOwYjNs9YhooaL-DYmFZnJ9elGNPQI_r_vJATxgOO2p4mQpVl5jmJP4C9A5DAK24SfTTJ0Ns47uDWoX3RliB_ucsUWEDduNn9nw-JHa10Cm4_5Qh_1eAgni2-WXr_9W9SiCmsQVqcOSfYmrubenS6URLv5E",
        "dq": "iHiGH13C3Q3eToJwKYnCBFtfZx_obDIKUU9wsBH-DFXbBhfQ4G7ZooeAYljK7vaxu8UnO9CVUSba05ChTEgaw9dSWTxd8FDF6QcCfC7t0XwOznPjluHPKWZdCZLJvz-3fA3IcnzTHa47dHNM5npmZ5JZ2bI8qZqZNZw4LzY5wn8",
        "n": "r72CQbxp-HucSbBvxJxpC7gIdG13gEoRKHzELtGrmIgG5mh9oUM0UcJ7rC8j_dEbRbXLr0FO3TGWHWHlzf39HG7OCVKcpsUTSWPGJl_NbQtEW0jKldfR8icoCHhuSHK1vwDrX-9zwfdA2w_xmH06ButiRENr3IY-XP06oxd0kGJ-Rgy6pFUu5YLSI6YiuuiuKdICmKwu9GJXRcUt5P2RtJ_Y14TyCxua9Zv0F1DAtcwTcHLc-vId23hsq_skrvMvF3jHehIiHavhlCsQ6fqqDi8LRv-H8i1x6xbDy38T2OOLaAuT168sGw40V7OdsVmysJ09ugw0pufhGqcSa3evOw"
    }
}

# Models
class GrafanaTeam(BaseModel):
    id: Optional[int] = None
    uid: Optional[str] = None
    name: str
    email: str

class DashboardRequest(BaseModel):
    user_id: int

# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Add this near the top with other imports and config
with open("keys/jwks.json") as f:
    JWKS = json.load(f)

async def create_grafana_request(method: str, path: str, json_data: dict = None) -> httpx.Request:
    headers = {
        "Authorization": f"Bearer {GRAFANA_CONFIG['token']}",
        "Content-Type": "application/json"
    }
    url = f"{GRAFANA_CONFIG['base_url']}{path}"
    return httpx.Request(method, url, json=json_data, headers=headers)

async def upsert_team(client: httpx.AsyncClient, team_data: GrafanaTeam) -> tuple[int, str]:
    """
    Search for a team by name and create it if it doesn't exist.
    Returns tuple of (team_id, team_uid).
    """
    # First, search for the team by name
    search_req = await create_grafana_request(
        "GET", 
        f"/api/teams/search?query={team_data.name}"
    )
    search_resp = await client.send(search_req)
    search_resp.raise_for_status()
    search_result = search_resp.json()

    # If team exists, return its ID and UID
    if search_result.get("totalCount", 0) > 0:
        teams = search_result.get("teams", [])
        if teams:
            return teams[0]["id"], teams[0]["uid"]

    # If team doesn't exist, create it
    create_req = await create_grafana_request(
        "POST", 
        "/api/teams", 
        team_data.dict(exclude={"id", "uid"})
    )
    create_resp = await client.send(create_req)
    create_resp.raise_for_status()
    new_team = create_resp.json()
    return new_team["teamId"], new_team["uid"]

async def upsert_team_group(client: httpx.AsyncClient, team_id: int, group_name: str) -> None:
    """
    Search for a group in team's groups and create it if it doesn't exist.
    """
    # First, get all groups for the team
    groups_req = await create_grafana_request(
        "GET",
        f"/api/teams/{team_id}/groups"
    )
    groups_resp = await client.send(groups_req)
    groups_resp.raise_for_status()
    existing_groups = groups_resp.json()

    # Check if group already exists
    group_exists = any(group["groupId"] == group_name for group in existing_groups)
    
    if not group_exists:
        # Add the new group
        add_group_req = await create_grafana_request(
            "POST",
            f"/api/teams/{team_id}/groups",
            {"groupId": group_name}
        )
        add_group_resp = await client.send(add_group_req)
        add_group_resp.raise_for_status()

async def update_datasource_permissions(client: httpx.AsyncClient, team_uid: str) -> None:
    """
    Grant Query permission to the team for the Prometheus datasource.
    """
    permission_data = {"permission": "Query"}

    # Update permissions for the datasource
    perm_req = await create_grafana_request(
        "POST",
        f"/api/access-control/datasources/{GRAFANA_CONFIG['datasource_id']}/teams/{team_uid}",
        permission_data
    )
    perm_resp = await client.send(perm_req)
    perm_resp.raise_for_status()

async def update_lbac_rules(client: httpx.AsyncClient, team_uid: str, team_name: str) -> None:
    """
    Update LBAC rules for the team to apply team_id label.
    First checks if rule exists to avoid overwriting other rules.
    """
    # First, get existing LBAC rules
    get_rules_req = await create_grafana_request(
        "GET",
        f"/api/datasources/uid/{GRAFANA_CONFIG['datasource_id']}/lbac/teams"
    )
    get_rules_resp = await client.send(get_rules_req)
    get_rules_resp.raise_for_status()
    
    existing_rules = get_rules_resp.json().get("rules", []) or []
    rule = {
        "teamUid": team_uid,
        "rules": [
            f'''{{team_id="{team_name}"}}'''
        ]
    }
      
    # Update LBAC rules for the datasource, if applicable.
    if rule not in existing_rules:
        lbac_req = await create_grafana_request(
            "PUT",
            f"/api/datasources/uid/{GRAFANA_CONFIG['datasource_id']}/lbac/teams",
            {"rules": existing_rules + [rule]}
        )
        lbac_resp = await client.send(lbac_req)
        lbac_resp.raise_for_status()

async def upsert_dashboard_role(client: httpx.AsyncClient, dashboard_id: str) -> str:
    """
    Create or update a role for the team with dashboard access permissions.
    Returns the role UID.
    """
    # Create role UID from dashboard ID
    role_uid = f"custom_dashboard_read_{dashboard_id}"
    
    role_data = {
        "version": 1,
        "uid": role_uid,
        "name": f"custom:dashboard-read:{dashboard_id}",
        "description": f"Provides dashboard access to {dashboard_id}",
        "displayName": f"Dashboard access - {dashboard_id}",
        "group": "Custom",
        "global": True,
        "permissions": [
            {
                "action": "dashboards:read",
                "scope": f"dashboards:uid:{dashboard_id}"
            },
            {
                "action": "annotations:read",
                # TODO: Double check this.
                "scope": "annotations:*"
            }
        ]
    }

    # First, try to get the role
    get_role_req = await create_grafana_request(
        "GET",
        f"/api/access-control/roles/{role_uid}"
    )
    get_role_resp = await client.send(get_role_req)
    
    # If role exists, update it with PUT
    if get_role_resp.status_code == 200:
        resp = get_role_resp.json()
        if resp["permissions"] != role_data["permissions"]:
            role_data["version"] = resp["version"] + 1
            role_req = await create_grafana_request(
                "PUT",
                f"/api/access-control/roles/{role_uid}",
                role_data
            )
    
    # If role doesn't exist, create it with POST
    else:
        role_req = await create_grafana_request(
            "POST",
            "/api/access-control/roles",
            role_data
        )
    
    role_resp = await client.send(role_req)
    role_resp.raise_for_status()
    
    return role_uid

async def assign_role_to_team(client: httpx.AsyncClient, team_id: int, role_uid: str) -> None:
    """
    Assign a role to a team.
    """
    # Assign role to team
    assign_req = await create_grafana_request(
        "POST",
        f"/api/access-control/teams/{team_id}/roles",
        {
            "roleUid": role_uid
        }
    )
    assign_resp = await client.send(assign_req)
    assign_resp.raise_for_status()

def generate_grafana_jwt(username: str, email: str, team_name: str, user_id: int) -> str:
    """Generate a JWT token for Grafana authentication"""
    now = int(time())
    claims = {
        "sub": str(user_id),  # Subject (user id as string)
        "iss": "embed-app",  # Issuer
        "iat": now,  # Issued at
        "exp": now + 3600,  # Expires in 1 hour
        "aud": "grafana",  # Audience
        "kid": "embed-key-1",  # Key ID matching the one in JWKS
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "groups": [team_name],
            "role": "None",
        }
    }
    
    return jwt.encode(
        claims=claims,
        key=GRAFANA_CONFIG["private_key"],
        algorithm="RS256",
        headers={"kid": "embed-key-1"}
    )

@app.get("/", response_class=HTMLResponse)
async def serve_html(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dashboard_id": GRAFANA_CONFIG["dashboard_id"]
    })

@app.post("/grafana/dashboard/{dashboard_id}")
async def handle_grafana_dashboard(dashboard_id: str, request: DashboardRequest):
    async with httpx.AsyncClient() as client:
        try:
            if request.user_id == 1:
                username = "john"
                user_email = "john@customer123.com"
                team_data = GrafanaTeam(name="Customer 123", email="team@customer123.com")
            elif request.user_id == 2:
                username = "peter"
                user_email = "peter@customer456.com"
                team_data = GrafanaTeam(name="Customer 456", email="team@customer456.com")
            else:
                raise HTTPException(status_code=400, detail="Invalid user ID")

            # Step 1: Upsert team
            team_id, team_uid = await upsert_team(client, team_data)
            
            # Step 2: Upsert dashboard role
            role_uid = await upsert_dashboard_role(client, dashboard_id)
            
            # Step 3: Assign role to team
            await assign_role_to_team(client, team_id, role_uid)
            
            # Step 4: Ensure team group exists
            await upsert_team_group(client, team_id, team_data.name)
            
            # Step 5: Update datasource permissions
            await update_datasource_permissions(client, team_uid)

            # Step 6: Update LBAC rules
            await update_lbac_rules(client, team_uid, team_data.name)
            
            # Generate JWT token with user info and team name
            auth_token = generate_grafana_jwt(username, user_email, team_data.name, request.user_id)
            
            base_url = GRAFANA_CONFIG["base_url"].rstrip('/')
            return {
                "message": f"Processing dashboard ID: {dashboard_id}",
                "team_id": team_id,
                "team_uid": team_uid,
                "url": f"{base_url}/d/{dashboard_id}?orgId=1&kiosk&auth_token={auth_token}"
            }
        except httpx.HTTPError as e:
            logger.error(f"Grafana API error: {str(e)}\nResponse content: {e.response.content if hasattr(e, 'response') else 'No response'}")
            raise HTTPException(
                status_code=500,
                detail=f"Grafana API error: {str(e)}"
            )

@app.get("/metrics")
async def metrics():
    """
    Return Prometheus-formatted metrics with simulated CPU utilization.
    """
    # Calculate oscillating values between 0.5 and 1.0 using sine wave
    t = time()
    base_value = 0.75  # Center point between 0.5 and 1.0
    amplitude = 0.25   # Distance from center to peak/trough
    
    # Create two different phases for different customers
    value1 = base_value + amplitude * math.sin(t)
    value2 = base_value + amplitude * math.sin(t + math.pi)  # Offset by π to get opposite phase
    
    # Format in Prometheus text format
    metrics_text = """# HELP cpu_utilization CPU utilization percentage
# TYPE cpu_utilization gauge
cpu_utilization{team_id="Customer 123"} %.3f
cpu_utilization{team_id="Customer 456"} %.3f
""" % (value1, value2)
    
    return Response(
        content=metrics_text,
        media_type="text/plain"
    )

@app.get("/.well-known/jwks.json")
async def serve_jwks():
    """
    Serve the JWKS (JSON Web Key Set) for JWT verification.
    """
    return JWKS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
