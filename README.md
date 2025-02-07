# Grafana Embedding PoC

> [!NOTE]  
> This documentation and codebase were generated with the assistance of Cursor AI.

This project demonstrates embedding Grafana dashboards with team-based access control and label-based access control (LBAC) for metrics.

## Features

- Embedded Grafana dashboard with JWT authentication
- Team-based access control for dashboards
- Label-based access control (LBAC) for metrics
- Custom metrics endpoint with simulated CPU utilization
- Role-based dashboard access permissions
- JWKS endpoint for JWT verification

## Prerequisites

- Python 3.9+
- A Grafana Cloud instance with:
  - Enterprise features enabled
  - Grafana Service Account token with admin privileges
  - Prometheus datasource configured
  - Dashboard configured with a panel based on the `cpu_utilization` metric (make note of the dashboard ID).

### Grafana Configuration Requirements

You'll want to contact support to have these enabled for you.

```ini
[feature_toggles]
teamHttpHeadersMimir = true

[auth.jwt]
auto_sign_up = true
cache_ttl = 60s
enabled = true
header_name = X-JWT-Assertion
jwk_set_url = https://<server_url>/.well-known/jwks.json
url_login = true
username_attribute_path = user.username
email_attribute_path = user.email
groups_attribute_path = user.group
# This is important, as users would otherwise have "Viewer" permission on the entire stack.
role_attribute_path = "'None'"

[security]
allow_embedding = true
```

## Running the application

1. Create a Python virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
# Grafana instance configuration
GRAFANA_BASE_URL=https://your-instance.grafana.net
GRAFANA_TOKEN=your-api-token
GRAFANA_DATASOURCE_ID=your-datasource-uid

# Grafana Cloud metrics configuration
GRAFANA_CLOUD_OTLP_ENDPOINT=https://prometheus-X.grafana.net/api/prom/push
GRAFANA_CLOUD_INSTANCE_ID=your-instance-id
GRAFANA_CLOUD_TOKEN=your-metrics-push-token
```

3. Start the metrics collection:
```bash
docker-compose up -d
```

4. Run the application:
```bash
python main.py
```

5. Visit http://localhost:8080 to test the dashboard embedding

## Usage

1. Open http://localhost:8080 in your browser
2. Select a customer from the dropdown (John @ Customer 123 or Peter @ Customer 456)
3. Click "Load" to view the dashboard with the appropriate team-based filtering

## Architecture

- FastAPI backend server providing:
  - JWT generation for Grafana authentication
  - Team and role management via Grafana API
  - LBAC rules configuration
  - Simulated metrics endpoint
- Frontend with customer selection and dashboard embedding
- RSA key pair for JWT signing and verification

## Security Features

- JWT-based authentication
- Team-based access control
- Label-based access control for metrics
- Role-based dashboard permissions
